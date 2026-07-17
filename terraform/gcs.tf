# Phase 1.4 — Application document GCS buckets with CMEK
# Prefix convention (logical paths inside each bucket — see docs/runbooks/gcs-document-buckets.md):
#   raw/       original uploads
#   versions/  immutable published document versions
#   assets/    multimodal assets
#   processed/ pipeline outputs
#
# Project-level roles/storage.admin on sa-rag-ci remains from Phase 1.2 (temporary).
# These bucket IAM bindings begin the path to removing project-level storage.admin (BL-FND-24).

locals {
  docs_soft_delete_seconds = var.docs_soft_delete_days * 24 * 60 * 60
}

# Cloud Storage project service agent (not a user JSON key).
# Format is fixed by GCP: service-PROJECT_NUMBER@gs-project-accounts.iam.gserviceaccount.com
# google_project_service_identity for storage does not always export email/member.
locals {
  gcs_service_agent_member = "serviceAccount:service-${data.google_project.current.number}@gs-project-accounts.iam.gserviceaccount.com"
}

resource "google_kms_crypto_key_iam_member" "storage_service_agent_gcs_key" {
  crypto_key_id = google_kms_crypto_key.gcs.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = local.gcs_service_agent_member

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket" "docs" {
  for_each = local.docs_environments

  name                        = "rag-docs-${each.key}"
  project                     = var.gcp_project_id
  location                    = var.region
  storage_class               = "STANDARD"
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = local.docs_soft_delete_seconds
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.gcs.id
  }

  # Delete non-current (versioned) objects after N days once a newer version exists
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions         = 1
      days_since_noncurrent_time = var.docs_noncurrent_version_days
      with_state                 = "ARCHIVED"
    }
  }

  labels = merge(
    {
      project     = "enterprise-rag-platform"
      managed_by  = "terraform"
      environment = each.key
      purpose     = "documents"
    }
  )

  depends_on = [
    google_project_service.required,
    google_kms_crypto_key_iam_member.storage_service_agent_gcs_key,
    google_kms_crypto_key_iam_member.sa_gcs_key,
  ]
}

# ── Bucket IAM (least privilege; scoped to these buckets only) ───────────────

# Ingest worker: full object control for upload/process/write pipeline outputs
resource "google_storage_bucket_iam_member" "docs_ingest_object_admin" {
  for_each = google_storage_bucket.docs

  bucket = each.value.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag["ingest"].email}"
}

# API: read + create objects (serve/download assets; limited write if needed)
resource "google_storage_bucket_iam_member" "docs_api_object_viewer" {
  for_each = google_storage_bucket.docs

  bucket = each.value.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.rag["api"].email}"
}

resource "google_storage_bucket_iam_member" "docs_api_object_creator" {
  for_each = google_storage_bucket.docs

  bucket = each.value.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.rag["api"].email}"
}

# CI: object admin on app buckets only (still has project storage.admin from 1.2 — remove later)
resource "google_storage_bucket_iam_member" "docs_ci_object_admin" {
  for_each = google_storage_bucket.docs

  bucket = each.value.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag["ci"].email}"
}
