"""Application settings — env-driven, no hard-coded project secrets."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for rag-api (Phase 2.1 upload path)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GCP
    gcp_project_id: str = Field(
        default="enterprise-rag-platform-502711",
        description="GCP project ID (override via GCP_PROJECT_ID)",
    )
    gcp_region: str = Field(default="asia-south1", description="Primary region")

    # Document storage
    gcs_docs_bucket: str = Field(
        default="rag-docs-dev",
        description="Document bucket (rag-docs-{env}); override via GCS_DOCS_BUCKET",
    )
    max_upload_bytes: int = Field(
        default=50 * 1024 * 1024,
        description="Max upload size in bytes (default 50 MiB)",
    )

    # Temporary auth (full OAuth + content_admin in later phase)
    auth_dev_bypass: bool = Field(
        default=True,
        description=(
            "If true, upload endpoints skip Bearer checks (local/dev only). "
            "Set AUTH_DEV_BYPASS=false in shared environments."
        ),
    )
    upload_bearer_token: str = Field(
        default="",
        description=(
            "When AUTH_DEV_BYPASS=false, require Authorization: Bearer <this value>. "
            "Empty token with bypass=false rejects all requests."
        ),
    )

    environment: str = Field(default="local", description="local | dev | test | prod")
    log_level: str = Field(default="INFO")

    # Vertex embeddings (Phase 3.1 / ADR-0007)
    embedding_model_id: str = Field(
        default="text-embedding-005",
        description="Vertex text embedding model id (EMBEDDING_MODEL_ID)",
    )
    embedding_batch_size: int = Field(
        default=32,
        description="Max texts per Vertex embedding API call",
    )
    vertex_location: str = Field(
        default="asia-south1",
        description="Vertex AI location (VERTEX_LOCATION)",
    )

    # Vector Search (Phase 3.2 / ADR-0007) — leave empty to skip upsert locally
    vector_search_enabled: bool = Field(
        default=False,
        description="When true, upsert/activate vectors (VECTOR_SEARCH_ENABLED)",
    )
    vector_search_index_id: str = Field(
        default="",
        description="Index id or full resource name (VECTOR_SEARCH_INDEX_ID)",
    )
    vector_search_endpoint_id: str = Field(
        default="",
        description="Endpoint id for queries (VECTOR_SEARCH_ENDPOINT_ID)",
    )
    vector_search_deployed_index_id: str = Field(
        default="",
        description="Deployed index id for FindNeighbors (VECTOR_SEARCH_DEPLOYED_INDEX_ID)",
    )
    vector_search_region: str = Field(
        default="asia-south1",
        description="Vector Search region (VECTOR_SEARCH_REGION)",
    )
    vector_search_dimensions: int = Field(
        default=768,
        description="Expected embedding dimensions (text-embedding-005 default)",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
