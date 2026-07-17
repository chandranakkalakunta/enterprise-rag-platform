# Phase 1.3 — Secret Manager secrets (CMEK-encrypted)
# Secret shells only — NO secret versions / real values in Terraform.
# Coordinator adds versions later via runbook (gcloud secrets versions add).

resource "google_secret_manager_secret" "oauth_client_id" {
  project   = var.gcp_project_id
  secret_id = "rag-oauth-client-id"

  labels = merge(
    local.common_labels,
    {
      purpose    = "oauth"
      managed_by = "terraform"
    }
  )

  replication {
    user_managed {
      replicas {
        location = var.region
        customer_managed_encryption {
          kms_key_name = google_kms_crypto_key.secrets.id
        }
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_kms_crypto_key_iam_member.secretmanager_service_agent,
  ]
}

resource "google_secret_manager_secret" "oauth_client_secret" {
  project   = var.gcp_project_id
  secret_id = "rag-oauth-client-secret"

  labels = merge(
    local.common_labels,
    {
      purpose    = "oauth"
      managed_by = "terraform"
    }
  )

  replication {
    user_managed {
      replicas {
        location = var.region
        customer_managed_encryption {
          kms_key_name = google_kms_crypto_key.secrets.id
        }
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_kms_crypto_key_iam_member.secretmanager_service_agent,
  ]
}
