"""Vertex AI Vector Search upsert + active flag updates (Phase 3.2 / ADR-0007).

Datapoint id: {document_id}:{version_id}:{chunk_index}

Restrict namespaces (filters):
  active, collection, document_id, version_id

Payload text for query-time grounding is stored under restrict namespace
``payload_text`` (returned when FindNeighbors uses return_full_datapoint).

No re-embed on publish/retire: re-upsert from GCS embeddings.jsonl + chunks.jsonl
with updated ``active`` only.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

logger = logging.getLogger("erp.api.vector_search")

# text-embedding-005 default output dimensionality
DEFAULT_EMBEDDING_DIMENSIONS = 768

# Max chars stored in payload_text restrict (Vector Search restrict value limits)
MAX_PAYLOAD_TEXT_CHARS = 1000


class VectorSearchError(Exception):
    """Raised when Vector Search operations fail."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class VectorIndexClient(Protocol):
    """Minimal protocol for upsert (tests inject fakes)."""

    def upsert_datapoints(self, datapoints: Sequence[dict[str, Any]]) -> None: ...


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingInput:
    """Joined chunk + embedding for datapoint build."""

    index: int
    text: str
    char_count: int
    embedding: list[float]


@dataclass(frozen=True, slots=True)
class VectorUpsertResult:
    datapoint_count: int
    active: bool
    index_id: str


def build_datapoint_id(document_id: str, version_id: str, chunk_index: int) -> str:
    """Stable datapoint id: {document_id}:{version_id}:{chunk_index}."""
    return f"{document_id}:{version_id}:{chunk_index}"


def _restriction(namespace: str, value: str) -> dict[str, Any]:
    return {"namespace": namespace, "allow_list": [value]}


def build_datapoint_dict(
    *,
    document_id: str,
    version_id: str,
    chunk_index: int,
    embedding: Sequence[float],
    text: str,
    char_count: int,
    active: bool,
    collection: str | None = None,
    title: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Build one stream-update datapoint as a plain dict (proto-friendly).

    Restricts used as both filters and lightweight payload carriers.
    """
    payload = (text or "")[:MAX_PAYLOAD_TEXT_CHARS]
    restricts = [
        _restriction("active", "true" if active else "false"),
        _restriction("collection", collection or "_none"),
        _restriction("document_id", document_id),
        _restriction("version_id", version_id),
        _restriction("chunk_index", str(chunk_index)),
        _restriction("payload_text", payload if payload else " "),
        _restriction("char_count", str(char_count)),
    ]
    if title:
        restricts.append(_restriction("title", title[:200]))
    if filename:
        restricts.append(_restriction("filename", filename[:200]))

    return {
        "datapoint_id": build_datapoint_id(document_id, version_id, chunk_index),
        "feature_vector": list(embedding),
        "restricts": restricts,
    }


def build_datapoints(
    *,
    document_id: str,
    version_id: str,
    items: Sequence[ChunkEmbeddingInput],
    active: bool,
    collection: str | None = None,
    title: str | None = None,
    filename: str | None = None,
) -> list[dict[str, Any]]:
    """Build full datapoint list for a document version."""
    out: list[dict[str, Any]] = []
    for item in items:
        if not item.embedding:
            raise VectorSearchError(f"Empty embedding at chunk index {item.index}")
        out.append(
            build_datapoint_dict(
                document_id=document_id,
                version_id=version_id,
                chunk_index=item.index,
                embedding=item.embedding,
                text=item.text,
                char_count=item.char_count,
                active=active,
                collection=collection,
                title=title,
                filename=filename,
            )
        )
    return out


def join_chunks_and_embeddings(
    chunks_rows: Sequence[dict[str, Any]],
    embeddings_rows: Sequence[dict[str, Any]],
) -> list[ChunkEmbeddingInput]:
    """Join chunks.jsonl and embeddings.jsonl rows by index."""
    emb_by_index: dict[int, dict[str, Any]] = {}
    for row in embeddings_rows:
        emb_by_index[int(row["index"])] = row

    items: list[ChunkEmbeddingInput] = []
    for crow in chunks_rows:
        idx = int(crow["index"])
        erow = emb_by_index.get(idx)
        if erow is None:
            raise VectorSearchError(f"Missing embedding for chunk index {idx}")
        emb = erow.get("embedding")
        if not emb:
            raise VectorSearchError(f"Empty embedding for chunk index {idx}")
        items.append(
            ChunkEmbeddingInput(
                index=idx,
                text=str(crow.get("text") or ""),
                char_count=int(crow.get("char_count") or len(crow.get("text") or "")),
                embedding=list(emb),
            )
        )
    if not items:
        raise VectorSearchError("No chunks to upsert")
    return items


def parse_jsonl_bytes(data: bytes) -> list[dict[str, Any]]:
    """Parse NDJSON bytes into list of objects."""
    rows: list[dict[str, Any]] = []
    for line in data.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


class VertexIndexClient:
    """Upsert via Vertex AI IndexServiceClient (STREAM_UPDATE indexes)."""

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        index_id: str,
    ) -> None:
        self.project_id = project_id
        self.location = location
        # index_id may be short id or full resource name
        if index_id.startswith("projects/"):
            self.index_name = index_id
        else:
            self.index_name = (
                f"projects/{project_id}/locations/{location}/indexes/{index_id}"
            )
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import aiplatform_v1
            from google.api_core.client_options import ClientOptions

            self._client = aiplatform_v1.IndexServiceClient(
                client_options=ClientOptions(
                    api_endpoint=f"{self.location}-aiplatform.googleapis.com"
                )
            )
        return self._client

    def upsert_datapoints(self, datapoints: Sequence[dict[str, Any]]) -> None:
        from google.cloud import aiplatform_v1

        client = self._get_client()
        proto_points = []
        for d in datapoints:
            restricts = [
                aiplatform_v1.IndexDatapoint.Restriction(
                    namespace=r["namespace"],
                    allow_list=list(r["allow_list"]),
                )
                for r in d.get("restricts", [])
            ]
            proto_points.append(
                aiplatform_v1.IndexDatapoint(
                    datapoint_id=d["datapoint_id"],
                    feature_vector=list(d["feature_vector"]),
                    restricts=restricts,
                )
            )
        # Batch in chunks of 100
        batch_size = 100
        for i in range(0, len(proto_points), batch_size):
            batch = proto_points[i : i + batch_size]
            client.upsert_datapoints(
                request=aiplatform_v1.UpsertDatapointsRequest(
                    index=self.index_name,
                    datapoints=batch,
                )
            )
        logger.info(
            "vector_upsert_ok index=%s count=%s",
            self.index_name,
            len(proto_points),
        )


def upsert_version_vectors(
    *,
    client: VectorIndexClient,
    document_id: str,
    version_id: str,
    items: Sequence[ChunkEmbeddingInput],
    active: bool,
    collection: str | None = None,
    title: str | None = None,
    filename: str | None = None,
    index_id: str = "",
) -> VectorUpsertResult:
    """Build datapoints and upsert to the index."""
    datapoints = build_datapoints(
        document_id=document_id,
        version_id=version_id,
        items=items,
        active=active,
        collection=collection,
        title=title,
        filename=filename,
    )
    try:
        client.upsert_datapoints(datapoints)
    except VectorSearchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise VectorSearchError(f"Upsert failed: {exc}") from exc
    return VectorUpsertResult(
        datapoint_count=len(datapoints),
        active=active,
        index_id=index_id,
    )


def set_active_for_version(
    *,
    client: VectorIndexClient,
    document_id: str,
    version_id: str,
    items: Sequence[ChunkEmbeddingInput],
    active: bool,
    collection: str | None = None,
    title: str | None = None,
    filename: str | None = None,
    index_id: str = "",
) -> VectorUpsertResult:
    """
    Set active flag for all datapoints of a version (re-upsert, no re-embed).

    Callers load embeddings+chunks from GCS and pass ``items``.
    """
    return upsert_version_vectors(
        client=client,
        document_id=document_id,
        version_id=version_id,
        items=items,
        active=active,
        collection=collection,
        title=title,
        filename=filename,
        index_id=index_id,
    )


def deactivate_version(
    *,
    client: VectorIndexClient,
    document_id: str,
    version_id: str,
    items: Sequence[ChunkEmbeddingInput],
    collection: str | None = None,
    title: str | None = None,
    filename: str | None = None,
    index_id: str = "",
) -> VectorUpsertResult:
    """Convenience: set active=false for a version."""
    return set_active_for_version(
        client=client,
        document_id=document_id,
        version_id=version_id,
        items=items,
        active=False,
        collection=collection,
        title=title,
        filename=filename,
        index_id=index_id,
    )
