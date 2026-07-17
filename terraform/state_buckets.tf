# Remote Terraform state buckets — one per environment (dev / test / prod).
# Created in a single foundation apply so every env has a ready backend target.
# Bucket names (locked):
#   enterprise-rag-tfstate-dev
#   enterprise-rag-tfstate-test
#   enterprise-rag-tfstate-prod

resource "google_storage_bucket" "tfstate" {
  for_each = toset(var.tfstate_environments)

  name                        = "enterprise-rag-tfstate-${each.key}"
  project                     = var.gcp_project_id
  location                    = var.region
  storage_class               = "STANDARD"
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = local.tfstate_soft_delete_seconds
  }

  labels = merge(
    local.common_labels,
    {
      environment = each.key
      purpose     = "tfstate"
      managed_by  = "terraform"
    }
  )

  depends_on = [google_project_service.required]
}
