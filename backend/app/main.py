"""Enterprise RAG Platform — FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format='{"severity":"%(levelname)s","message":"%(message)s","logger":"%(name)s"}',
)
logger = logging.getLogger("erp.api")

SERVICE_NAME = "rag-api"


def _app_version() -> str:
    """Build/deploy version from env (git SHA or semver); local default 'dev'."""
    return os.getenv("APP_VERSION", "dev")


def _deployed_at() -> str:
    """ISO-8601 deploy timestamp from env; empty string for local if unset."""
    return os.getenv("DEPLOYED_AT", "")


def _health_payload(status: str) -> dict[str, Any]:
    """Shared fields for /health and /ready (NFR-REL-03a)."""
    return {
        "status": status,
        "service": SERVICE_NAME,
        "version": _app_version(),
        "deployed_at": _deployed_at(),
    }


def _bm25_warm_start_background() -> None:
    """Rebuild in-process BM25 from published corpus (never crashes the process)."""
    try:
        from app.core.config import get_settings
        from app.services.bm25_ops import rebuild_bm25_from_published

        settings = get_settings()
        if not settings.bm25_warm_start:
            logger.info("bm25_warm_start_disabled")
            return
        if not settings.hybrid_retrieval_enabled and not settings.bm25_always_index:
            logger.info("bm25_warm_start_skipped hybrid_off")
            return
        result = rebuild_bm25_from_published(settings=settings)
        logger.info("bm25_warm_start_result %s", result)
    except Exception:  # noqa: BLE001
        logger.exception("bm25_warm_start_thread_failed")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "API starting service=%s version=%s",
        SERVICE_NAME,
        _app_version(),
    )
    # Phase 4.3: warm BM25 without blocking readiness
    warm = threading.Thread(
        target=_bm25_warm_start_background,
        name="bm25-warm-start",
        daemon=True,
    )
    warm.start()
    yield


app = FastAPI(
    title="Enterprise RAG Platform API",
    description=(
        "Production-grade Enterprise RAG API. "
        "Upload/lifecycle, embeddings, Vector Search; "
        "POST /api/v1/query/search (dense retrieval, published-only)."
    ),
    version=_app_version(),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Frontend origins (local Next.js; extend via env later for Cloud Run web URL)
_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness probe — no external dependency checks (Cloud Run / k8s)."""
    return _health_payload("ok")


@app.get("/ready")
async def ready() -> dict[str, Any]:
    """Readiness probe — expand checks in later phases (DB, Vector Search, etc.)."""
    payload = _health_payload("ready")
    # Placeholder for future dependency probes; keep lightweight for now
    payload["checks"] = {}
    return payload


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Enterprise RAG Platform API",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "me": "/api/v1/me",
        "upload": "/api/v1/documents/upload",
        "search": "/api/v1/query/search",
        "answer": "/api/v1/query/answer",
    }
