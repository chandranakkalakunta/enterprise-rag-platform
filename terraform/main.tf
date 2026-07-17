# Enterprise RAG Platform — Terraform root module (skeleton)
# Phase 0: structure only. No resources applied until Phase 1 foundation.
#
# GCP project: var.gcp_project_id (default example: enterprise-rag-platform-502711)
# Application code must never hard-code project ID; use env/config only.

locals {
  name_prefix = "erp-${var.environment}"
}

# Placeholder: enable APIs in Phase 1 via google_project_service (idempotent).
# Example services (not created yet):
#   - run.googleapis.com
#   - aiplatform.googleapis.com
#   - storage.googleapis.com
#   - secretmanager.googleapis.com
#   - cloudkms.googleapis.com
#   - bigquery.googleapis.com
#   - firestore.googleapis.com
#   - cloudbuild.googleapis.com
#   - iam.googleapis.com
#   - artifactregistry.googleapis.com

output "gcp_project_id" {
  description = "Active GCP project (from var.gcp_project_id)"
  value       = var.gcp_project_id
}

output "region" {
  description = "Primary region"
  value       = var.region
}

output "name_prefix" {
  description = "Resource name prefix"
  value       = local.name_prefix
}
