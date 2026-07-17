# Runbook: Cloud Run services (Phase 1.6 + 2.3 lifecycle)

**Project:** `enterprise-rag-platform-502711`  
**Region:** `asia-south1`  

## Services

| Service | Purpose | Runtime SA | Image ownership |
|---------|---------|------------|-----------------|
| `rag-api` | Query / upload API | `sa-rag-api@…` | **CI** (Artifact Registry) after first deploy |
| `rag-ingest` | Ingest worker | `sa-rag-ingest@…` | CI when worker image lands |
| `rag-web` | Web/PWA | `sa-rag-web@…` | CI when web image lands |

Bootstrap image in Terraform: Cloud Run hello sample (create-only baseline).

## Configuration (all three)

- Scale: **min instances = 0** (scale-to-zero)
- Resources: 1 CPU, 512Mi memory (baseline)
- Env (bootstrap): `APP_VERSION`, `DEPLOYED_AT`, `SERVICE_NAME`, `GCP_PROJECT_ID` — CI overwrites version timestamps on deploy
- Ingress: all traffic (tighten later with LB/Armor)
- Invoker: **not** public (`allUsers` not granted)

## Terraform lifecycle (Phase 2.3)

`google_cloud_run_v2_service.rag` uses:

```hcl
lifecycle {
  ignore_changes = [
    client,
    client_version,
    template[0].containers,  # image + env managed by CI
    labels["purpose"],
  ]
}
```

**Why:** Without ignore, full `terraform apply` rolls CI-deployed Artifact Registry tags back to the hello stub (Phase 2.2 issue log).

- Terraform still owns: service account, scaling limits, ingress, project/region, SA wiring.
- CI (WIF → `sa-rag-ci`) owns: container image and deploy-time env (`APP_VERSION` / `DEPLOYED_AT`).

## List / describe

```bash
gcloud run services list --region=asia-south1 --project=enterprise-rag-platform-502711 \
  --format="table(metadata.name,status.url,status.conditions[0].status)"

gcloud run services describe rag-api --region=asia-south1 \
  --project=enterprise-rag-platform-502711 \
  --format="yaml(status.url,spec.template.spec.serviceAccountName,spec.template.spec.containers[0].image)"
```

## Related

- CI deploy: [github-actions-ci.md](./github-actions-ci.md)  
- Binary Authorization: NFR-SEC-14 / BL-SEC-09 (future)  

