output "resource_group" {
  value = azurerm_resource_group.this.name
}

output "registry" {
  description = "Login server for az acr build."
  value       = azurerm_container_registry.this.login_server
}

output "registry_name" {
  value = azurerm_container_registry.this.name
}

output "key_vault" {
  value = azurerm_key_vault.this.name
}

output "web_app" {
  value = azurerm_container_app.web.name
}

output "web_default_fqdn" {
  description = "Target of the CNAME record for app_domain."
  value       = azurerm_container_app.web.ingress[0].fqdn
}

output "custom_domain_verification_id" {
  description = "Value of the TXT record asuid.<app_domain>."
  value       = azurerm_container_app.web.custom_domain_verification_id
}

output "migrate_job" {
  value = azurerm_container_app_job.migrate.name
}

output "postgres_host" {
  value = azurerm_postgresql_flexible_server.this.fqdn
}

output "container_app_environment" {
  value = azurerm_container_app_environment.this.name
}
