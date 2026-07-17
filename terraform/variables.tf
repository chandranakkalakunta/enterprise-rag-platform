variable "gcp_project_id" {
  description = "GCP project ID. Set via tfvars or -var. Application code must read from env/config only — never hard-code. Default is the current dev project example."
  type        = string
  default     = "enterprise-rag-platform-502711"
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
