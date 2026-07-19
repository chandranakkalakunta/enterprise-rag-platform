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


class VectorQueryClient(Protocol):
    """Minimal protocol for FindNeighbors (tests inject fakes)."""

    def find_neighbors(
        self,
        *,
        query_embedding: Sequence[float],
        top_k: int,
        restricts: Sequence[dict[str, Any]],
    ) -> list["NeighborHit"]: ...


@dataclass(frozen=True, slots=True)
class NeighborHit:
    """One dense search neighbor (citation-ready)."""

    datapoint_id: str
    score: float
    document_id: str | None
    version_id: str | None
    chunk_index: int | None
    text: str | None
    title: str | None
    filename: str | None
    collection: str | None
    char_count: int | None


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


def _restricts_to_map(restricts: Sequence[Any]) -> dict[str, str]:
    """Flatten Restriction protos or dicts to namespace → first allow value."""
    out: dict[str, str] = {}
    for r in restricts or []:
        if isinstance(r, dict):
            ns = r.get("namespace")
            allow = r.get("allow_list") or []
        else:
            ns = getattr(r, "namespace", None)
            allow = list(getattr(r, "allow_list", []) or [])
        if ns and allow:
            out[str(ns)] = str(allow[0])
    return out


def parse_datapoint_id(datapoint_id: str) -> tuple[str | None, str | None, int | None]:
    """Parse {document_id}:{version_id}:{chunk_index} (best-effort)."""
    parts = (datapoint_id or "").split(":")
    if len(parts) < 3:
        return None, None, None
    try:
        chunk_index = int(parts[-1])
    except ValueError:
        chunk_index = None
    version_id = parts[-2]
    document_id = ":".join(parts[:-2]) if len(parts) > 3 else parts[0]
    return document_id or None, version_id or None, chunk_index


def neighbor_from_match(
    *,
    datapoint_id: str,
    distance: float,
    restricts: Sequence[Any] | None = None,
) -> NeighborHit:
    """Map a MatchService neighbor to NeighborHit (distance → score)."""
    meta = _restricts_to_map(restricts or [])
    doc_id, ver_id, chunk_idx = parse_datapoint_id(datapoint_id)
    # Prefer restrict metadata over id parse
    document_id = meta.get("document_id") or doc_id
    version_id = meta.get("version_id") or ver_id
    if "chunk_index" in meta:
        try:
            chunk_idx = int(meta["chunk_index"])
        except ValueError:
            pass
    char_count = None
    if "char_count" in meta:
        try:
            char_count = int(meta["char_count"])
        except ValueError:
            char_count = None
    # DOT_PRODUCT: higher is better; distance field is often similarity for this measure
    score = float(distance)
    return NeighborHit(
        datapoint_id=datapoint_id,
        score=score,
        document_id=document_id,
        version_id=version_id,
        chunk_index=chunk_idx,
        text=meta.get("payload_text"),
        title=meta.get("title"),
        filename=meta.get("filename"),
        collection=meta.get("collection"),
        char_count=char_count,
    )


def build_active_restricts(collection: str | None = None) -> list[dict[str, Any]]:
    """Query filters: always active=true; optional collection."""
    restricts: list[dict[str, Any]] = [
        {"namespace": "active", "allow_list": ["true"]},
    ]
    if collection and collection.strip():
        restricts.append(
            {"namespace": "collection", "allow_list": [collection.strip()]}
        )
    return restricts


class VertexMatchClient:
    """FindNeighbors via Vertex AI MatchServiceClient."""

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        endpoint_id: str,
        deployed_index_id: str,
        public_endpoint_domain: str = "",
    ) -> None:
        self.project_id = project_id
        self.location = location
        self.deployed_index_id = deployed_index_id
        if endpoint_id.startswith("projects/"):
            self.endpoint_name = endpoint_id
        else:
            self.endpoint_name = (
                f"projects/{project_id}/locations/{location}/"
                f"indexEndpoints/{endpoint_id}"
            )
        # Public endpoints require the public domain as api_endpoint
        self._api_endpoint = (
            public_endpoint_domain.strip()
            if public_endpoint_domain.strip()
            else f"{location}-aiplatform.googleapis.com"
        )
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import aiplatform_v1
            from google.api_core.client_options import ClientOptions

            self._client = aiplatform_v1.MatchServiceClient(
                client_options=ClientOptions(api_endpoint=self._api_endpoint)
            )
        return self._client

    def find_neighbors(
        self,
        *,
        query_embedding: Sequence[float],
        top_k: int,
        restricts: Sequence[dict[str, Any]],
    ) -> list[NeighborHit]:
        from google.cloud import aiplatform_v1

        if top_k < 1:
            raise VectorSearchError("top_k must be >= 1")
        if not query_embedding:
            raise VectorSearchError("query_embedding is required")

        client = self._get_client()
        proto_restricts = [
            aiplatform_v1.IndexDatapoint.Restriction(
                namespace=r["namespace"],
                allow_list=list(r["allow_list"]),
            )
            for r in restricts
        ]
        datapoint = aiplatform_v1.IndexDatapoint(
            feature_vector=list(query_embedding),
            restricts=proto_restricts,
        )
        query = aiplatform_v1.FindNeighborsRequest.Query(
            datapoint=datapoint,
            neighbor_count=top_k,
        )
        request = aiplatform_v1.FindNeighborsRequest(
            index_endpoint=self.endpoint_name,
            deployed_index_id=self.deployed_index_id,
            queries=[query],
            return_full_datapoint=True,
        )
        try:
            response = client.find_neighbors(request)
        except Exception as exc:  # noqa: BLE001
            raise VectorSearchError(f"FindNeighbors failed: {exc}") from exc

        hits: list[NeighborHit] = []
        nearest = list(response.nearest_neighbors) if response.nearest_neighbors else []
        if not nearest:
            return hits
        for neighbor in nearest[0].neighbors:
            dp = neighbor.datapoint
            datapoint_id = dp.datapoint_id if dp else ""
            distance = float(neighbor.distance) if neighbor.distance is not None else 0.0
            restricts_out = list(dp.restricts) if dp and dp.restricts else []
            hits.append(
                neighbor_from_match(
                    datapoint_id=datapoint_id,
                    distance=distance,
                    restricts=restricts_out,
                )
            )
        logger.info(
            "vector_find_neighbors_ok endpoint=%s hits=%s top_k=%s",
            self.endpoint_name,
            len(hits),
            top_k,
        )
        return hits


def find_neighbors(
    *,
    client: VectorQueryClient,
    query_embedding: Sequence[float],
    top_k: int = 5,
    collection: str | None = None,
) -> list[NeighborHit]:
    """
    Dense search with published-only filter (active=true).

    Optional collection filter is ANDed via restricts.
    """
    restricts = build_active_restricts(collection)
    try:
        return client.find_neighbors(
            query_embedding=query_embedding,
            top_k=top_k,
            restricts=restricts,
        )
    except VectorSearchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise VectorSearchError(f"Search failed: {exc}") from exc
