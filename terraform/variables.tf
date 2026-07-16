variable "gcp_project_id" {
  description = "GCP project ID. Set via tfvars or -var; do not hardcode real project IDs in code or docs."
  type        = string
  default     = "your-gcp-project-id"
}

variable "region" {
  description = "Primary GCP region (never hardcode in application code)"
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Deployment environment label"
  type        = string
  default     = "dev"
}

variable "labels" {
  description = "Common resource labels"
  type        = map(string)
  default = {
    project     = "enterprise-rag-platform"
    managed_by  = "terraform"
    environment = "dev"
  }
}
