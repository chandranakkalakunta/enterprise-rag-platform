# Vertex AI Vector Search (Matching Engine) — Phase 3.2 / ADR-0007
#
# STREAM_UPDATE index so runtime upserts do not require batch rebuilds.
# Dev-sized: SHARD_SIZE_SMALL, min_replica_count=1.
#
# Region: prefer var.vector_search_region (default asia-south1). If the region
# does not support Vector Search indexes, set vector_search_region to a
# supported region (e.g. us-central1) without changing var.region for the rest
# of the stack.
#
# text-embedding-005 default output dimensionality = 768
# (https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings)

# contents_delta_uri bootstrap for index create.
# NEVER use .keep / extensionless placeholders — Vertex rejects unknown formats
# (FAILED_PRECONDITION). Only supported embedding file types under the prefix
# (e.g. .json / .csv / .avro). See docs/runbooks/vector-search.md.
#
# STREAM_UPDATE indexes still need a bootstrap URI at create; runtime datapoints
# arrive via IndexService.UpsertDatapoints (not this object).
resource "google_storage_bucket_object" "vector_search_bootstrap" {
  count = var.enable_vector_search ? 1 : 0

  name         = "vector-search/index-bootstrap-${var.environment}/datapoint.json"
  bucket       = google_storage_bucket.docs[var.environment].name
  content_type = "application/json"
  content = jsonencode({
    id = "bootstrap-0"
    embedding = concat(
      [1.0],
      [for _ in range(var.vector_search_dimensions - 1) : 0.0]
    )
  })
}

resource "google_vertex_ai_index" "rag_docs" {
  count = var.enable_vector_search ? 1 : 0

  project      = var.gcp_project_id
  region       = var.vector_search_region
  display_name = "rag-docs-${var.environment}"
  description  = "Enterprise RAG dense index (STREAM_UPDATE, dev-sized). Embeddings: text-embedding-005 dim=${var.vector_search_dimensions}."

  labels = local.common_labels

  metadata {
    contents_delta_uri = "gs://${google_storage_bucket.docs[var.environment].name}/vector-search/index-bootstrap-${var.environment}/"
    config {
      dimensions                  = var.vector_search_dimensions
      approximate_neighbors_count = var.vector_search_approximate_neighbors_count
      shard_size                  = "SHARD_SIZE_SMALL"
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"

      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 500
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }

  index_update_method = "STREAM_UPDATE"

  depends_on = [
    google_project_service.required,
    google_storage_bucket_object.vector_search_bootstrap,
  ]
}

resource "google_vertex_ai_index_endpoint" "rag_docs" {
  count = var.enable_vector_search ? 1 : 0

  project                 = var.gcp_project_id
  region                  = var.vector_search_region
  display_name            = "rag-docs-endpoint-${var.environment}"
  description             = "Public endpoint for rag-docs Vector Search (dev)"
  public_endpoint_enabled = true

  labels = local.common_labels

  depends_on = [google_project_service.required]
}

# Deployed index id must match [a-z]([a-z0-9_]{0,61}[a-z0-9])?
resource "google_vertex_ai_index_endpoint_deployed_index" "rag_docs" {
  count = var.enable_vector_search ? 1 : 0

  index_endpoint    = google_vertex_ai_index_endpoint.rag_docs[0].id
  index             = google_vertex_ai_index.rag_docs[0].id
  deployed_index_id = "rag_docs_${var.environment}"
  display_name      = "rag-docs-${var.environment}"

  # Cost-aware: single small replica band (automatic resources)
  automatic_resources {
    min_replica_count = 1
    max_replica_count = 1
  }

  depends_on = [
    google_vertex_ai_index.rag_docs,
    google_vertex_ai_index_endpoint.rag_docs,
  ]
}

# Data-plane access for runtime SAs (upsert + query)
resource "google_project_iam_member" "vertex_ai_user_runtime" {
  for_each = var.enable_vector_search ? toset(["api", "ingest"]) : toset([])

  project = var.gcp_project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.rag[each.key].email}"
}
