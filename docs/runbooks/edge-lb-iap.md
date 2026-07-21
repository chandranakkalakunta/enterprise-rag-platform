# Runbook: HTTPS LB + IAP edge (Phase 6.1 / ADR-0012)

**Status:** Terraform implemented behind `enable_edge`  
**Never:** grant `allUsers` or public `roles/run.invoker` on Cloud Run  

## What this deploys

| Piece | Resource |
|-------|----------|
| Global IP | `google_compute_global_address` |
| Serverless NEGs | `rag-web`, `rag-api` (region from `var.region`) |
| Backend services | IAP **enabled**; EXTERNAL_MANAGED |
| URL map | Default → web; `/api/*`, `/health`, `/ready`, OpenAPI paths → api |
| HTTPS | Managed cert when `edge_domain` set, or pre-created cert self_link |
| Cloud Run | `rag-web` / `rag-api` ingress = `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER` |
| IAM | IAP SA → `roles/run.invoker` on web+api; `iap_access_members` → `roles/iap.httpsResourceAccessor` |

### Path routing (full path preserved)

```text
https://<edge_domain>/              → rag-web
https://<edge_domain>/_next/...     → rag-web
https://<edge_domain>/api/v1/...    → rag-api   (path NOT stripped)
https://<edge_domain>/health        → rag-api
```

FastAPI continues to serve `/api/v1/...`. Do **not** strip the `/api` prefix in the URL map.

### Dual-host alternative

Not implemented in TF by default. Prefer single host. Dual-host would need two URL maps / host rules and CORS — see ADR-0012.

## Prerequisites

1. `compute.googleapis.com` and `iap.googleapis.com` enabled (default `required_apis`).  
2. Cloud Run services `rag-web` and `rag-api` already exist (this config updates ingress when edge is on).  
3. **IAP OAuth brand** (often Console one-time):  
   - APIs & Services → OAuth consent screen / IAP brand, **or**  
   - `create_iap_brand=true` with `iap_support_email` (org may block).  
4. IAP OAuth **client**:  
   - `create_iap_client=true` + `iap_brand_name`, **or**  
   - `iap_oauth_client_id` + `iap_oauth_client_secret` (use `TF_VAR_iap_oauth_client_secret`).  
5. Domain (recommended): DNS control for A record → LB IP.

## Apply order (Coordinator)

```bash
cd terraform
terraform init -reconfigure -backend-config=environments/dev/backend.hcl

# Review plan with edge OFF first (default)
terraform plan -var-file=environments/dev/terraform.tfvars

# Enable edge in tfvars (example):
# enable_edge          = true
# edge_domain          = "rag-dev.YOUR_DOMAIN"
# iap_access_members   = ["user:you@chandraailabs.com", "user:you@gmail.com"]
# create_iap_client    = true
# iap_brand_name       = "projects/PROJECT_NUMBER/brands/...."
# iap_support_email    = "you@chandraailabs.com"   # if creating brand

export TF_VAR_iap_oauth_client_secret='...'   # if using existing client

terraform plan -var-file=environments/dev/terraform.tfvars
# Confirm: NO allUsers, ingress change on rag-web/rag-api, IAP backends

terraform apply -var-file=environments/dev/terraform.tfvars
```

### DNS

```text
A  rag-dev.YOUR_DOMAIN  →  <terraform output -raw edge_ip>
```

Wait for Google-managed cert to become ACTIVE (can take 15–60+ minutes after DNS propagates).

### Outputs

```bash
terraform output edge_ip
terraform output edge_url
terraform output edge_iap_service_account
terraform output edge_coordinator_notes
```

## Smoke test

1. Open `https://<edge_domain>/` (or temporary host / cert as configured).  
2. Complete **IAP** Google sign-in as a principal in `iap_access_members`.  
3. Confirm UI loads from `rag-web` (not a direct `run.app` URL).  
4. Hit `https://<edge_domain>/health` → JSON from `rag-api`.  
5. Confirm direct `https://rag-api-....run.app/health` is **not** publicly invokable without identity (ingress LB-only).  
6. **Phase 6.2** will align app AuthN with IAP JWT and same-origin `NEXT_PUBLIC_API_BASE_URL` (empty or same host). Until then, API browser calls may still need transitional GIS Bearer if testing beyond health.

### Temporary dual testing (pre–6.2)

| Goal | Approach |
|------|----------|
| Edge smoke | LB + IAP only for UI shell + `/health` |
| Full chat with GIS | May still need app OAuth client origins updated; full same-origin + IAP JWT is **6.2** |

## Rollback

```hcl
enable_edge = false
```

Re-apply to restore Cloud Run ingress to `INGRESS_TRAFFIC_ALL` for web/api (still without public invoker). Destroy edge resources as planned by Terraform. Do **not** add `allUsers` invoker as a “fix”.

## Residual risks

- Managed cert stuck PROVISIONING → DNS / CAA issues  
- IAP brand/client org policy blocks TF create → Console  
- Path collisions if Next.js later adds `/api/*` routes (reserve backend API under `/api/v1`)  
- Multi-minute LB provisioning  

## Related

- [ADR-0012](../adr/0012-production-edge-lb-iap.md)  
- [cloud-run-services.md](./cloud-run-services.md)  
- [oauth-and-frontend-auth.md](./oauth-and-frontend-auth.md) (app auth; 6.2 IAP JWT)  
