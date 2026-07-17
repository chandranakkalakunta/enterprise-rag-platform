# Phase 1.6 — Cloud Run service stubs
# Placeholder public image only; real app images land in later phases.
# Runtime SAs: sa-rag-api / sa-rag-ingest / sa-rag-web (no JSON keys).
# Invoker: not public (allUsers) — verify via gcloud describe / authenticated smoke later.

locals {
  # Stub image: Google-maintained Cloud Run sample (not application code)
  cloud_run_stub_image = "us-docker.pkg.dev/cloudrun/container/hello"

  cloud_run_services = {
    api = {
      name        = "rag-api"
      sa_key      = "api"
      description = "Query API stub — replace image with FastAPI app in later phase"
    }
    ingest = {
      name        = "rag-ingest"
      sa_key      = "ingest"
      description = "Ingest worker stub — replace with async pipeline image later"
    }
    web = {
      name        = "rag-web"
      sa_key      = "web"
      description = "Web/PWA stub — replace with Next.js image later"
    }
  }

  # Static deploy metadata for stubs (avoid terraform timestamp() plan churn)
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
    purpose     = "stub"
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

depends_on = [
    google_project_service.required,
    google_service_account.rag,
  ]
}

# Optional: allow project members with run.invoker to call services.
# No allUsers — keep stubs non-public until auth is wired.
# CI already has roles/run.admin for deploy.
