# Enterprise RAG API — production image for Cloud Run
# Python 3.12 · non-root uid 1001 · port 8080
# Build: docker build -t rag-api --build-arg APP_VERSION=... --build-arg DEPLOYED_AT=... .

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps only if needed later (e.g. libgomp); keep slim for stub API
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pinned deps from requirements.txt (CI non-negotiable source of truth)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip check

# Application code
COPY app/ ./app/

# Non-root runtime (uid/gid 1001) — production non-negotiable
RUN groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER 1001:1001

# Build-time metadata (overridden at deploy via Cloud Run env)
ARG APP_VERSION=dev
ARG DEPLOYED_AT=
ENV APP_VERSION=${APP_VERSION} \
    DEPLOYED_AT=${DEPLOYED_AT} \
    PORT=8080

EXPOSE 8080

# Cloud Run sets PORT; default 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
