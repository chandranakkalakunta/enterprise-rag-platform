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


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
