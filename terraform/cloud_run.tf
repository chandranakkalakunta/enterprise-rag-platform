# Phase 1.6 — Cloud Run services (bootstrap image + SA/scaling owned by Terraform)
# Phase 2.3 — lifecycle ignore so CI (WIF) owns container image / deploy metadata.
# Runtime SAs: sa-rag-api / sa-rag-ingest / sa-rag-web (no JSON keys).
# Invoker: not public (allUsers) — verify via gcloud describe / authenticated smoke later.

locals {
  # Bootstrap / fallback image only. Real images are deployed by GitHub Actions CI.
  # Do NOT remove lifecycle.ignore_changes on image — full apply would roll back CI tags.
  cloud_run_stub_image = "us-docker.pkg.dev/cloudrun/container/hello"

  cloud_run_services = {
    api = {
      name        = "rag-api"
      sa_key      = "api"
      description = "Query API — image managed by CI after bootstrap"
    }
    ingest = {
      name        = "rag-ingest"
      sa_key      = "ingest"
      description = "Ingest worker — image managed by CI after bootstrap"
    }
    web = {
      name        = "rag-web"
      sa_key      = "web"
      description = "Web/PWA — image managed by CI after bootstrap"
    }
  }

  # Bootstrap deploy metadata (ignored after first CI deploy via lifecycle)
  stub_app_version = "phase-1-6-stub"
  stub_deployed_at = "2026-07-17T12:00:00Z"
}

resource "google_cloud_run_v2_service" "rag" {
  for_each = local.cloud_run_services

  project  = var.gcp_project_id
  name     = each.value.name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = each.value.name
    purpose     = "runtime"
  }

  template {
    service_account = google_service_account.rag[each.value.sa_key].email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = local.cloud_run_stub_image

      env {
        name  = "APP_VERSION"
        value = local.stub_app_version
      }
      env {
        name  = "DEPLOYED_AT"
        value = local.stub_deployed_at
      }
      env {
        name  = "SERVICE_NAME"
        value = each.value.name
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  # CI owns image + revision deploy metadata (APP_VERSION / DEPLOYED_AT).
  # Without this, terraform apply reverts Artifact Registry tags to the hello stub
  # (see docs/issues_log.md Phase 2.2).
  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers,
      labels["purpose"],
    ]
  }

  depends_on = [
    google_project_service.required,
    google_service_account.rag,
  ]
}

# Optional: allow project members with run.invoker to call services.
# No allUsers — keep stubs non-public until auth is wired.
# CI already has roles/run.admin for deploy.
