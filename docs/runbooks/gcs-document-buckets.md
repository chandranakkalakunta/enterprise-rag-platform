# Runbook: Application document GCS buckets (Phase 1.4)

**Project:** `enterprise-rag-platform-502711`  
**CMEK:** `rag-gcs-key` on key ring `rag-keyring` (`asia-south1`)  

## Buckets

| Environment | Bucket name | URL |
|-------------|-------------|-----|
| dev | `rag-docs-dev` | `gs://rag-docs-dev` |
| test | `rag-docs-test` | `gs://rag-docs-test` |
| prod | `rag-docs-prod` | `gs://rag-docs-prod` |

### Settings (all three)

- Location: `asia-south1`
- Storage class: STANDARD
- Uniform bucket-level access: **true**
- Public access prevention: **enforced**
- Versioning: **enabled**
- Soft delete: **7 days**
- Default encryption: **CMEK** `rag-gcs-key`
- Lifecycle: delete **non-current** versions after **90 days** (when a newer version exists)

## Prefix convention (logical folders)

Paths are prefixes inside each bucket (not separate buckets):

| Prefix | Purpose |
|--------|---------|
| `raw/` | Original uploads as received from content admins |
| `versions/` | Immutable published document version binaries |
| `assets/` | Multimodal assets (images, table extracts, captions) |
| `processed/` | Pipeline intermediates (chunks metadata dumps, job artifacts) |

Example object keys:

```text
gs://rag-docs-dev/raw/{document_id}/{upload_id}/source.pdf
gs://rag-docs-dev/versions/{document_id}/{version_id}/content.pdf
gs://rag-docs-dev/assets/{document_id}/{version_id}/figures/fig-001.png
gs://rag-docs-dev/processed/{document_id}/{version_id}/chunks.jsonl
```

## Bucket IAM (least privilege)

| Principal | Role on each `rag-docs-*` |
|-----------|---------------------------|
| `sa-rag-ingest` | `roles/storage.objectAdmin` |
| `sa-rag-api` | `roles/storage.objectViewer` + `roles/storage.objectCreator` |
| `sa-rag-ci` | `roles/storage.objectAdmin` (bucket-scoped) |
| `sa-rag-web` | **none** (web should not touch GCS data plane) |

**Note (Phase 1.5):** Project-level `roles/storage.admin` on `sa-rag-ci` has been **removed**.  
CI storage access is **bucket-scoped** `objectAdmin` on `rag-docs-*` only.

## KMS

- Storage service agent has `roles/cloudkms.cryptoKeyEncrypterDecrypter` on `rag-gcs-key` (required for default CMEK).
- Custom SAs also have encrypter/decrypter on `rag-gcs-key` (Phase 1.3).

## Verify

```bash
export PROJECT=enterprise-rag-platform-502711

gcloud storage buckets list --project="$PROJECT" \
  --filter="name:rag-docs-" \
  --format="table(name,location,versioning_enabled)"

gcloud storage buckets describe gs://rag-docs-dev \
  --format="yaml(encryption,iamConfiguration,lifecycle,versioning,softDeletePolicy)"

gcloud storage buckets describe gs://rag-docs-dev \
  --format="value(encryption.defaultKmsKeyName)"
# Expect: .../cryptoKeys/rag-gcs-key
```

## Related

- Terraform: `terraform/gcs.tf`, `terraform/kms.tf`  
- ADR-0003 document versioning · ADR-0005 security  
