# Custom service accounts — Phase 1.2
# NEVER create or download JSON keys for these accounts.
# Runtime SAs attach to Cloud Run; sa-rag-ci is impersonated only via WIF (GitHub OIDC).

resource "google_service_account" "rag" {
  for_each = local.service_accounts

  project      = var.gcp_project_id
  account_id   = each.value.account_id
  display_name = each.value.display_name
  description  = each.value.description
  disabled     = false

  depends_on = [google_project_service.required]
}
