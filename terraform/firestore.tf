# Firestore Native metadata database (Phase 2.2 / ADR-0006)
# Location locked to asia-south1 with the rest of the stack.

resource "google_firestore_database" "metadata" {
  project     = var.gcp_project_id
  name        = var.firestore_database_name
  location_id = var.firestore_location_id
  type        = "FIRESTORE_NATIVE"

  # Native mode only (not Datastore mode)
  concurrency_mode            = "PESSIMISTIC"
  app_engine_integration_mode = "DISABLED"
  delete_protection_state     = "DELETE_PROTECTION_ENABLED"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_DISABLED"

  depends_on = [google_project_service.required]
}

# Least-privilege metadata R/W for API and ingest runtimes.
# roles/datastore.user is the standard Firestore data-plane role.
resource "google_project_iam_member" "firestore_data" {
  for_each = toset(["api", "ingest"])

  project = var.gcp_project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.rag[each.key].email}"

  depends_on = [
    google_firestore_database.metadata,
    google_service_account.rag,
  ]
}
