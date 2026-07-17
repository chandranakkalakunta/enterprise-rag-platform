# Runbook: Terraform multi-env bootstrap (Phase 1.1)

**Project:** `var.gcp_project_id` (locked: `enterprise-rag-platform-502711`)  
**Region:** `asia-south1`  
**State buckets:** `enterprise-rag-tfstate-{dev,test,prod}`

## Prerequisites

1. `gcloud` authenticated; ADC for Terraform (`gcloud auth application-default login`)
2. Active account can enable APIs and create GCS buckets
3. **Billing enabled** on the project (required for many APIs)
4. `terraform` >= 1.5
5. **Zero JSON SA keys** — user ADC or WIF only

```bash
gcloud config set project enterprise-rag-platform-502711
gcloud billing projects describe enterprise-rag-platform-502711 --format='value(billingEnabled)'
# must be True
```

## Bootstrap sequence (done once)

Remote backend needs the state bucket first → **local state**, then migrate.

```bash
cd terraform

# 1) Init with local state (backend "gcs" {} commented out in versions.tf during first bootstrap)
terraform init -input=false

# 2) Apply foundation: required APIs + all three state buckets
terraform plan  -var-file=environments/dev/terraform.tfvars -out=tfplan-dev
terraform apply -input=false tfplan-dev

# 3) Enable backend "gcs" {} in versions.tf, then migrate
terraform init -migrate-state -force-copy -input=false \
  -backend-config=environments/dev/backend.hcl
```

Foundation state for Phase 1.1 lives in **`gs://enterprise-rag-tfstate-dev`** (prefix `terraform/state`).  
All three state buckets are created in that foundation apply so test/prod backends are ready.

## Day-2: select environment

```bash
cd terraform

# Dev (foundation backend)
terraform init -reconfigure -backend-config=environments/dev/backend.hcl
terraform plan  -var-file=environments/dev/terraform.tfvars
terraform apply -var-file=environments/dev/terraform.tfvars

# Test / prod — same foundation resources; only outputs/labels differ today.
# When env-specific resources land, use matching backend + tfvars:
terraform init -reconfigure -backend-config=environments/test/backend.hcl
terraform plan  -var-file=environments/test/terraform.tfvars

terraform init -reconfigure -backend-config=environments/prod/backend.hcl
terraform plan  -var-file=environments/prod/terraform.tfvars
```

## Verify

```bash
gcloud services list --enabled --project=enterprise-rag-platform-502711 \
  --format="value(config.name)" | sort

gcloud storage buckets list --project=enterprise-rag-platform-502711 \
  --filter="name:enterprise-rag-tfstate-" \
  --format="table(name,location,versioning_enabled)"
```

## Notes

- Application code must **never** hard-code project IDs.
- Do not commit `*.tfstate` or `.terraform/`.
- Commit `terraform/.terraform.lock.hcl`.
- `force_destroy = false` on state buckets.
