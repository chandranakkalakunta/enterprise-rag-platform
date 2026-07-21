locals {
  name_prefix = "erp-${var.environment}"

  # Standard labels applied to all managed resources
  common_labels = merge(
    {
      project     = "enterprise-rag-platform"
      managed_by  = "terraform"
      environment = var.environment
    },
    var.labels,
    {
      # Ensure environment from var wins if labels also set it
      environment = var.environment
      managed_by  = "terraform"
    }
  )

  tfstate_soft_delete_seconds = var.tfstate_soft_delete_days * 24 * 60 * 60

  # Runtime + CI service accounts (account_id must be 6–30 chars, lowercase)
  service_accounts = {
    api = {
      account_id   = "sa-rag-api"
      display_name = "RAG API runtime"
      description  = "Cloud Run api service identity — query path, Vertex, secrets (least privilege; expanded later)"
    }
    ingest = {
      account_id   = "sa-rag-ingest"
      display_name = "RAG ingest worker runtime"
      description  = "Cloud Run ingest-worker identity — parse/embed/index jobs (least privilege; expanded later)"
    }
    web = {
      account_id   = "sa-rag-web"
      display_name = "RAG web runtime"
      description  = "Cloud Run web (Next.js) identity — serve UI only; no direct Vertex/GCS admin"
    }
    ci = {
      account_id   = "sa-rag-ci"
      display_name = "RAG CI deploy"
      description  = "GitHub Actions via WIF only — deploy images/revisions; NEVER JSON keys"
    }
  }

  # Project-level roles for CI
  # Phase 1.5: removed roles/storage.admin — use bucket-scoped objectAdmin on rag-docs-* only
  # Justifications documented in iam.tf
  ci_project_roles = toset([
    "roles/run.admin",
    "roles/secretmanager.secretAccessor",
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.editor",
    "roles/logging.logWriter",
  ])

  # Minimal project roles for runtime SAs (api / ingest / web)
  runtime_project_roles = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/secretmanager.secretAccessor",
  ])

  runtime_sa_keys = toset(["api", "ingest", "web"])

  # Application document buckets (one per environment)
  docs_environments = toset(["dev", "test", "prod"])

  # Object prefix convention (logical folders inside each bucket — not separate buckets)
  docs_prefixes = [
    "raw/",       # original uploads
    "versions/",  # immutable published document versions
    "assets/",    # multimodal assets (images, extracted tables)
    "processed/", # parse/chunk pipeline outputs
  ]
}
