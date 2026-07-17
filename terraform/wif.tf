# Workload Identity Federation — GitHub Actions → sa-rag-ci (keyless)
# Restricts tokens to a single repository via attribute_condition.

data "google_project" "current" {
  project_id = var.gcp_project_id
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.gcp_project_id
  workload_identity_pool_id = var.wif_pool_id
  display_name              = "RAG GitHub Actions"
  description               = "OIDC pool for GitHub Actions deploy (zero JSON SA keys)"
  disabled                  = false

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.gcp_project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = var.wif_provider_id
  display_name                       = "GitHub OIDC"
  description                        = "Trust GitHub Actions OIDC for ${var.github_repository} only"
  disabled                           = false

  # Only this repository may mint identity tokens accepted by the pool
  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow GitHub repo principal set to impersonate sa-rag-ci
resource "google_service_account_iam_member" "ci_workload_identity_user" {
  service_account_id = google_service_account.rag["ci"].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}
