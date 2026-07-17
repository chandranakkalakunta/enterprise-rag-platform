# Runbook: Cloud Run services (Phase 1.6 stubs)

**Project:** `enterprise-rag-platform-502711`  
**Region:** `asia-south1`  

## Services

| Service | Purpose | Runtime SA | Image (stub) |
|---------|---------|------------|--------------|
| `rag-api` | Query API (future FastAPI) | `sa-rag-api@…` | Cloud Run hello sample |
| `rag-ingest` | Ingest worker (future pipeline) | `sa-rag-ingest@…` | Cloud Run hello sample |
| `rag-web` | Web/PWA (future Next.js) | `sa-rag-web@…` | Cloud Run hello sample |

## Configuration (all three)

- Scale: **min instances = 0** (scale-to-zero)
- Resources: 1 CPU, 512Mi memory (stub)
- Env: `APP_VERSION=phase-1-6-stub`, `DEPLOYED_AT=2026-07-17T12:00:00Z`, `SERVICE_NAME`, `GCP_PROJECT_ID`
- Ingress: all traffic (tighten later with LB/Armor)
- Invoker: **not** public (`allUsers` not granted) — use `gcloud` auth or IAM for HTTP smoke

## List / describe

```bash
gcloud run services list --region=asia-south1 --project=enterprise-rag-platform-502711 \
  --format="table(metadata.name,status.url,status.conditions[0].status)"

gcloud run services describe rag-api --region=asia-south1 \
  --project=enterprise-rag-platform-502711 \
  --format="yaml(status.url,spec.template.spec.serviceAccountName)"
```

## Replace stub images (later)

Build and deploy real images via CI (WIF → `sa-rag-ci`) to Artifact Registry, then update Terraform `image` or deploy pipeline.

## Related

- Health contract on real API image: Phase 1.5  
- Binary Authorization: NFR-SEC-14 / BL-SEC-09 (future)  
