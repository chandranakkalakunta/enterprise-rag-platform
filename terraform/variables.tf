variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "sport-slot-dev"
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
