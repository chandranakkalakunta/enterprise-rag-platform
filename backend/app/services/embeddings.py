"""Vertex AI text embeddings (Phase 3.1 / ADR-0007).

Isolated from FastAPI / Firestore. GCS write helpers live in gcs_storage.
Vertex client is injectable for unit tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

logger = logging.getLogger("erp.api.embeddings")

# Default GA-family pin (override via EMBEDDING_MODEL_ID)
DEFAULT_EMBEDDING_MODEL_ID = "text-embedding-005"
DEFAULT_EMBEDDING_BATCH_SIZE = 32


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class TextEmbedder(Protocol):
    """Minimal client protocol for tests."""

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass(frozen=True, slots=True)
class EmbeddingRecord:
    """One chunk embedding for embeddings.jsonl."""

    chunk_id: str
    index: int
    embedding: list[float]
    char_count: int
    document_id: str
    version_id: str

    def to_jsonl_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "index": self.index,
            "embedding": self.embedding,
            "char_count": self.char_count,
            "document_id": self.document_id,
            "version_id": self.version_id,
        }


def _batch(items: Sequence[str], size: int) -> list[list[str]]:
    if size < 1:
        raise EmbeddingError("batch_size must be >= 1")
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


def embed_texts(
    texts: Sequence[str],
    *,
    model_id: str,
    project_id: str,
    location: str,
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
    embedder: TextEmbedder | None = None,
) -> list[list[float]]:
    """
    Embed a list of texts with Vertex AI Text Embedding API.

    Args:
        texts: Non-empty strings to embed (order preserved).
        model_id: Vertex embedding model id (e.g. text-embedding-005).
        project_id: GCP project.
        location: Vertex location (e.g. asia-south1 or us-central1).
        batch_size: Max texts per API call.
        embedder: Optional injectable client (tests).

    Returns:
        List of embedding vectors aligned with ``texts``.
    """
    if not texts:
        return []
    for i, t in enumerate(texts):
        if t is None or not str(t).strip():
            raise EmbeddingError(f"Empty text at index {i}")

    if not (model_id or "").strip():
        raise EmbeddingError("model_id is required")

    client = embedder or VertexTextEmbedder(
        project_id=project_id,
        location=location,
        model_id=model_id.strip(),
    )

    try:
        vectors: list[list[float]] = []
        for part in _batch(list(texts), batch_size):
            vectors.extend(client.embed_texts(part))
    except EmbeddingError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise EmbeddingError(f"Vertex embedding failed: {exc}") from exc

    if len(vectors) != len(texts):
        raise EmbeddingError(
            f"Embedding count mismatch: got {len(vectors)}, expected {len(texts)}"
        )
    for i, vec in enumerate(vectors):
        if not vec:
            raise EmbeddingError(f"Empty embedding vector at index {i}")
    return vectors


class VertexTextEmbedder:
    """Vertex AI TextEmbeddingModel wrapper."""

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        model_id: str,
    ) -> None:
        self.project_id = project_id
        self.location = location
        self.model_id = model_id
        self._model = None

    def _get_model(self):
        if self._model is None:
            import vertexai
            from vertexai.language_models import TextEmbeddingModel

            vertexai.init(project=self.project_id, location=self.location)
            self._model = TextEmbeddingModel.from_pretrained(self.model_id)
        return self._model

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._get_model()
        results = model.get_embeddings(list(texts))
        return [list(r.values) for r in results]


def build_embedding_records(
    *,
    chunks: Sequence,  # Chunk-like: index, text, char_count, chunk_id
    vectors: Sequence[Sequence[float]],
    document_id: str,
    version_id: str,
) -> list[EmbeddingRecord]:
    """Zip chunks with vectors into durable records."""
    if len(chunks) != len(vectors):
        raise EmbeddingError("chunks and vectors length mismatch")
    records: list[EmbeddingRecord] = []
    for chunk, vec in zip(chunks, vectors, strict=True):
        records.append(
            EmbeddingRecord(
                chunk_id=str(getattr(chunk, "chunk_id", chunk.index)),
                index=int(chunk.index),
                embedding=list(vec),
                char_count=int(chunk.char_count),
                document_id=document_id,
                version_id=version_id,
            )
        )
    return records
