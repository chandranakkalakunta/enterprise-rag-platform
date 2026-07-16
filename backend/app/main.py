"""Enterprise RAG Platform — FastAPI application entrypoint (Phase 0 placeholder)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='{"severity":"%(levelname)s","message":"%(message)s","logger":"%(name)s"}',
)
logger = logging.getLogger("erp.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("API starting (phase=0 skeleton)")
    yield


app = FastAPI(
    title="Enterprise RAG Platform API",
    description="Production-grade Enterprise RAG (Phase 0 skeleton)",
    version="0.1.0",
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
async def health() -> dict[str, str]:
    """Liveness probe for local and Cloud Run smoke tests."""
    return {
        "status": "ok",
        "service": "enterprise-rag-platform-api",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness probe — expand with dependency checks in later phases."""
    return {"status": "ready"}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Enterprise RAG Platform API",
        "docs": "/docs",
        "health": "/health",
    }
