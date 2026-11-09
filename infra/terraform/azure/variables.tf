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
