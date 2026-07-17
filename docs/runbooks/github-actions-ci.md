# Runbook: GitHub Actions CI (Phase 1.7)

**Keyless pipeline only** — Workload Identity Federation. **No JSON service-account keys.**

## Constants (locked)

| Item | Value |
|------|--------|
| GCP project | `enterprise-rag-platform-502711` |
| Project number | `642114828076` |
| Region | `asia-south1` |
| CI service account | `sa-rag-ci@enterprise-rag-platform-502711.iam.gserviceaccount.com` |
| **WIF provider** | `projects/642114828076/locations/global/workloadIdentityPools/rag-github-pool/providers/github-oidc` |
| Artifact Registry | `rag-containers` |
| Image path | `asia-south1-docker.pkg.dev/enterprise-rag-platform-502711/rag-containers/rag-api` |
| Cloud Run service | `rag-api` |
| Allowed GitHub repo | `chandranakkalakunta/enterprise-rag-platform` |

## Workflow file

`.github/workflows/ci.yml`

### Jobs

1. **test** (every PR + push)  
   - Python 3.12  
   - `pip install -r backend/requirements.txt` + `pip check`  
   - `pytest -q`

2. **build-and-deploy** (only `push` to `main`, after test)  
   - `permissions.id-token: write` (OIDC)  
   - `google-github-actions/auth@v2` with WIF provider + `sa-rag-ci`  
   - Docker build/push to Artifact Registry  
   - `gcloud run services update rag-api` with new image + `APP_VERSION` / `DEPLOYED_AT`  
   - Runtime identity remains `sa-rag-api@…`

## Flow diagram

```text
PR / push
   │
   ▼
[test] pytest ──fail──▶ stop
   │ pass
   │
   │  (main push only)
   ▼
[build-and-deploy]
   WIF OIDC ──▶ sa-rag-ci (short-lived token)
   docker build/push ──▶ Artifact Registry rag-containers
   gcloud run update ──▶ rag-api (status.url)
```

## Coordinator: first real CI run after merge

1. Merge this PR to `main`.  
2. Ensure GitHub Actions is enabled for the repository.  
3. No GCP keys to configure in GitHub secrets (WIF only).  
4. Optional GitHub **Environment** protection for production later.  
5. Watch **Actions** tab: `test` then `build-and-deploy`.  
6. Verify:

```bash
gcloud run services describe rag-api --region=asia-south1 \
  --project=enterprise-rag-platform-502711 \
  --format='value(status.url,spec.template.spec.containers[0].image)'

# Smoke (requires invoker permission or temporary unauthenticated if enabled later)
curl -sS "$(gcloud run services describe rag-api --region=asia-south1 \
  --project=enterprise-rag-platform-502711 --format='value(status.url)')/health"
```

## IAM used by CI SA (existing)

- `roles/run.admin` — deploy Cloud Run  
- `roles/artifactregistry.writer` — push images  
- `roles/iam.serviceAccountUser` on `sa-rag-api` — set runtime SA  
- Bucket objectAdmin on `rag-docs-*` (not project storage.admin)

## Related

- WIF bootstrap: [github-actions-wif.md](./github-actions-wif.md)  
- Cloud Run services: [cloud-run-services.md](./cloud-run-services.md)  
