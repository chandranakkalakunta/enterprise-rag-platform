# Runbook: GitHub Actions + Workload Identity Federation (Phase 1.2)

**Goal:** Deploy from GitHub Actions **without JSON service account keys**.  
**CI identity:** `sa-rag-ci@enterprise-rag-platform-502711.iam.gserviceaccount.com`  
**Repo allowed:** `chandranakkalakunta/enterprise-rag-platform` only  

## Prerequisites

- Phase 1.2 Terraform applied (WIF pool `rag-github-pool`, provider `github-oidc`)
- GitHub Actions permission: `id-token: write`

## Get provider + SA from Terraform outputs

```bash
cd terraform
terraform init -reconfigure -backend-config=environments/dev/backend.hcl
terraform output -raw github_actions_workload_identity_provider
terraform output -raw github_actions_service_account
```

Typical values (confirm with outputs — do not invent):

- **workload_identity_provider:**  
  `projects/642114828076/locations/global/workloadIdentityPools/rag-github-pool/providers/github-oidc`
- **service_account:**  
  `sa-rag-ci@enterprise-rag-platform-502711.iam.gserviceaccount.com`

## Minimal GitHub Actions example

```yaml
# .github/workflows/example-wif.yml
name: WIF smoke
on:
  workflow_dispatch:

permissions:
  contents: read
  id-token: write   # required for OIDC

jobs:
  gcp:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/642114828076/locations/global/workloadIdentityPools/rag-github-pool/providers/github-oidc
          service_account: sa-rag-ci@enterprise-rag-platform-502711.iam.gserviceaccount.com

      - name: Verify identity
        run: gcloud auth list
```

## Security rules

1. **Never** create or download SA JSON keys for `sa-rag-*`.
2. Do **not** broaden `attribute_condition` beyond this repository without an ADR.
3. Prefer branch/ref conditions later if deploy should be main-only.
4. Runtime SAs (`sa-rag-api`, `sa-rag-ingest`, `sa-rag-web`) are for Cloud Run only — not for GitHub.

## Verify (CLI)

```bash
gcloud iam service-accounts list --project=enterprise-rag-platform-502711

for sa in sa-rag-api sa-rag-ingest sa-rag-web sa-rag-ci; do
  gcloud iam service-accounts keys list \
    --iam-account=${sa}@enterprise-rag-platform-502711.iam.gserviceaccount.com \
    --format='table(name,keyType,validAfterTime)'
done
# Expect: only GOOGLE_SYSTEM_MANAGED keys if any listing shows system keys —
# never USER_MANAGED key files created by us.

gcloud iam workload-identity-pools list --location=global \
  --project=enterprise-rag-platform-502711

gcloud iam workload-identity-pools providers list \
  --workload-identity-pool=rag-github-pool \
  --location=global \
  --project=enterprise-rag-platform-502711
```

## Related

- ADR-0005 Security Posture  
- Terraform: `terraform/wif.tf`, `terraform/service_accounts.tf`, `terraform/iam.tf`
