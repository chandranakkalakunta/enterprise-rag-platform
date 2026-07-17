# Runbook: Firestore metadata database (Phase 2.2)

**Project:** `enterprise-rag-platform-502711`  
**ADR:** [ADR-0006](../adr/0006-metadata-store-firestore.md)

## Database

| Property | Value |
|----------|--------|
| Name | `(default)` |
| Type | `FIRESTORE_NATIVE` |
| Location | `asia-south1` |
| Delete protection | Enabled |
| App Engine integration | Disabled |

Terraform resource: `google_firestore_database.metadata` in `terraform/firestore.tf`.

## IAM (least privilege)

| Principal | Role | Purpose |
|-----------|------|---------|
| `sa-rag-api@…` | `roles/datastore.user` | Document/version R/W on upload path |
| `sa-rag-ingest@…` | `roles/datastore.user` | Future worker updates |

`sa-rag-web` has **no** Firestore data role.

## Data model (MVP)

```text
documents/{document_id}
documents/{document_id}/versions/{version_id}
```

Version status machine (partial): `processing` → `ready` | `failed` (publish/retire later).

## Verify

```bash
export PROJECT=enterprise-rag-platform-502711

gcloud services list --enabled --project="$PROJECT" \
  --filter="config.name:firestore.googleapis.com" \
  --format="value(config.name)"

gcloud firestore databases describe \
  --database='(default)' \
  --project="$PROJECT" \
  --format="yaml(name,type,locationId)"

gcloud projects get-iam-policy "$PROJECT" \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/datastore.user" \
  --format="table(bindings.role,bindings.members)"
```

## Apply notes

```bash
cd terraform
terraform init -reconfigure -backend-config=environments/dev/backend.hcl
# Prefer targeted apply if Cloud Run images are managed by CI (avoids stub image rollback):
terraform apply -var-file=environments/dev/terraform.tfvars \
  -target='google_project_service.required["firestore.googleapis.com"]' \
  -target='google_firestore_database.metadata' \
  -target='google_project_iam_member.firestore_data["api"]' \
  -target='google_project_iam_member.firestore_data["ingest"]'
```
