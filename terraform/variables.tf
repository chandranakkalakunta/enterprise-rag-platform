variable "gcp_project_id" {
  description = "GCP project ID. Set via tfvars or -var. Application code must never hard-code this value."
  type        = string
  default     = "enterprise-rag-platform-502711"
}

variable "region" {
  description = "Primary GCP region (never hard-code in application code)"
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Deployment environment label for this workspace apply context"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be one of: dev, test, prod."
  }
}

variable "labels" {
  description = "Common resource labels merged with standard managed-by / environment labels"
  type        = map(string)
  default = {
    project    = "enterprise-rag-platform"
    managed_by = "terraform"
  }
}

variable "required_apis" {
  description = "Minimum Google APIs to enable for Phase 1 foundation"
  type        = list(string)
  default = [
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "serviceusage.googleapis.com",
    "cloudkms.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "aiplatform.googleapis.com",
  ]
}

variable "tfstate_environments" {
  description = "Environments for which remote state buckets are created (all envs, once per project)"
  type        = list(string)
  default     = ["dev", "test", "prod"]
}

variable "tfstate_soft_delete_days" {
  description = "Soft-delete retention for state buckets (days)"
  type        = number
  default     = 7
}

variable "github_repository" {
  description = "GitHub org/repo allowed to impersonate sa-rag-ci via WIF (attribute.repository)"
  type        = string
  default     = "chandranakkalakunta/enterprise-rag-platform"
}

variable "wif_pool_id" {
  description = "Workload Identity Pool ID (global)"
  type        = string
  default     = "rag-github-pool"
}

variable "wif_provider_id" {
  description = "Workload Identity Pool Provider ID for GitHub OIDC"
  type        = string
  default     = "github-oidc"
}
