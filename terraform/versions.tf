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

  # Partial GCS backend — configure per env:
  #   terraform init -reconfigure -backend-config=environments/<env>/backend.hcl
  # See docs/runbooks/terraform-bootstrap.md
  backend "gcs" {}
}
