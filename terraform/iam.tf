# IAM grants — Phase 1.2 baseline (least privilege we know we need soon).
# Tighten storage/run scopes in later phases (bucket-level, no project storage.admin).
# NEVER grant roles/owner or create JSON keys.

# ── CI service account (sa-rag-ci) — project roles ───────────────────────────
# roles/run.admin              — deploy/update Cloud Run services (narrow later)
# roles/secretmanager.secretAccessor — read deploy-time secrets
# roles/artifactregistry.writer — push container images
# roles/cloudbuild.builds.editor — submit builds if using Cloud Build
# roles/logging.logWriter      — CI logs
# storage: bucket-scoped objectAdmin on rag-docs-* only (gcs.tf); NO project storage.admin

resource "google_project_iam_member" "ci" {
  for_each = local.ci_project_roles

  project = var.gcp_project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.rag["ci"].email}"
}

# CI may act as runtime SAs when deploying Cloud Run with those identities
# roles/iam.serviceAccountUser on each runtime SA (not project-wide actAs)
resource "google_service_account_iam_member" "ci_act_as_runtime" {
  for_each = local.runtime_sa_keys

  service_account_id = google_service_account.rag[each.key].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.rag["ci"].email}"
}

# ── Runtime service accounts (api / ingest / web) — minimal project roles ────
# roles/logging.logWriter              — structured Cloud Logging
# roles/monitoring.metricWriter        — custom/system metrics
# roles/secretmanager.secretAccessor   — app secrets at runtime (later wire specific secrets)
# Storage / Vertex / specific bucket roles: deferred to later phases (bucket-scoped)

resource "google_project_iam_member" "runtime" {
  for_each = {
    for pair in setproduct(local.runtime_sa_keys, local.runtime_project_roles) :
    "${pair[0]}|${pair[1]}" => {
      sa_key = pair[0]
      role   = pair[1]
    }
  }

  project = var.gcp_project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.rag[each.value.sa_key].email}"
}
