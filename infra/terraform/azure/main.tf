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
  registry     = azurerm_container_registry.this.login_server
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

# whoever runs terraform writes the generated secrets
resource "azurerm_role_assignment" "kv_deployer" {
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

  generated_secrets = {
    "hb-secret-key"        = random_password.secret_key.result
    "hb-encryption-key"    = local.fernet
    "hb-internal-token"    = random_password.internal_token.result
    "hb-database-url"      = local.db_app
    "hb-migration-db-url"  = local.db_owner
    "hb-admin-dsn"         = local.dsn_owner
    "hb-app-db-password"   = random_password.pg_app.result
  }

  # set by hand after the first apply (README, step 4); terraform never overwrites them
  manual_secrets = ["hb-s3-secret-key", "hb-smtp-password"]
}

resource "azurerm_key_vault_secret" "generated" {
  for_each     = local.generated_secrets
  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.this.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "manual" {
  for_each     = toset(local.manual_secrets)
  name         = each.key
  value        = "set-me"
  key_vault_id = azurerm_key_vault.this.id
  depends_on   = [azurerm_role_assignment.kv_deployer]

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

  lifecycle {
    ignore_changes = [infrastructure_resource_group_name]
  }
}

locals {
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
  }, var.extra_env)

  # env var -> Key Vault secret name
  python_secrets = merge({
    HB_DATABASE_URL   = "hb-database-url"
    HB_SECRET_KEY     = "hb-secret-key"
    HB_ENCRYPTION_KEY = "hb-encryption-key"
    HB_INTERNAL_TOKEN = "hb-internal-token"
    HB_S3_SECRET_KEY  = "hb-s3-secret-key"
    HB_SMTP_PASSWORD  = "hb-smtp-password"
  }, { for v in var.optional_secrets : v => lower(replace(v, "_", "-")) })

  kv_uri = azurerm_key_vault.this.vault_uri

  # Creates or updates the runtime role (no BYPASSRLS, ADR 005) before the migrations grant to it.
  ensure_role_py = <<-PY
    import asyncio, os, asyncpg
    async def main():
        c = await asyncpg.connect(os.environ["HB_ADMIN_DSN"])
        pw = os.environ["HB_APP_DB_PASSWORD"]
        exists = await c.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'handball_app'")
        verb = "ALTER" if exists else "CREATE"
        await c.execute(f"{verb} ROLE handball_app LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS")
        await c.execute("GRANT CONNECT ON DATABASE handball TO handball_app")
        await c.execute("GRANT USAGE ON SCHEMA public TO handball_app")
        await c.close()
    asyncio.run(main())
  PY

  python_apps = {
    api = {
      image   = "hb-api"
      cpu     = 0.5
      memory  = "1Gi"
      min     = 1
      max     = 3
      ingress = true
      env     = { FORWARDED_ALLOW_IPS = "*" }
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
    gpu-worker = {
      image   = "hb-gpu-worker"
      cpu     = var.gpu_worker_cpu
      memory  = var.gpu_worker_memory
      min     = 1
      max     = 1
      ingress = false
      env     = {}
    }
  }
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
    container {
      name    = "redis"
      image   = "docker.io/library/redis:7-alpine"
      cpu     = 0.25
      memory  = "0.5Gi"
      # via sh: the azurerm provider cannot read back an empty argument ("--save" "")
      command = ["sh", "-c", "exec redis-server --save '' --appendonly no --maxmemory 384mb"]
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
    azurerm_key_vault_secret.manual,
    azurerm_postgresql_flexible_server_configuration.extensions,
    azurerm_postgresql_flexible_server_database.handball,
  ]
}
