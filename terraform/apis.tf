# Enable only the minimum required APIs for Phase 1 foundation.
# Idempotent: safe to re-apply. disable_on_destroy = false avoids accidental disable.

resource "google_project_service" "required" {
  for_each = toset(var.required_apis)

  project = var.gcp_project_id
  service = each.value

  disable_on_destroy         = false
  disable_dependent_services = false
}
