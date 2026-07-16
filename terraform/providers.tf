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
  # backend "gcs" {
  #   bucket = "sport-slot-dev-tfstate"
  #   prefix = "enterprise-rag-platform"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
