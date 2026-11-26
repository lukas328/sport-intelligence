# Azure module (ADR 025): Container Apps + Postgres Flexible Server in one resource group.
# Video and artifacts stay in Cloudflare R2 (ADR 002); GPU analysis behind GpuBackend.

data "azurerm_client_config" "current" {}

locals {
  prefix = "${var.name}-${var.environment == "production" ? "prod" : "stg"}"
  # globally unique names (registry, key vault, postgres) get a short random suffix
  unique = "${var.name}${var.environment == "production" ? "prod" : "stg"}${random_string.suffix.result}"
  tags = {
    app         = "handball-ai"
    environment = var.environment
    managed_by  = "terraform"
  }
  web_base_url = "https://${var.app_domain}"
  # the sending domain: by default the site's domain (app.example.ch -> example.ch)
  mail_domain = var.mail_domain != "" ? var.mail_domain : join(".", slice(split(".", var.app_domain), 1, length(split(".", var.app_domain))))
  registry    = azurerm_container_registry.this.login_server
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.prefix}"
  location = var.location
  tags     = local.tags
}

# --- Cost guard ---------------------------------------------------------------------------------

resource "azurerm_consumption_budget_resource_group" "this" {
  name              = "budget-${local.prefix}"
  resource_group_id = azurerm_resource_group.this.id
  amount            = var.budget_amount
  time_grain        = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", plantimestamp())
  }

  notification {
    operator       = "GreaterThan"
    threshold      = 80
    threshold_type = "Actual"
    contact_emails = var.alert_emails
  }

  notification {
    operator       = "GreaterThan"
    threshold      = 100
    threshold_type = "Forecasted"
    contact_emails = var.alert_emails
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}

# --- Logs, network, registry, identity ----------------------------------------------------------

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${local.prefix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_virtual_network" "this" {
  name                = "vnet-${local.prefix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  address_space       = ["10.40.0.0/16"]
  tags                = local.tags
}

# Container Apps needs its own subnet; a custom network also allows the internal TCP ingress for Redis.
resource "azurerm_subnet" "apps" {
  name                 = "snet-apps"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = ["10.40.0.0/23"]

  delegation {
    name = "containerapps"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_container_registry" "this" {
  name                = "acr${local.unique}"
  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

# One identity for all apps: pulls images and reads secrets, nothing else.
resource "azurerm_user_assigned_identity" "apps" {
  name                = "id-${local.prefix}-apps"
  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
}

# --- E-mail: Azure Communication Services (ADR 009) --------------------------------------------
# The sending domain is the site's domain, managed by us: its DNS records (domain, SPF, DKIM) are
# set by hand from the output mail_verification_records, the deploy then asks Azure to verify
# them. Only once all are verified does mail_live link the domain and switch the apps to it.

resource "azurerm_email_communication_service" "this" {
  name                = "${local.prefix}-email"
  resource_group_name = azurerm_resource_group.this.name
  data_location       = var.mail_data_location
  tags                = local.tags
}

resource "azurerm_email_communication_service_domain" "this" {
  name                             = local.mail_domain
  email_service_id                 = azurerm_email_communication_service.this.id
  domain_management                = "CustomerManaged"
  user_engagement_tracking_enabled = false
  tags                             = local.tags
}

resource "azurerm_email_communication_service_domain_sender_username" "this" {
  name                    = var.mail_sender
  email_service_domain_id = azurerm_email_communication_service_domain.this.id
  display_name            = "Handball Intelligence"
}

resource "azurerm_communication_service" "this" {
  name                = "${local.prefix}-acs-${local.unique}"
  resource_group_name = azurerm_resource_group.this.name
  data_location       = var.mail_data_location
  tags                = local.tags
}

# only a verified domain can be linked (the deploy sets mail_live once Azure verified it)
resource "azurerm_communication_service_email_domain_association" "this" {
  count                    = var.mail_live ? 1 : 0
  communication_service_id = azurerm_communication_service.this.id
  email_service_domain_id  = azurerm_email_communication_service_domain.this.id
}

# --- Secrets ------------------------------------------------------------------------------------

resource "azurerm_key_vault" "this" {
  name                       = "kv-${local.unique}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  soft_delete_retention_days = 7
  tags                       = local.tags
}

resource "azurerm_role_assignment" "kv_apps" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
}

# writes the generated secrets: whoever runs terraform, or the person named in kv_deployer_object_id
# when GitHub Actions deploys (its own identity gets the role from infra/azure/setup-github-deploy.sh,
# so that it can read the vault before terraform runs)
resource "azurerm_role_assignment" "kv_deployer" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = coalesce(var.kv_deployer_object_id, data.azurerm_client_config.current.object_id)
}

# a new environment applied from GitHub Actions while kv_deployer_object_id names the owner: the
# runner needs to write the vault too (the first environment got this role from
# infra/azure/setup-github-deploy.sh, so it stays off there)
resource "azurerm_role_assignment" "kv_runner" {
  count                = var.kv_runner_role ? 1 : 0
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

resource "random_password" "internal_token" {
  length  = 48
  special = false
}

resource "random_password" "pg_admin" {
  length  = 40
  special = false
}

resource "random_password" "pg_app" {
  length  = 40
  special = false
}

# Fernet key: 32 random bytes, URL-safe base64
resource "random_bytes" "encryption_key" {
  length = 32
}

locals {
  pg_host   = azurerm_postgresql_flexible_server.this.fqdn
  pg_admin  = "hbadmin"
  fernet    = replace(replace(random_bytes.encryption_key.base64, "+", "-"), "/", "_")
  db_app    = "postgresql+asyncpg://handball_app:${random_password.pg_app.result}@${local.pg_host}:5432/handball?ssl=require"
  db_owner  = "postgresql+asyncpg://${local.pg_admin}:${random_password.pg_admin.result}@${local.pg_host}:5432/handball?ssl=require"
  dsn_owner = "postgresql://${local.pg_admin}:${random_password.pg_admin.result}@${local.pg_host}:5432/handball?sslmode=require"

  # sessions and the encrypted columns depend on these two: Terraform writes a random value once and
  # never overwrites it, so a new environment can take over the old one's values (the move to
  # another region copies them before the database, docs/plans/staging-umzug-eu.md)
  carried_secrets = {
    "hb-secret-key"     = random_password.secret_key.result
    "hb-encryption-key" = local.fernet
  }

  generated_secrets = {
    "hb-internal-token"   = random_password.internal_token.result
    "hb-database-url"     = local.db_app
    "hb-migration-db-url" = local.db_owner
    "hb-admin-dsn"        = local.dsn_owner
    "hb-app-db-password"  = random_password.pg_app.result
    # the access key of the mail service: used only once mail_live switches the backend
    "hb-acs-connection-string" = azurerm_communication_service.this.primary_connection_string
  }

  # set by hand after the first apply (README, step 4); terraform never overwrites them
  manual_secrets = ["hb-s3-secret-key", "hb-smtp-password"]
}

resource "azurerm_key_vault_secret" "generated" {
  for_each     = local.generated_secrets
  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.this.id
  depends_on   = [azurerm_role_assignment.kv_deployer, azurerm_role_assignment.kv_runner]
}

resource "azurerm_key_vault_secret" "carried" {
  for_each     = local.carried_secrets
  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.this.id
  depends_on   = [azurerm_role_assignment.kv_deployer, azurerm_role_assignment.kv_runner]

  lifecycle {
    ignore_changes = [value, tags]
  }
}

moved {
  from = azurerm_key_vault_secret.generated["hb-secret-key"]
  to   = azurerm_key_vault_secret.carried["hb-secret-key"]
}

moved {
  from = azurerm_key_vault_secret.generated["hb-encryption-key"]
  to   = azurerm_key_vault_secret.carried["hb-encryption-key"]
}

resource "azurerm_key_vault_secret" "manual" {
  for_each     = toset(local.manual_secrets)
  name         = each.key
  value        = "set-me"
  key_vault_id = azurerm_key_vault.this.id
  depends_on   = [azurerm_role_assignment.kv_deployer, azurerm_role_assignment.kv_runner]

  lifecycle {
    ignore_changes = [value, tags]
  }
}

# --- Postgres -----------------------------------------------------------------------------------

resource "azurerm_postgresql_flexible_server" "this" {
  name                          = "psql-${local.unique}"
  resource_group_name           = azurerm_resource_group.this.name
  location                      = var.location
  version                       = "16"
  sku_name                      = var.postgres_sku
  storage_mb                    = var.postgres_storage_mb
  backup_retention_days         = var.postgres_backup_days
  geo_redundant_backup_enabled  = false
  administrator_login           = local.pg_admin
  administrator_password        = random_password.pg_admin.result
  public_network_access_enabled = true
  tags                          = local.tags

  authentication {
    password_auth_enabled = true
  }

  lifecycle {
    ignore_changes = [zone, high_availability[0].standby_availability_zone]
  }
}

# Extensions used by the baseline migration must be allow-listed on Azure.
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "PGCRYPTO,CITEXT"
}

resource "azurerm_postgresql_flexible_server_database" "handball" {
  name      = "handball"
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# 0.0.0.0 = "allow Azure services". TLS is enforced and passwords are long; private access via the
# VNet is the next hardening step (ADR 025, consequences).
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Postgres logs and metrics in Log Analytics, next to the apps' logs: who connects (with the API's
# application_name per process), connection counts and failures. Staging 17.11.: the connection
# errors could not be explained because none of this was collected.
resource "azurerm_monitor_diagnostic_setting" "postgres" {
  name                       = "diag-postgres"
  target_resource_id         = azurerm_postgresql_flexible_server.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  enabled_log {
    category = "PostgreSQLLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_postgresql_flexible_server_configuration" "log_connections" {
  for_each  = toset(["log_connections", "log_disconnections"])
  name      = each.key
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "on"
}

# The API's connections must fit the server's free slots, with room for the migration job and a
# diagnosis: a plan with more replicas, processes or pool than the server takes fails here instead
# of on a busy afternoon.
check "db_connections" {
  assert {
    condition = (
      local.api_db.processes * local.python_apps.api.max * (local.api_db.pool + local.api_db.overflow)
      + var.postgres_spare_connections <= var.postgres_user_connections
    )
    error_message = "API connections (processes x max replicas x (pool + overflow)) plus the spare ones exceed postgres_user_connections."
  }
}

# --- Container Apps -----------------------------------------------------------------------------

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${local.prefix}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  infrastructure_subnet_id   = azurerm_subnet.apps.id
  tags                       = local.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }

  # serverless T4 for the GPU job (only in regions that offer it, e.g. swedencentral)
  dynamic "workload_profile" {
    for_each = var.gpu ? [1] : []
    content {
      name                  = local.gpu_profile
      workload_profile_type = "Consumption-GPU-NC8as-T4"
    }
  }

  lifecycle {
    ignore_changes = [infrastructure_resource_group_name]
  }
}

locals {
  # Apps without an HTTP rule (workers, Redis over TCP) never scale in on their own, even with
  # min_replicas = 0. While paused they get a cron rule that is active one minute a year, so KEDA
  # scales them to 0 the rest of the time.
  paused_rule = {
    name = "paused"
    type = "cron"
    metadata = {
      timezone        = "Etc/UTC"
      start           = "0 0 1 1 *"
      end             = "1 0 1 1 *"
      desiredReplicas = "1"
    }
  }

  app_names = {
    web   = "${local.prefix}-web"
    api   = "${local.prefix}-api"
    redis = "${local.prefix}-redis"
  }

  # Non-secret settings shared by api, worker, gpu-worker and the migration job.
  python_env = merge({
    HB_ENV                    = var.environment
    HB_LOG_JSON               = "true"
    HB_REDIS_URL              = "redis://${local.app_names.redis}:6379/0"
    HB_API_INTERNAL_URL       = "http://${local.app_names.api}"
    HB_WEB_BASE_URL           = local.web_base_url
    HB_CORS_ORIGINS           = jsonencode([local.web_base_url])
    HB_S3_ENDPOINT_URL        = var.s3_endpoint_url
    HB_S3_PUBLIC_ENDPOINT_URL = var.s3_endpoint_url
    HB_S3_REGION              = "auto"
    HB_S3_ACCESS_KEY          = var.s3_access_key
    HB_S3_BUCKET_VIDEOS       = var.s3_bucket_videos
    HB_S3_BUCKET_ARTIFACTS    = var.s3_bucket_artifacts
    HB_MEDIA_DIRECT           = var.media_direct ? "true" : "false"
    HB_EMAIL_BACKEND          = "smtp"
    HB_EMAIL_FROM             = var.email_from
    HB_SMTP_HOST              = var.smtp_host
    HB_SMTP_PORT              = tostring(var.smtp_port)
    HB_SMTP_USERNAME          = var.smtp_username
    HB_SMTP_STARTTLS          = var.smtp_port == 587 ? "true" : "false"
    HB_COOKIE_SECURE          = "true"
    HB_PWNED_CHECK            = "true"
    HB_BILLING_ENFORCE        = var.billing_enforce ? "true" : "false"
    HB_OPERATOR_EMAILS        = jsonencode(var.operator_emails)
    HB_GPU_BACKEND            = var.gpu_backend
  }, var.extra_env, local.mail_env)

  # once the sending domain is verified and linked, mail goes through it; this overrides a
  # «console» backend kept in extra_env from the time without a provider
  mail_env = var.mail_live ? {
    HB_EMAIL_BACKEND = "acs"
    HB_EMAIL_FROM    = "Handball Intelligence <${var.mail_sender}@${local.mail_domain}>"
    HB_MAIL_ENABLED  = "true"
  } : {}

  # env var -> Key Vault secret name
  python_secrets = merge({
    HB_DATABASE_URL   = "hb-database-url"
    HB_SECRET_KEY     = "hb-secret-key"
    HB_ENCRYPTION_KEY = "hb-encryption-key"
    HB_INTERNAL_TOKEN = "hb-internal-token"
    HB_S3_SECRET_KEY  = "hb-s3-secret-key"
    HB_SMTP_PASSWORD  = "hb-smtp-password"
    }, {
    # the mail service's access key (Key Vault, written by Terraform)
    HB_ACS_CONNECTION_STRING = "hb-acs-connection-string"
  }, { for v in var.optional_secrets : v => lower(replace(v, "_", "-")) })

  kv_uri = azurerm_key_vault.this.vault_uri

  # Creates or updates the runtime role (no BYPASSRLS, ADR 005) before the migrations grant to it.
  ensure_role_py = <<-PY
    import asyncio, os, asyncpg
    async def main():
        c = await asyncpg.connect(os.environ["HB_ADMIN_DSN"])
        pw = os.environ["HB_APP_DB_PASSWORD"]
        exists = await c.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'handball_app'")
        # The Azure admin is no superuser: it may set the attributes when it creates the role,
        # but naming them again in ALTER ROLE fails, so a rerun only refreshes the password.
        if exists:
            await c.execute(f"ALTER ROLE handball_app LOGIN PASSWORD '{pw}'")
        else:
            await c.execute(f"CREATE ROLE handball_app LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS")
        await c.execute("GRANT CONNECT ON DATABASE handball TO handball_app")
        await c.execute("GRANT USAGE ON SCHEMA public TO handball_app")
        await c.close()
    asyncio.run(main())
  PY

  # API connections to Postgres per process; all replicas together must fit the server's free
  # slots (check "db_connections")
  api_db = { processes = 2, pool = 3, overflow = 1 }

  # the analysis on the CPU of an always-on app; with var.gpu the GPU job below takes the GPU queue
  python_apps = merge(local.base_apps, var.gpu ? {} : { gpu-worker = local.cpu_analysis_app })

  base_apps = {
    api = {
      image   = "hb-api"
      cpu     = 0.5
      memory  = "1Gi"
      min     = 1
      max     = 3
      ingress = true
      # Database connections: processes x replicas x (pool + overflow), checked against the
      # server's free slots by the check "db_connections" below (17.11.: TooManyConnections when
      # the HTTP scaler started a second replica)
      env = {
        FORWARDED_ALLOW_IPS = "*"
        HB_WORKERS          = tostring(local.api_db.processes)
        HB_DB_POOL_SIZE     = tostring(local.api_db.pool)
        HB_DB_MAX_OVERFLOW  = tostring(local.api_db.overflow)
      }
    }
    worker = {
      image   = "hb-worker"
      cpu     = 1
      memory  = "2Gi"
      min     = 1
      max     = 2
      ingress = false
      env     = {}
    }

  }

  cpu_analysis_app = {
    image   = "hb-gpu-worker"
    cpu     = var.gpu_worker_cpu
    memory  = var.gpu_worker_memory
    min     = 1
    max     = 1
    ingress = false
    # Ball net on the CPU (no GPU on staging yet, tests with 5 to 10 minute clips): one net,
    # every 3rd frame at 960 px width. The model file lies in the artifacts bucket and is
    # checked against its SHA-256. Re-identification runs only with a GPU (product audit
    # 2026-11: 56 % of the CPU analysis time), HB_BALL_ALLOW_CPU does not switch it on.
    env = {
      HB_BALL_MODEL        = "models/ball/ball_hrp1_fp16-37153d8dfc83.onnx"
      HB_BALL_MODEL_SHA256 = "37153d8dfc832e683283b43229d35ea5fd1a257757c689d1b05ffb81fd9779f5"
      HB_BALL_ALLOW_CPU    = "1"
      HB_BALL_WIDTH        = "960"
      HB_BALL_EVERY        = "3"
    }
  }
}

# Redis keeps the job queue. Without persistence every restart of its replica (platform moves,
# a change to this app) wiped out the jobs that were only waiting (staging 17.11.). An append-only
# file on a small Azure Files share brings them back; the queue is small, so the share is too.
resource "azurerm_storage_account" "redis" {
  name                            = substr("st${local.unique}redis", 0, 24)
  resource_group_name             = azurerm_resource_group.this.name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = local.tags
}

resource "azurerm_storage_share" "redis" {
  name               = "redis"
  storage_account_id = azurerm_storage_account.redis.id
  quota              = 1
}

resource "azurerm_container_app_environment_storage" "redis" {
  name                         = "redis-data"
  container_app_environment_id = azurerm_container_app_environment.this.id
  account_name                 = azurerm_storage_account.redis.name
  share_name                   = azurerm_storage_share.redis.name
  access_key                   = azurerm_storage_account.redis.primary_access_key
  access_mode                  = "ReadWrite"
}

resource "azurerm_container_app" "redis" {
  name                         = local.app_names.redis
  resource_group_name          = azurerm_resource_group.this.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  # Job queue and rate limits only; nothing durable lives here (ADR 001), so no persistence.
  template {
    min_replicas = var.paused ? 0 : 1
    max_replicas = 1

    dynamic "custom_scale_rule" {
      for_each = var.paused ? [local.paused_rule] : []
      content {
        name             = custom_scale_rule.value.name
        custom_rule_type = custom_scale_rule.value.type
        metadata         = custom_scale_rule.value.metadata
      }
    }

    container {
      name   = "redis"
      image  = "docker.io/library/redis:7-alpine"
      cpu    = 0.25
      memory = "0.5Gi"
      # via sh: the azurerm provider cannot read back an empty argument ("--save" ""). The
      # append-only file on the share survives a restart; fsync once a second is enough for a
      # queue that the watchdog repairs anyway (a lost waiting job is enqueued again).
      command = [
        "sh", "-c",
        "exec redis-server --dir /data --appendonly yes --appendfsync everysec --save '' --maxmemory 384mb",
      ]
      volume_mounts {
        name = "data"
        path = "/data"
      }
    }

    volume {
      name         = "data"
      storage_name = azurerm_container_app_environment_storage.redis.name
      storage_type = "AzureFile"
    }
  }

  ingress {
    external_enabled = false
    transport        = "tcp"
    target_port      = 6379
    exposed_port     = 6379
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

resource "azurerm_container_app" "python" {
  for_each                     = local.python_apps
  name                         = "${local.prefix}-${each.key}"
  resource_group_name          = azurerm_resource_group.this.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = local.registry
    identity = azurerm_user_assigned_identity.apps.id
  }

  dynamic "secret" {
    for_each = local.python_secrets
    content {
      name                = secret.value
      identity            = azurerm_user_assigned_identity.apps.id
      key_vault_secret_id = "${local.kv_uri}secrets/${secret.value}"
    }
  }

  template {
    min_replicas = var.paused ? 0 : each.value.min
    max_replicas = each.value.max

    dynamic "custom_scale_rule" {
      for_each = var.paused ? [local.paused_rule] : []
      content {
        name             = custom_scale_rule.value.name
        custom_rule_type = custom_scale_rule.value.type
        metadata         = custom_scale_rule.value.metadata
      }
    }

    container {
      name   = each.key
      image  = "${local.registry}/${each.value.image}:${var.image_tag}"
      cpu    = each.value.cpu
      memory = each.value.memory

      dynamic "env" {
        for_each = merge(local.python_env, each.value.env)
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.python_secrets
        content {
          name        = env.key
          secret_name = env.value
        }
      }
    }
  }

  dynamic "ingress" {
    for_each = each.value.ingress ? [1] : []
    content {
      external_enabled = false
      target_port      = 8000
      transport        = "http"
      traffic_weight {
        latest_revision = true
        percentage      = 100
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_apps,
    azurerm_key_vault_secret.generated,
    azurerm_key_vault_secret.carried,
    azurerm_key_vault_secret.manual,
  ]
}

resource "azurerm_container_app" "web" {
  name                         = local.app_names.web
  resource_group_name          = azurerm_resource_group.this.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = local.registry
    identity = azurerm_user_assigned_identity.apps.id
  }

  template {
    min_replicas = var.paused ? 0 : var.web_min_replicas
    max_replicas = 3

    container {
      name   = "web"
      image  = "${local.registry}/hb-web:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "HB_API_INTERNAL_URL"
        value = "http://${local.app_names.api}"
      }
      env {
        name  = "HB_S3_PUBLIC_URL"
        value = var.s3_endpoint_url
      }
      # absolute URLs in the link previews of shared pages (og:image, og:url)
      env {
        name  = "HB_WEB_BASE_URL"
        value = local.web_base_url
      }
    }
  }

  # The browser only talks to web; /v1 is proxied to the internal API (apps/web/src/app/v1).
  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}

# Needs the DNS records first (README, step 6); the managed certificate is then bound with az,
# which terraform must not undo.
resource "azurerm_container_app_custom_domain" "web" {
  count            = var.bind_custom_domain ? 1 : 0
  name             = var.app_domain
  container_app_id = azurerm_container_app.web.id

  lifecycle {
    ignore_changes = [certificate_binding_type, container_app_environment_certificate_id]
  }
}

# Migrations: run by hand after each deploy that contains a new migration (README, step 5).
resource "azurerm_container_app_job" "migrate" {
  name                         = "${local.prefix}-migrate"
  resource_group_name          = azurerm_resource_group.this.name
  location                     = var.location
  container_app_environment_id = azurerm_container_app_environment.this.id
  workload_profile_name        = "Consumption"
  replica_timeout_in_seconds   = 1800
  replica_retry_limit          = 0
  tags                         = local.tags

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = local.registry
    identity = azurerm_user_assigned_identity.apps.id
  }

  dynamic "secret" {
    for_each = merge(local.python_secrets, {
      HB_MIGRATION_DATABASE_URL = "hb-migration-db-url"
      HB_ADMIN_DSN              = "hb-admin-dsn"
      HB_APP_DB_PASSWORD        = "hb-app-db-password"
    })
    content {
      name                = secret.value
      identity            = azurerm_user_assigned_identity.apps.id
      key_vault_secret_id = "${local.kv_uri}secrets/${secret.value}"
    }
  }

  template {
    container {
      name    = "migrate"
      image   = "${local.registry}/hb-api:${var.image_tag}"
      cpu     = 0.5
      memory  = "1Gi"
      command = ["sh", "-c", "python -c \"$HB_ENSURE_ROLE_PY\" && cd /app/apps/api && alembic upgrade head && python -m handball_api.bootstrap"]

      env {
        name  = "HB_ENSURE_ROLE_PY"
        value = local.ensure_role_py
      }

      dynamic "env" {
        for_each = local.python_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = merge(local.python_secrets, {
          HB_MIGRATION_DATABASE_URL = "hb-migration-db-url"
          HB_ADMIN_DSN              = "hb-admin-dsn"
          HB_APP_DB_PASSWORD        = "hb-app-db-password"
        })
        content {
          name        = env.key
          secret_name = env.value
        }
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_apps,
    azurerm_key_vault_secret.generated,
    azurerm_key_vault_secret.carried,
    azurerm_key_vault_secret.manual,
    azurerm_postgresql_flexible_server_configuration.extensions,
    azurerm_postgresql_flexible_server_database.handball,
    # without it the job cannot reach the server: a targeted apply of the job (the deploy's
    # migration step on a new environment) must create it too (stack eu bootstrap, 23.11.)
    azurerm_postgresql_flexible_server_firewall_rule.azure,
  ]
}

# --- GPU analysis: serverless T4, an event-driven job (docs/plans/staging-umzug-eu.md) ------------
# One execution per batch of waiting analyses: KEDA watches the length of the GPU queue in Redis,
# the execution runs the GPU worker in burst mode (works the queue, then ends). A job, not an app:
# scaling in would stop an app replica mid-analysis once the job left the list, an execution runs
# to its end. At most one at a time, nothing runs (and nothing is billed) while the queue is empty.

locals {
  gpu_profile = "gpu-t4"
  gpu_env = {
    # the uint8 ball net at 960 px on every frame (Dockerfile.cuda defaults), as staging-env.json
    # names it for the CPU worker; videos over the limit end as «too long»
    HB_ANALYSIS_MAX_MINUTES = tostring(var.gpu_max_video_minutes)
    HB_BALL_MODEL           = var.gpu_ball_model
    HB_BALL_MODEL_SHA256    = var.gpu_ball_model_sha256
  }
}

resource "azurerm_container_app_job" "gpu" {
  count                        = var.gpu ? 1 : 0
  name                         = "${local.prefix}-gpu"
  resource_group_name          = azurerm_resource_group.this.name
  location                     = var.location
  container_app_environment_id = azurerm_container_app_environment.this.id
  workload_profile_name        = local.gpu_profile
  replica_timeout_in_seconds   = var.gpu_job_timeout_s
  replica_retry_limit          = 0
  tags                         = local.tags

  event_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
    scale {
      min_executions              = 0
      max_executions              = 1
      polling_interval_in_seconds = 30
      rules {
        name             = "gpu-queue"
        custom_rule_type = "redis"
        metadata = {
          address    = "${local.app_names.redis}:6379"
          listName   = "rq:queue:gpu"
          listLength = "1"
        }
      }
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = local.registry
    identity = azurerm_user_assigned_identity.apps.id
  }

  dynamic "secret" {
    for_each = local.python_secrets
    content {
      name                = secret.value
      identity            = azurerm_user_assigned_identity.apps.id
      key_vault_secret_id = "${local.kv_uri}secrets/${secret.value}"
    }
  }

  template {
    container {
      name    = "gpu-worker"
      image   = "${local.registry}/hb-gpu-worker-cuda:${var.image_tag}"
      cpu     = 8
      memory  = "56Gi"
      command = ["python", "-m", "handball_gpu_worker", "--burst"]

      dynamic "env" {
        for_each = merge(local.python_env, local.gpu_env)
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.python_secrets
        content {
          name        = env.key
          secret_name = env.value
        }
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_apps,
    azurerm_key_vault_secret.generated,
    azurerm_key_vault_secret.carried,
    azurerm_key_vault_secret.manual,
  ]
}

# The GPU part has its own monthly budget (alerts at gpu_budget_warn and gpu_budget_amount, in
# the billing currency), next to the one for the whole resource group.
resource "azurerm_consumption_budget_resource_group" "gpu" {
  count             = var.gpu ? 1 : 0
  name              = "budget-${local.prefix}-gpu"
  resource_group_id = azurerm_resource_group.this.id
  amount            = var.gpu_budget_amount
  time_grain        = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", plantimestamp())
  }

  filter {
    dimension {
      name   = "ResourceId"
      values = [azurerm_container_app_job.gpu[0].id]
    }
  }

  notification {
    operator       = "GreaterThan"
    threshold      = floor(100 * var.gpu_budget_warn / var.gpu_budget_amount)
    threshold_type = "Actual"
    contact_emails = var.alert_emails
  }

  notification {
    operator       = "GreaterThan"
    threshold      = 100
    threshold_type = "Actual"
    contact_emails = var.alert_emails
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}

# --- Monitoring: probe and alerts (infra/monitoring/alerts.md, GO_LIVE) ---------------------------
# E-mail to alert_emails through one action group. The probe runs only for the environment the app
# domain is bound to (bind_custom_domain): a paused or old environment does not probe a domain that
# points elsewhere. Log alerts read the environment's own Log Analytics workspace every 15 minutes.
# Rough cost: the probe about 7 USD per month (2 locations, every 15 min), each log alert about
# 0.50 USD, the metric alerts a few cents.

locals {
  monitoring = var.monitoring
  probe      = var.monitoring && var.bind_custom_domain
}

resource "azurerm_monitor_action_group" "ops" {
  count               = local.monitoring ? 1 : 0
  name                = "ag-${local.prefix}-ops"
  resource_group_name = azurerm_resource_group.this.name
  short_name          = "hb-ops"
  tags                = local.tags

  dynamic "email_receiver" {
    for_each = var.alert_emails
    content {
      name                    = "mail-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }
}

resource "azurerm_application_insights" "probe" {
  count               = local.probe ? 1 : 0
  name                = "appi-${local.prefix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "other"
  tags                = local.tags
}

# GET /api/healthz on the public domain (web and, behind it, the API), with the certificate's
# remaining lifetime checked (alert below 14 days)
resource "azurerm_application_insights_standard_web_test" "health" {
  count                   = local.probe ? 1 : 0
  name                    = "probe-${local.prefix}-health"
  resource_group_name     = azurerm_resource_group.this.name
  location                = var.location
  application_insights_id = azurerm_application_insights.probe[0].id
  frequency               = 900
  timeout                 = 30
  enabled                 = !var.paused
  retry_enabled           = true
  geo_locations           = var.probe_locations
  tags                    = local.tags

  request {
    url = "https://${var.app_domain}/api/healthz"
  }

  validation_rules {
    expected_status_code        = 200
    ssl_check_enabled           = true
    ssl_cert_remaining_lifetime = 14
  }
}

resource "azurerm_monitor_metric_alert" "availability" {
  count               = local.probe ? 1 : 0
  name                = "alert-${local.prefix}-availability"
  resource_group_name = azurerm_resource_group.this.name
  description         = "The app domain fails its health probe (or the certificate expires within 14 days) from all probe locations."
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"
  scopes = [
    azurerm_application_insights_standard_web_test.health[0].id,
    azurerm_application_insights.probe[0].id,
  ]
  tags = local.tags

  application_insights_web_test_location_availability_criteria {
    web_test_id           = azurerm_application_insights_standard_web_test.health[0].id
    component_id          = azurerm_application_insights.probe[0].id
    failed_location_count = length(var.probe_locations)
  }

  action {
    action_group_id = azurerm_monitor_action_group.ops[0].id
  }
}

locals {
  # name -> (description, severity, query, threshold: alert when the count is above it)
  log_alerts = {
    api-errors = {
      description = "The API answered with unexpected errors (500, unhandled exception) more than 3 times in 15 minutes."
      severity    = 1
      window      = "PT15M"
      threshold   = 3
      query       = "ContainerAppConsoleLogs_CL | where ContainerAppName_s endswith '-api' | where Log_s has 'unhandled_exception'"
    }
    job-failures = {
      description = "At least 3 processing jobs (ingest, analysis, sync) failed in the last hour, or the watchdog ended silent ones."
      severity    = 2
      window      = "PT1H"
      threshold   = 2
      query       = "ContainerAppConsoleLogs_CL | where ContainerAppName_s endswith '-api' | where Log_s has_any ('\"job_failed\"', '\"job_failed_silent\"')"
    }
    out-of-memory = {
      description = "A container was killed for using too much memory (analysis on a too small worker, a leak)."
      severity    = 2
      window      = "PT15M"
      threshold   = 0
      query       = "ContainerAppSystemLogs_CL | where Reason_s has 'OOMKilled' or Log_s has 'OOMKilled'"
    }
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "logs" {
  for_each             = local.monitoring ? local.log_alerts : {}
  name                 = "alert-${local.prefix}-${each.key}"
  resource_group_name  = azurerm_resource_group.this.name
  location             = var.location
  description          = each.value.description
  severity             = each.value.severity
  scopes               = [azurerm_log_analytics_workspace.this.id]
  evaluation_frequency = "PT15M"
  window_duration      = each.value.window
  enabled              = !var.paused
  tags                 = local.tags

  criteria {
    query                   = each.value.query
    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = each.value.threshold
    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.ops[0].id]
  }
}

resource "azurerm_monitor_metric_alert" "postgres_storage" {
  count               = local.monitoring ? 1 : 0
  name                = "alert-${local.prefix}-postgres-storage"
  resource_group_name = azurerm_resource_group.this.name
  description         = "The database uses more than 80 % of its storage."
  severity            = 2
  frequency           = "PT15M"
  window_size         = "PT1H"
  scopes              = [azurerm_postgresql_flexible_server.this.id]
  tags                = local.tags

  criteria {
    metric_namespace = "Microsoft.DBforPostgreSQL/flexibleServers"
    metric_name      = "storage_percent"
    aggregation      = "Maximum"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.ops[0].id
  }
}
