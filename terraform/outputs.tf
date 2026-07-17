output "gcp_project_id" {
  description = "Active GCP project (from var.gcp_project_id)"
  value       = var.gcp_project_id
}

output "region" {
  description = "Primary region"
  value       = var.region
}

output "environment" {
  description = "Apply-context environment label"
  value       = var.environment
}

output "name_prefix" {
  description = "Resource name prefix for this environment"
  value       = local.name_prefix
}

output "enabled_apis" {
  description = "APIs managed by this configuration"
  value       = sort([for s in google_project_service.required : s.service])
}

output "tfstate_bucket_names" {
  description = "Remote state bucket names by environment"
  value       = { for k, b in google_storage_bucket.tfstate : k => b.name }
}

output "tfstate_bucket_urls" {
  description = "gs:// URLs for state buckets"
  value       = { for k, b in google_storage_bucket.tfstate : k => "gs://${b.name}" }
}
