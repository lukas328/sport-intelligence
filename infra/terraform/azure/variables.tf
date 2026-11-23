variable "subscription_id" {
  description = "Azure subscription id (az account show --query id -o tsv)."
  type        = string
}

variable "name" {
  description = "Short prefix for all resources, lowercase letters and digits only."
  type        = string
  default     = "hb"
  validation {
    condition     = can(regex("^[a-z][a-z0-9]{1,9}$", var.name))
    error_message = "2 to 10 lowercase letters or digits, starting with a letter."
  }
}

variable "environment" {
  description = "production or staging; also sets HB_ENV."
  type        = string
  default     = "production"
  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "production or staging."
  }
}

variable "location" {
  description = "Azure region. Switzerland North keeps app data in CH (adequate for EU clubs); germanywestcentral is the EU alternative."
  type        = string
  default     = "switzerlandnorth"
}

variable "app_domain" {
  description = "Public host name of the web app, e.g. app.example.ch. The custom domain is bound after the first apply (README, step 6)."
  type        = string
}

variable "bind_custom_domain" {
  description = "Set to true once the CNAME and asuid TXT records for app_domain exist (README, step 6)."
  type        = bool
  default     = false
}

variable "kv_deployer_object_id" {
  description = "Object id of the person who keeps the Key Vault role «Secrets Officer» (empty: whoever runs terraform). Set when GitHub Actions deploys, so the owner keeps access."
  type        = string
  default     = ""
}

variable "image_tag" {
  description = "Tag of the images hb-api, hb-worker, hb-gpu-worker and hb-web in the registry."
  type        = string
  default     = "latest"
}

variable "budget_amount" {
  description = "Monthly budget for the resource group in the billing currency; alerts at 80 % and 100 % (forecast)."
  type        = number
  default     = 80
}

variable "alert_emails" {
  description = "Addresses that receive budget alerts."
  type        = list(string)
}

# --- Postgres -----------------------------------------------------------------------------------

variable "postgres_sku" {
  description = "Flexible Server SKU. B_Standard_B1ms is enough for the pilot; GP_Standard_D2ds_v5 for real load."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_user_connections" {
  description = "Connections the Postgres server leaves to the apps (max_connections minus the slots Azure reserves); B1ms: 50 minus about 15. Verify with the diagnosis (diag-queries, SHOW max_connections)."
  type        = number
  default     = 35
}

variable "postgres_spare_connections" {
  description = "Connections kept free for the migration job, a diagnosis and a person with psql."
  type        = number
  default     = 6
}

variable "postgres_storage_mb" {
  type    = number
  default = 32768
}

variable "postgres_backup_days" {
  description = "Point-in-time restore window (7 to 35 days)."
  type        = number
  default     = 14
}

# --- Object storage: Cloudflare R2 (ADR 002) ----------------------------------------------------

variable "s3_endpoint_url" {
  description = "R2 endpoint with EU jurisdiction: https://<account-id>.eu.r2.cloudflarestorage.com"
  type        = string
}

variable "s3_access_key" {
  description = "R2 access key id (not secret on its own; the secret key goes to Key Vault)."
  type        = string
}

variable "s3_bucket_videos" {
  type    = string
  default = "hb-videos"
}

variable "s3_bucket_artifacts" {
  type    = string
  default = "hb-artifacts"
}

variable "media_direct" {
  description = "HLS segments straight from R2 with presigned URLs in the playlists (HB_MEDIA_DIRECT, ADR 002 point 7). Needs the CORS rule on the video bucket (README, step 5). false: segments go through the API and the web proxy (Azure egress)."
  type        = bool
  default     = true
}

# --- E-mail (ADR 009) ---------------------------------------------------------------------------

variable "email_from" {
  description = "Sender, e.g. \"Hallenblick <noreply@example.ch>\"."
  type        = string
}

variable "smtp_host" {
  type = string
}

variable "smtp_port" {
  type    = number
  default = 587
}

variable "smtp_username" {
  type    = string
  default = ""
}

variable "mail_domain" {
  description = "Domain mail is sent from through Azure Communication Services; empty: the domain of app_domain."
  type        = string
  default     = ""
}

variable "mail_sender" {
  description = "Local part of the sender address, e.g. noreply."
  type        = string
  default     = "noreply"
}

variable "mail_live" {
  description = "Set by the deploy once Azure verified the sending domain: links it and switches the apps to it."
  type        = bool
  default     = false
}

# --- Settings -----------------------------------------------------------------------------------

variable "operator_emails" {
  description = "Platform operators for /ops (named people with 2FA)."
  type        = list(string)
  default     = []
}

variable "billing_enforce" {
  description = "Enforce plan limits (needs the Stripe secrets). Off for the pilot."
  type        = bool
  default     = false
}

variable "gpu_backend" {
  description = "local runs the analysis on the CPU of the gpu-worker container (slow, fine for the pilot); modal once that backend is implemented."
  type        = string
  default     = "local"
}

variable "extra_env" {
  description = "Further non-secret HB_ settings, e.g. { HB_GOOGLE_CLIENT_ID = \"...\", HB_SUPPORT_EMAIL = \"...\" }."
  type        = map(string)
  default     = {}
}

variable "optional_secrets" {
  description = <<-EOT
    Names of environment variables whose value you have stored in Key Vault yourself, e.g.
    ["HB_GOOGLE_CLIENT_SECRET", "HB_STRIPE_SECRET_KEY"]. The Key Vault secret name is the variable
    name in lowercase with dashes (hb-google-client-secret). README, step 5.
  EOT
  type        = set(string)
  default     = []
}

# --- Sizing -------------------------------------------------------------------------------------

variable "paused" {
  description = "true scales every app to 0 replicas (nothing runs, no compute cost); stop Postgres separately (README, \"Pause\")."
  type        = bool
  default     = false
}

variable "web_min_replicas" {
  description = "1 avoids cold starts on the first request; 0 saves a little more."
  type        = number
  default     = 1
}

variable "gpu_worker_cpu" {
  type    = number
  default = 2
}

variable "gpu_worker_memory" {
  type    = string
  default = "4Gi"
}

# --- Mail data location and serverless GPU (docs/plans/staging-umzug-eu.md) ----------------------

variable "mail_data_location" {
  description = "Data location of Azure Communication Services: Switzerland (the first environment) or Europe. Changing it replaces the mail resources (new DNS records)."
  type        = string
  default     = "Switzerland"
}

variable "gpu" {
  description = "Run the analysis as a serverless T4 job (Consumption-GPU-NC8as-T4, scale to zero, at most one at a time) instead of the always-on CPU app. Only in regions with serverless GPUs (e.g. swedencentral, not switzerlandnorth) and with T4 quota."
  type        = bool
  default     = false
}

variable "gpu_max_video_minutes" {
  description = "Longest video the GPU analysis takes, minutes; longer ones end at once as «too long»."
  type        = number
  default     = 15
}

variable "gpu_job_timeout_s" {
  description = "Hard end of one GPU job execution (it works the queue in burst mode, several analyses in a row)."
  type        = number
  default     = 14400
}

variable "gpu_ball_model" {
  description = "Ball net for the GPU job: key in the artifacts bucket (uint8 file, ml/ball/onnx_u8.py)."
  type        = string
  default     = "models/ball/ball_hrp1_fp16_u8-8efd55d05333.onnx"
}

variable "gpu_ball_model_sha256" {
  type    = string
  default = "8efd55d0533301889c0b3715bff3fa708a9e4f9be3b2d8162a4c56377a70253f"
}

variable "gpu_budget_amount" {
  description = "Monthly budget of the GPU job in the billing currency: an alert when it is used up."
  type        = number
  default     = 30
}

variable "gpu_budget_warn" {
  description = "Earlier alert of the GPU budget, same currency."
  type        = number
  default     = 20
}

variable "kv_runner_role" {
  description = "Give whoever runs terraform the role «Key Vault Secrets Officer» on the vault (a new environment deployed from GitHub Actions; the first one has it from setup-github-deploy.sh)."
  type        = bool
  default     = false
}
