locals {
  name_prefix = "erp-${var.environment}"

  # Standard labels applied to all managed resources
  common_labels = merge(
    {
      project     = "enterprise-rag-platform"
      managed_by  = "terraform"
      environment = var.environment
    },
    var.labels,
    {
      # Ensure environment from var wins if labels also set it
      environment = var.environment
      managed_by  = "terraform"
    }
  )

  tfstate_soft_delete_seconds = var.tfstate_soft_delete_days * 24 * 60 * 60
}
