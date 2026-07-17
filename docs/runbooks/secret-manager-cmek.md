# Runbook: Secret Manager + CMEK (Phase 1.3)

**Project:** `enterprise-rag-platform-502711`  
**Key ring:** `rag-keyring` (`asia-south1`)  
**Secrets CMEK:** `rag-secrets-key`  
**GCS CMEK (future buckets):** `rag-gcs-key`  

## What Terraform manages

| Resource | Name | Notes |
|----------|------|--------|
| Key ring | `rag-keyring` | asia-south1 |
| Crypto key | `rag-gcs-key` | ENCRYPT_DECRYPT, 90-day rotation |
| Crypto key | `rag-secrets-key` | ENCRYPT_DECRYPT, 90-day rotation |
| Secret shell | `rag-oauth-client-id` | CMEK; **no version** until Coordinator adds value |
| Secret shell | `rag-oauth-client-secret` | CMEK; **no version** until Coordinator adds value |

Terraform **never** stores OAuth values. Real values are added only via CLI/console by humans with access.

## Principals with `roles/cloudkms.cryptoKeyEncrypterDecrypter`

On **both** keys (`rag-gcs-key`, `rag-secrets-key`):

- `sa-rag-api@…`
- `sa-rag-ingest@…`
- `sa-rag-web@…`
- `sa-rag-ci@…`

On **rag-secrets-key only** (required for SM CMEK):

- `service-PROJECT_NUMBER@gcp-sa-secretmanager.iam.gserviceaccount.com`

## Coordinator: add secret values (after OAuth client exists)

```bash
export PROJECT=enterprise-rag-platform-502711
gcloud config set project "$PROJECT"

# Client ID (plain string)
printf '%s' 'YOUR_OAUTH_CLIENT_ID' | \
  gcloud secrets versions add rag-oauth-client-id --data-file=-

# Client secret (never commit; never put in Terraform)
printf '%s' 'YOUR_OAUTH_CLIENT_SECRET' | \
  gcloud secrets versions add rag-oauth-client-secret --data-file=-

# Verify version exists (does not print secret payload)
gcloud secrets versions list rag-oauth-client-id
gcloud secrets versions list rag-oauth-client-secret
```

## Verify CMEK attachment

```bash
gcloud kms keyrings list --location=asia-south1 --project=enterprise-rag-platform-502711
gcloud kms keys list --keyring=rag-keyring --location=asia-south1 \
  --project=enterprise-rag-platform-502711

gcloud secrets describe rag-oauth-client-id --project=enterprise-rag-platform-502711
gcloud secrets describe rag-oauth-client-secret --project=enterprise-rag-platform-502711
# Expect replication.userManaged.replicas[].customerManagedEncryption.kmsKeyName
# containing rag-secrets-key
```

## Future

- **Binary Authorization** — backlog (image attestation for Cloud Run); not Phase 1.3.
- GCS data buckets with `rag-gcs-key` + Storage service agent KMS grant.
- Per-secret IAM (narrow `secretAccessor` to individual secrets) when apps go live.

## Related

- ADR-0005 Security Posture  
- Terraform: `terraform/kms.tf`, `terraform/secrets.tf`
