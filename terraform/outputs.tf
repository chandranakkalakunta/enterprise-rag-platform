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

# ── Phase 1.3: CMEK + secrets ────────────────────────────────────────────────

output "kms_key_ring_id" {
  description = "KMS key ring resource ID"
  value       = google_kms_key_ring.rag.id
}

output "kms_key_ring_name" {
  description = "KMS key ring short name"
  value       = google_kms_key_ring.rag.name
}

output "kms_crypto_key_gcs_id" {
  description = "Full resource name of rag-gcs-key (future GCS CMEK)"
  value       = google_kms_crypto_key.gcs.id
}

output "kms_crypto_key_secrets_id" {
  description = "Full resource name of rag-secrets-key (Secret Manager CMEK)"
  value       = google_kms_crypto_key.secrets.id
}

output "secret_ids" {
  description = "Secret Manager secret IDs (no versions/values in Terraform)"
  value = {
    oauth_client_id     = google_secret_manager_secret.oauth_client_id.secret_id
    oauth_client_secret = google_secret_manager_secret.oauth_client_secret.secret_id
  }
}

output "secret_resource_names" {
  description = "Fully qualified secret resource names"
  value = {
    oauth_client_id     = google_secret_manager_secret.oauth_client_id.name
    oauth_client_secret = google_secret_manager_secret.oauth_client_secret.name
  }
}

# ── Phase 1.4: application document buckets ──────────────────────────────────

output "docs_bucket_names" {
  description = "Application document bucket names by environment"
  value       = { for k, b in google_storage_bucket.docs : k => b.name }
}

output "docs_bucket_urls" {
  description = "gs:// URLs for application document buckets"
  value       = { for k, b in google_storage_bucket.docs : k => "gs://${b.name}" }
}

output "docs_bucket_prefixes" {
  description = "Logical prefix convention inside each docs bucket"
  value       = local.docs_prefixes
}

output "docs_bucket_kms_key" {
  description = "CMEK used as default encryption on document buckets"
  value       = google_kms_crypto_key.gcs.id
}

# ── Phase 1.6: Cloud Run stubs ───────────────────────────────────────────────

output "cloud_run_service_names" {
  description = "Cloud Run service names by key"
  value       = { for k, s in google_cloud_run_v2_service.rag : k => s.name }
}

output "cloud_run_service_urls" {
  description = "Cloud Run service URIs (use status.url equivalent — uri field)"
  value       = { for k, s in google_cloud_run_v2_service.rag : k => s.uri }
}

output "cloud_run_service_accounts" {
  description = "Runtime SA email attached to each Cloud Run service"
  value = {
    for k, s in local.cloud_run_services :
    k => google_service_account.rag[s.sa_key].email
  }
}

# ── Phase 1.7: Artifact Registry ─────────────────────────────────────────────

output "artifact_registry_repository" {
  description = "Artifact Registry repository ID"
  value       = google_artifact_registry_repository.containers.repository_id
}

output "artifact_registry_location" {
  description = "Artifact Registry location"
  value       = google_artifact_registry_repository.containers.location
}

output "artifact_registry_docker_base" {
  description = "Base path for docker push/pull (without image name/tag)"
  value       = "${var.region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.containers.repository_id}"
}

# ── Phase 2.2: Firestore metadata ────────────────────────────────────────────

output "firestore_database_name" {
  description = "Firestore database ID"
  value       = google_firestore_database.metadata.name
}

output "firestore_database_id" {
  description = "Full Firestore database resource ID"
  value       = google_firestore_database.metadata.id
}

output "firestore_location_id" {
  description = "Firestore location"
  value       = google_firestore_database.metadata.location_id
}

output "firestore_type" {
  description = "Firestore database type (expect FIRESTORE_NATIVE)"
  value       = google_firestore_database.metadata.type
}

output "firestore_data_plane_members" {
  description = "Principals granted roles/datastore.user for metadata R/W"
  value = [
    for k in ["api", "ingest"] :
    google_service_account.rag[k].email
  ]
}

# ── Phase 3.2: Vector Search ─────────────────────────────────────────────────

output "vector_search_enabled" {
  description = "Whether Vector Search resources are managed"
  value       = var.enable_vector_search
}

output "vector_search_region" {
  description = "Region of Vector Search resources"
  value       = var.vector_search_region
}

output "vector_search_dimensions" {
  description = "Index embedding dimensions"
  value       = var.vector_search_dimensions
}

output "vector_search_index_id" {
  description = "Short Vector Search index id (empty if disabled)"
  value       = var.enable_vector_search ? google_vertex_ai_index.rag_docs[0].name : ""
}

output "vector_search_index_resource_name" {
  description = "Full resource name of the Vector Search index"
  value       = var.enable_vector_search ? google_vertex_ai_index.rag_docs[0].id : ""
}

output "vector_search_endpoint_id" {
  description = "Short index endpoint id"
  value       = var.enable_vector_search ? google_vertex_ai_index_endpoint.rag_docs[0].name : ""
}

output "vector_search_endpoint_resource_name" {
  description = "Full resource name of the index endpoint"
  value       = var.enable_vector_search ? google_vertex_ai_index_endpoint.rag_docs[0].id : ""
}

output "vector_search_deployed_index_id" {
  description = "Deployed index id used in FindNeighbors / query clients"
  value       = var.enable_vector_search ? google_vertex_ai_index_endpoint_deployed_index.rag_docs[0].deployed_index_id : ""
}

output "vector_search_public_endpoint_domain" {
  description = "Public endpoint domain name when public_endpoint_enabled"
  value = var.enable_vector_search ? try(
    google_vertex_ai_index_endpoint.rag_docs[0].public_endpoint_domain_name,
    ""
  ) : ""
}
