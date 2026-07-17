"""Enterprise RAG Platform — FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "API starting service=%s version=%s",
        SERVICE_NAME,
        _app_version(),
    )
    yield


app = FastAPI(
    title="Enterprise RAG Platform API",
    description="Production-grade Enterprise RAG API",
    version=_app_version(),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    }
