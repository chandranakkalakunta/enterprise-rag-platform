output "gcp_project_id" {
  description = "Active GCP project (from var.gcp_project_id)"
  value       = var.gcp_project_id
}

output "gcp_project_number" {
  description = "Numeric project number (for WIF resource names)"
  value       = data.google_project.current.number
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

# ── Phase 1.2: identities ────────────────────────────────────────────────────

output "service_account_emails" {
  description = "Custom service account emails by key (api, ingest, web, ci)"
  value       = { for k, sa in google_service_account.rag : k => sa.email }
}

output "service_account_ids" {
  description = "Fully qualified SA resource names"
  value       = { for k, sa in google_service_account.rag : k => sa.name }
}

output "wif_pool_id" {
  description = "Workload Identity Pool ID"
  value       = google_iam_workload_identity_pool.github.workload_identity_pool_id
}

output "wif_pool_name" {
  description = "Full resource name of the WIF pool"
  value       = google_iam_workload_identity_pool.github.name
}

output "wif_provider_id" {
  description = "Workload Identity Pool Provider ID"
  value       = google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id
}

output "wif_provider_name" {
  description = "Full resource name of the GitHub OIDC provider (use in GitHub Actions)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "wif_github_principal_set" {
  description = "Principal set for the allowed GitHub repository"
  value       = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

output "github_actions_workload_identity_provider" {
  description = "Value for GitHub Actions google-github-actions/auth workload_identity_provider input"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_actions_service_account" {
  description = "Value for GitHub Actions google-github-actions/auth service_account input"
  value       = google_service_account.rag["ci"].email
}
