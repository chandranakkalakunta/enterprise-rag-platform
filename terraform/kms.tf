# Phase 1.3 — CMEK foundation
# Key ring + crypto keys for future GCS and Secret Manager encryption.
# NEVER create JSON SA keys. Grant cryptoKeyEncrypterDecrypter only to known principals.

resource "google_kms_key_ring" "rag" {
  project  = var.gcp_project_id
  name     = "rag-keyring"
  location = var.region

  depends_on = [google_project_service.required]
}

resource "google_kms_crypto_key" "gcs" {
  name            = "rag-gcs-key"
  key_ring        = google_kms_key_ring.rag.id
  purpose         = "ENCRYPT_DECRYPT"
  rotation_period = "7776000s" # 90 days

  version_template {
    algorithm = "GOOGLE_SYMMETRIC_ENCRYPTION"
  }

  labels = merge(
    local.common_labels,
    {
      purpose    = "gcs-cmek"
      managed_by = "terraform"
    }
  )
}

resource "google_kms_crypto_key" "secrets" {
  name            = "rag-secrets-key"
  key_ring        = google_kms_key_ring.rag.id
  purpose         = "ENCRYPT_DECRYPT"
  rotation_period = "7776000s" # 90 days

  version_template {
    algorithm = "GOOGLE_SYMMETRIC_ENCRYPTION"
  }

  labels = merge(
    local.common_labels,
    {
      purpose    = "secretmanager-cmek"
      managed_by = "terraform"
    }
  )
}

# Secret Manager service agent (created via service identity API — not a user SA key).
# Must use the CMEK to encrypt/decrypt secret payloads; without this grant, CMEK secrets fail.
resource "google_project_service_identity" "secretmanager" {
  provider = google-beta
  project  = var.gcp_project_id
  service  = "secretmanager.googleapis.com"

  depends_on = [google_project_service.required]
}

resource "google_kms_crypto_key_iam_member" "secretmanager_service_agent" {
  crypto_key_id = google_kms_crypto_key.secrets.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = google_project_service_identity.secretmanager.member
}

# Cloud Storage service agent KMS grant: see google_project_service_identity.storage
# and google_kms_crypto_key_iam_member.storage_service_agent_gcs_key in gcs.tf (Phase 1.4).

# Runtime + CI custom SAs — use keys for application encrypt/decrypt operations
resource "google_kms_crypto_key_iam_member" "sa_gcs_key" {
  for_each = google_service_account.rag

  crypto_key_id = google_kms_crypto_key.gcs.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${each.value.email}"
}

resource "google_kms_crypto_key_iam_member" "sa_secrets_key" {
  for_each = google_service_account.rag

  crypto_key_id = google_kms_crypto_key.secrets.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${each.value.email}"
}
