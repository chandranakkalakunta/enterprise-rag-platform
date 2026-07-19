"""Application settings — env-driven, no hard-coded project secrets."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for rag-api (Phase 5.1 auth + prior features)."""

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

    # Auth (Phase 5.1 / ADR-0009)
    auth_dev_bypass: bool = Field(
        default=True,
        description=(
            "If true, skip Google token verification and inject a local admin "
            "context (automated tests / local only). "
            "Set AUTH_DEV_BYPASS=false in shared environments."
        ),
    )
    google_oauth_client_id: str = Field(
        default="",
        description=(
            "Google OAuth 2.0 Web client ID (audience for ID token verify). "
            "Env: GOOGLE_OAUTH_CLIENT_ID. Secret shell: rag-oauth-client-id."
        ),
    )
    admin_emails: str = Field(
        default="",
        description=(
            "Comma-separated emails elevated to role admin on login (ADMIN_EMAILS)"
        ),
    )
    content_admin_emails: str = Field(
        default="",
        description=(
            "Comma-separated emails elevated to content_admin if not admin "
            "(CONTENT_ADMIN_EMAILS)"
        ),
    )
    allowed_email_domains: str = Field(
        default="chandraailabs.com,gmail.com",
        description=(
            "Comma-separated allowed email domains (ALLOWED_EMAIL_DOMAINS). "
            "Default: chandraailabs.com,gmail.com"
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
    vector_search_public_endpoint_domain: str = Field(
        default="",
        description=(
            "Public endpoint domain for MatchService (VECTOR_SEARCH_PUBLIC_ENDPOINT_DOMAIN). "
            "When set, used as api_endpoint for FindNeighbors."
        ),
    )

    # Dense retrieval (Phase 3.3 / ADR-0008)
    retrieval_top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Default fused/final neighbor count (RETRIEVAL_TOP_K)",
    )

    # Hybrid retrieval (Phase 4.2 / ADR-0011)
    hybrid_retrieval_enabled: bool = Field(
        default=True,
        description=(
            "When true, fuse dense Vector Search + in-process BM25 via RRF "
            "(HYBRID_RETRIEVAL_ENABLED). False = dense-only."
        ),
    )
    retrieval_top_k_dense: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description=(
            "Per-channel dense top_k before RRF (RETRIEVAL_TOP_K_DENSE). "
            "None = use RETRIEVAL_TOP_K."
        ),
    )
    retrieval_top_k_bm25: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description=(
            "Per-channel BM25 top_k before RRF (RETRIEVAL_TOP_K_BM25). "
            "None = use RETRIEVAL_TOP_K."
        ),
    )
    rrf_k: int = Field(
        default=60,
        ge=1,
        le=200,
        description="RRF constant k (RRF_K); typical default 60",
    )
    bm25_always_index: bool = Field(
        default=False,
        description=(
            "If true, index BM25 on publish even when hybrid is off "
            "(BM25_ALWAYS_INDEX). Useful for warm standby."
        ),
    )
    bm25_warm_start: bool = Field(
        default=True,
        description=(
            "On API startup, rebuild BM25 from published versions "
            "(BM25_WARM_START). Failures are logged; API still starts."
        ),
    )
    bm25_warm_start_max_docs: int = Field(
        default=200,
        ge=1,
        le=5000,
        description="Max documents to scan on BM25 warm-start (BM25_WARM_START_MAX_DOCS)",
    )

    # Citations (Phase 4.3)
    citation_max_per_doc: int = Field(
        default=1,
        ge=1,
        le=10,
        description=(
            "Max citation cards per document_id in answer responses "
            "(CITATION_MAX_PER_DOC). Default 1 reduces SOURCES spam."
        ),
    )
    citation_merge_snippets: bool = Field(
        default=True,
        description=(
            "When CITATION_MAX_PER_DOC=1, merge one extra distinct snippet "
            "into the winning card (CITATION_MERGE_SNIPPETS)."
        ),
    )

    # Grounded generation (Phase 3.4 / ADR-0008)
    # Model runs in VERTEX_LOCATION (same region as embeddings unless overridden).
    generation_model_id: str = Field(
        default="gemini-2.5-flash",
        description="Vertex Gemini model id (GENERATION_MODEL_ID); default gemini-2.5-flash",
    )
    generation_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Generation temperature (GENERATION_TEMPERATURE)",
    )
    evidence_min_score: float | None = Field(
        default=None,
        description=(
            "Optional minimum neighbor score; if set and all hits are below, refuse. "
            "None = only refuse on zero usable hits (EVIDENCE_MIN_SCORE)."
        ),
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


def parse_csv_set(raw: str) -> set[str]:
    """Parse comma-separated config into a lowercased stripped set."""
    if not raw or not raw.strip():
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}
