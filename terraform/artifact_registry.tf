# Phase 1.7 — Artifact Registry for CI-built container images
# sa-rag-ci already has roles/artifactregistry.writer (Phase 1.2).

resource "google_artifact_registry_repository" "containers" {
  project       = var.gcp_project_id
  location      = var.region
  repository_id = "rag-containers"
  description   = "Enterprise RAG container images (api, ingest, web)"
  format        = "DOCKER"

  labels = merge(
    local.common_labels,
    {
      purpose    = "containers"
      managed_by = "terraform"
    }
  )

  depends_on = [google_project_service.required]
}
