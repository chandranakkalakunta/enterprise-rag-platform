# Phase 6.1 — Production edge (ADR-0012)
# Global HTTPS Application Load Balancer + IAP + serverless NEGs → rag-web / rag-api
# Feature flag: var.enable_edge (default false)
# NEVER grant allUsers / public run.invoker.

locals {
  edge_enabled = var.enable_edge

  # Prefer managed cert when domain set; else pre-created cert self_link
  edge_use_managed_cert = local.edge_enabled && var.edge_domain != "" && var.edge_ssl_certificate_self_link == ""
  edge_has_ssl = local.edge_enabled && (
    var.edge_ssl_certificate_self_link != "" || var.edge_domain != ""
  )

  edge_ssl_certificates = local.edge_enabled ? (
    var.edge_ssl_certificate_self_link != "" ? [var.edge_ssl_certificate_self_link] : (
      local.edge_use_managed_cert ? [google_compute_managed_ssl_certificate.edge[0].id] : []
    )
  ) : []

  iap_sa_member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-iap.iam.gserviceaccount.com"

  # OAuth client for IAP block on backend services
  edge_iap_client_id = local.edge_enabled ? (
    var.create_iap_client ? google_iap_client.edge[0].client_id : var.iap_oauth_client_id
  ) : ""

  edge_iap_client_secret = local.edge_enabled ? (
    var.create_iap_client ? google_iap_client.edge[0].secret : var.iap_oauth_client_secret
  ) : ""

  edge_api_paths = [
    "/api",
    "/api/*",
    "/health",
    "/ready",
    "/docs",
    "/docs/*",
    "/openapi.json",
    "/redoc",
  ]
}

# Fail fast on incomplete edge configuration
check "edge_ssl_when_enabled" {
  assert {
    condition     = !var.enable_edge || length(local.edge_ssl_certificates) > 0
    error_message = "enable_edge=true requires edge_domain (managed cert) or edge_ssl_certificate_self_link."
  }
}

check "edge_iap_credentials_when_enabled" {
  assert {
    condition = !var.enable_edge || (
      (var.create_iap_client && (var.create_iap_brand || var.iap_brand_name != "")) ||
      (var.iap_oauth_client_id != "" && var.iap_oauth_client_secret != "")
    )
    error_message = "enable_edge=true requires create_iap_client (+ brand) or both iap_oauth_client_id and iap_oauth_client_secret."
  }
}

check "edge_iap_members_when_enabled" {
  assert {
    condition     = !var.enable_edge || length(var.iap_access_members) > 0
    error_message = "enable_edge=true requires iap_access_members (user: or group: principals). Never allUsers."
  }
}

check "edge_no_allusers_iap_members" {
  assert {
    condition = length([
      for m in var.iap_access_members : m
      if can(regex("(?i)^allusers$|^allauthenticatedusers$|^allUsers$|^allAuthenticatedUsers$", m))
      || startswith(lower(m), "allusers")
      || startswith(lower(m), "allauthenticatedusers")
    ]) == 0
    error_message = "iap_access_members must not include allUsers or allAuthenticatedUsers."
  }
}

# ── IAP OAuth brand / client (optional; brand is often Console one-time) ──────

resource "google_iap_brand" "edge" {
  count = local.edge_enabled && var.create_iap_brand ? 1 : 0

  project           = var.gcp_project_id
  support_email     = var.iap_support_email
  application_title = "Enterprise RAG Platform (${var.environment})"

  depends_on = [google_project_service.required]
}

resource "google_iap_client" "edge" {
  count = local.edge_enabled && var.create_iap_client ? 1 : 0

  display_name = "erp-${var.environment}-iap-edge"
  brand = (
    var.create_iap_brand
    ? google_iap_brand.edge[0].name
    : var.iap_brand_name
  )
}

# ── Serverless NEGs ──────────────────────────────────────────────────────────

resource "google_compute_region_network_endpoint_group" "edge_web" {
  count = local.edge_enabled ? 1 : 0

  project               = var.gcp_project_id
  name                  = "${local.name_prefix}-neg-web"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.rag["web"].name
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service.rag,
  ]
}

resource "google_compute_region_network_endpoint_group" "edge_api" {
  count = local.edge_enabled ? 1 : 0

  project               = var.gcp_project_id
  name                  = "${local.name_prefix}-neg-api"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.rag["api"].name
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service.rag,
  ]
}

# ── Backend services + IAP ───────────────────────────────────────────────────

resource "google_compute_backend_service" "edge_web" {
  count = local.edge_enabled ? 1 : 0

  project               = var.gcp_project_id
  name                  = "${local.name_prefix}-bes-web"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 30
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.edge_web[0].id
  }

  # Presence of iap {} enables IAP (provider ~> 5.40)
  iap {
    oauth2_client_id     = local.edge_iap_client_id
    oauth2_client_secret = local.edge_iap_client_secret
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }

  depends_on = [google_project_service.required]
}

resource "google_compute_backend_service" "edge_api" {
  count = local.edge_enabled ? 1 : 0

  project               = var.gcp_project_id
  name                  = "${local.name_prefix}-bes-api"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 120
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.edge_api[0].id
  }

  iap {
    oauth2_client_id     = local.edge_iap_client_id
    oauth2_client_secret = local.edge_iap_client_secret
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }

  depends_on = [google_project_service.required]
}

# IAP access: who may pass IAP (humans / groups). Never allUsers.
resource "google_iap_web_backend_service_iam_member" "edge_web_access" {
  for_each = local.edge_enabled ? toset(var.iap_access_members) : toset([])

  project             = var.gcp_project_id
  web_backend_service = google_compute_backend_service.edge_web[0].name
  role                = "roles/iap.httpsResourceAccessor"
  member              = each.value
}

resource "google_iap_web_backend_service_iam_member" "edge_api_access" {
  for_each = local.edge_enabled ? toset(var.iap_access_members) : toset([])

  project             = var.gcp_project_id
  web_backend_service = google_compute_backend_service.edge_api[0].name
  role                = "roles/iap.httpsResourceAccessor"
  member              = each.value
}

# IAP service agent invokes Cloud Run (not public invoker)
resource "google_cloud_run_v2_service_iam_member" "iap_invoker_web" {
  count = local.edge_enabled ? 1 : 0

  project  = var.gcp_project_id
  location = var.region
  name     = google_cloud_run_v2_service.rag["web"].name
  role     = "roles/run.invoker"
  member   = local.iap_sa_member
}

resource "google_cloud_run_v2_service_iam_member" "iap_invoker_api" {
  count = local.edge_enabled ? 1 : 0

  project  = var.gcp_project_id
  location = var.region
  name     = google_cloud_run_v2_service.rag["api"].name
  role     = "roles/run.invoker"
  member   = local.iap_sa_member
}

# ── URL map: path routing (full path preserved — FastAPI expects /api/v1/...) ─

resource "google_compute_url_map" "edge" {
  count = local.edge_enabled ? 1 : 0

  project         = var.gcp_project_id
  name            = "${local.name_prefix}-urlmap"
  default_service = google_compute_backend_service.edge_web[0].id

  host_rule {
    hosts        = [var.edge_domain != "" ? var.edge_domain : "*"]
    path_matcher = "main"
  }

  path_matcher {
    name            = "main"
    default_service = google_compute_backend_service.edge_web[0].id

    path_rule {
      paths   = local.edge_api_paths
      service = google_compute_backend_service.edge_api[0].id
    }
  }
}

# Optional HTTP → HTTPS redirect (only useful with real hostname)
resource "google_compute_url_map" "edge_http_redirect" {
  count = local.edge_enabled && var.edge_domain != "" ? 1 : 0

  project = var.gcp_project_id
  name    = "${local.name_prefix}-urlmap-http-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "edge_redirect" {
  count = local.edge_enabled && var.edge_domain != "" ? 1 : 0

  project = var.gcp_project_id
  name    = "${local.name_prefix}-http-proxy-redirect"
  url_map = google_compute_url_map.edge_http_redirect[0].id
}

resource "google_compute_global_forwarding_rule" "edge_http" {
  count = local.edge_enabled && var.edge_domain != "" ? 1 : 0

  project               = var.gcp_project_id
  name                  = "${local.name_prefix}-fwd-http"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.edge_redirect[0].id
  ip_address            = google_compute_global_address.edge[0].id
}

# ── TLS + HTTPS proxy + global IP ────────────────────────────────────────────

resource "google_compute_global_address" "edge" {
  count = local.edge_enabled ? 1 : 0

  project      = var.gcp_project_id
  name         = "${local.name_prefix}-edge-ip"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
}

resource "google_compute_managed_ssl_certificate" "edge" {
  count = local.edge_use_managed_cert ? 1 : 0

  project = var.gcp_project_id
  name    = "${local.name_prefix}-edge-cert"

  managed {
    domains = [var.edge_domain]
  }
}

resource "google_compute_target_https_proxy" "edge" {
  count = local.edge_enabled ? 1 : 0

  project          = var.gcp_project_id
  name             = "${local.name_prefix}-https-proxy"
  url_map          = google_compute_url_map.edge[0].id
  ssl_certificates = local.edge_ssl_certificates
}

resource "google_compute_global_forwarding_rule" "edge_https" {
  count = local.edge_enabled ? 1 : 0

  project               = var.gcp_project_id
  name                  = "${local.name_prefix}-fwd-https"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.edge[0].id
  ip_address            = google_compute_global_address.edge[0].id
}
