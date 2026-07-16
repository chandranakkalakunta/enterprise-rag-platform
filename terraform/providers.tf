terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.40"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.40"
    }
  }

  # Remote state backend — configure after GCS state bucket exists (Phase 1).
  # Backend blocks cannot interpolate variables; set the bucket name explicitly
  # in a backend.hcl or partial config (derived from your gcp_project_id at apply time).
  # backend "gcs" {
  #   bucket = "your-gcp-project-id-tfstate"
  #   prefix = "enterprise-rag-platform"
  # }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.region
}
