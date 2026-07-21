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
  description = "Minimum Google APIs to enable for foundation + edge (Phase 6.1)"
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
    "firestore.googleapis.com",
    "compute.googleapis.com",
    "iap.googleapis.com",
  ]
}

# ── Phase 6.1: Production edge (HTTPS LB + IAP) ───────────────────────────────

variable "enable_edge" {
  description = "Provision global HTTPS LB + IAP + serverless NEGs (ADR-0012). Default false until Coordinator opts in."
  type        = bool
  default     = false
}

variable "edge_domain" {
  description = "FQDN for managed SSL (e.g. rag.dev.example.com). Required for Google-managed cert when enable_edge and no edge_ssl_certificate_self_link."
  type        = string
  default     = ""
}

variable "edge_ssl_certificate_self_link" {
  description = "Optional pre-created SSL cert self_link. When set, skips google_compute_managed_ssl_certificate."
  type        = string
  default     = ""
}

variable "iap_access_members" {
  description = "Principals granted roles/iap.httpsResourceAccessor on edge backends (e.g. user:you@gmail.com). Never allUsers."
  type        = list(string)
  default     = []
}

variable "iap_support_email" {
  description = "Support email for IAP OAuth brand (required if create_iap_brand=true)"
  type        = string
  default     = ""
}

variable "create_iap_brand" {
  description = "Create google_iap_brand (often one-time / org-restricted). Prefer Console brand then set create_iap_client or existing OAuth client vars."
  type        = bool
  default     = false
}

variable "create_iap_client" {
  description = "Create google_iap_client under project brand for IAP backends"
  type        = bool
  default     = false
}

variable "iap_brand_name" {
  description = "Existing IAP brand resource name (projects/PROJECT_NUMBER/brands/BRAND_ID) when create_iap_brand=false but create_iap_client=true"
  type        = string
  default     = ""
}

variable "iap_oauth_client_id" {
  description = "Existing IAP OAuth client ID (when not creating google_iap_client)"
  type        = string
  default     = ""
}

variable "iap_oauth_client_secret" {
  description = "Existing IAP OAuth client secret (sensitive; prefer TF_VAR_ or secret-backed apply)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "firestore_database_name" {
  description = "Firestore database ID (use (default) for the default database)"
  type        = string
  default     = "(default)"
}

variable "firestore_location_id" {
  description = "Firestore multi-region or region location (must match product choice)"
  type        = string
  default     = "asia-south1"
}

# ── Phase 3.2: Vertex AI Vector Search ───────────────────────────────────────

variable "enable_vector_search" {
  description = "Provision Vertex AI Vector Search index + endpoint (dev cost; can disable for local-only workspaces)"
  type        = bool
  default     = true
}

variable "vector_search_region" {
  description = "Region for Vector Search index/endpoint (prefer asia-south1; override if unsupported)"
  type        = string
  default     = "asia-south1"
}

variable "vector_search_dimensions" {
  description = "Embedding dimensions (text-embedding-005 default output = 768)"
  type        = number
  default     = 768
}

variable "vector_search_approximate_neighbors_count" {
  description = "ANN approximate neighbors count for index config"
  type        = number
  default     = 10
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

variable "docs_soft_delete_days" {
  description = "Soft-delete retention for application document buckets (days)"
  type        = number
  default     = 7
}

variable "docs_noncurrent_version_days" {
  description = "Delete non-current object versions after this many days"
  type        = number
  default     = 90
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
