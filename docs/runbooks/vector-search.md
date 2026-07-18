# Runbook: Vertex AI Vector Search (Phase 3.2)

**ADR:** [ADR-0007](../adr/0007-embedding-and-vector-search.md)  
**Embedding model:** `text-embedding-005` → **768** dimensions (default output)  
**Index mode:** `STREAM_UPDATE` (runtime upserts)

## Resources (Terraform)

| Resource | Purpose |
|----------|---------|
| `google_vertex_ai_index.rag_docs` | STREAM_UPDATE index, `SHARD_SIZE_SMALL` |
| `google_vertex_ai_index_endpoint.rag_docs` | Public endpoint (`public_endpoint_enabled`) |
| `google_vertex_ai_index_endpoint_deployed_index.rag_docs` | `automatic_resources` min/max = 1 |

**Region:** `var.vector_search_region` (default **`asia-south1`**). If the API rejects the region, set:

```hcl
vector_search_region = "us-central1"
```

**Toggle:** `enable_vector_search = false` skips provisioning (local/dev workspaces without cost).

### Bootstrap object (index create)

`contents_delta_uri` must contain a **valid embedding file** with a supported extension:

| Allowed | Not allowed |
|---------|-------------|
| `.json`, `.csv`, `.avro` embedding dumps | **`.keep`**, empty markers, unknown extensions |

**Lesson (Phase 3.2 hotfix):** bootstrap with `.keep` caused index create `FAILED_PRECONDITION` / unknown format. Terraform now writes env-aware:

```text
gs://rag-docs-{env}/vector-search/index-bootstrap-{env}/datapoint.json
```

with a single JSON datapoint whose `embedding` length = `var.vector_search_dimensions` (default 768). Runtime still uses **STREAM_UPDATE** upserts; the bootstrap file is only for create-time metadata.

Also include bootstrap in targeted applies:

```bash
-target=google_storage_bucket_object.vector_search_bootstrap
```

### Cost notes (dev)

- Smallest practical: `SHARD_SIZE_SMALL`, 1 automatic replica  
- STREAM_UPDATE indexes + deployed endpoints incur **ongoing** cost — disable when unused  
- Index create/deploy can take **tens of minutes**

### Apply (dev)

```bash
cd terraform
terraform init -reconfigure -backend-config=environments/dev/backend.hcl
terraform plan -var-file=environments/dev/terraform.tfvars \
  -target=google_storage_bucket_object.vector_search_bootstrap \
  -target=google_vertex_ai_index.rag_docs \
  -target=google_vertex_ai_index_endpoint.rag_docs \
  -target=google_vertex_ai_index_endpoint_deployed_index.rag_docs \
  -target=google_project_iam_member.vertex_ai_user_runtime
# Review cost → apply
```

Copy outputs into API env / Cloud Run:

| Env var | Terraform output |
|---------|------------------|
| `VECTOR_SEARCH_ENABLED` | `true` |
| `VECTOR_SEARCH_REGION` | `vector_search_region` |
| `VECTOR_SEARCH_INDEX_ID` | `vector_search_index_id` (or full resource name) |
| `VECTOR_SEARCH_ENDPOINT_ID` | `vector_search_endpoint_id` |
| `VECTOR_SEARCH_DEPLOYED_INDEX_ID` | `vector_search_deployed_index_id` |

## Datapoint schema

**ID:** `{document_id}:{version_id}:{chunk_index}`

### Restrict namespaces (filters + lightweight payload)

| Namespace | Values | Role |
|-----------|--------|------|
| `active` | `true` / `false` | Query only published active set |
| `collection` | collection label or `_none` | Filter |
| `document_id` | uuid | Filter |
| `version_id` | uuid | Filter |
| `chunk_index` | string int | Identity |
| `payload_text` | chunk text (≤1000 chars) | Grounding when `return_full_datapoint` |
| `char_count` | string int | Metadata |
| `title` / `filename` | optional | Display |

Hard-delete of inactive datapoints is **not** done here — see backlog **BL-RAG-16**.

## Lifecycle

```text
embeddings_status=ready
  → Upsert datapoints with active=false   (vector_status=upserted|skipped|failed)

POST .../publish
  → Firestore published + active_version_id
  → Re-upsert this version active=true    (vector_status=activated)
  → Re-upsert previous published active=false  (vector_status=deactivated)

POST .../retire
  → Firestore retired
  → Re-upsert active=false                (vector_status=deactivated)
```

No re-embed on publish/retire: vectors reloaded from `embeddings.jsonl` + text from `chunks.jsonl`.

When `VECTOR_SEARCH_ENABLED=false` or index id empty → `vector_status=skipped` (local tests).

## IAM

| SA | Role |
|----|------|
| `sa-rag-api` | `roles/aiplatform.user` |
| `sa-rag-ingest` | `roles/aiplatform.user` |

## Related

- [document-upload-api.md](./document-upload-api.md) — embeddings.jsonl  
- [version-lifecycle.md](./version-lifecycle.md) — publish/retire  
