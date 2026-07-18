"""Unit tests for Vector Search datapoints + lifecycle ops (Phase 3.2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.vector_search import (
    ChunkEmbeddingInput,
    VectorSearchError,
    build_datapoint_id,
    build_datapoints,
    join_chunks_and_embeddings,
    set_active_for_version,
    upsert_version_vectors,
)
from app.services.vector_ops import (
    activate_version_vectors,
    deactivate_version_vectors,
    upsert_inactive_after_embed,
)


def test_datapoint_id_format() -> None:
    assert build_datapoint_id("doc1", "ver2", 3) == "doc1:ver2:3"


def test_build_datapoints_metadata_shape() -> None:
    items = [
        ChunkEmbeddingInput(
            index=0,
            text="Hello world",
            char_count=11,
            embedding=[0.1, 0.2, 0.3],
        )
    ]
    points = build_datapoints(
        document_id="d1",
        version_id="v1",
        items=items,
        active=False,
        collection="policies",
        title="T",
        filename="a.md",
    )
    assert len(points) == 1
    p = points[0]
    assert p["datapoint_id"] == "d1:v1:0"
    assert p["feature_vector"] == [0.1, 0.2, 0.3]
    namespaces = {r["namespace"]: r["allow_list"][0] for r in p["restricts"]}
    assert namespaces["active"] == "false"
    assert namespaces["collection"] == "policies"
    assert namespaces["document_id"] == "d1"
    assert namespaces["version_id"] == "v1"
    assert namespaces["payload_text"] == "Hello world"
    assert namespaces["title"] == "T"
    assert namespaces["filename"] == "a.md"


def test_build_datapoints_active_true() -> None:
    items = [
        ChunkEmbeddingInput(index=1, text="x", char_count=1, embedding=[1.0])
    ]
    p = build_datapoints(
        document_id="d", version_id="v", items=items, active=True
    )[0]
    active = next(r for r in p["restricts"] if r["namespace"] == "active")
    assert active["allow_list"] == ["true"]


def test_join_chunks_and_embeddings() -> None:
    chunks = [{"index": 0, "text": "aa", "char_count": 2}]
    embs = [{"index": 0, "embedding": [0.5, 0.5]}]
    items = join_chunks_and_embeddings(chunks, embs)
    assert items[0].text == "aa"
    assert items[0].embedding == [0.5, 0.5]


def test_join_missing_embedding_raises() -> None:
    with pytest.raises(VectorSearchError, match="Missing embedding"):
        join_chunks_and_embeddings([{"index": 0, "text": "a"}], [])


def test_upsert_calls_client() -> None:
    fake = MagicMock()
    items = [
        ChunkEmbeddingInput(index=0, text="t", char_count=1, embedding=[0.1])
    ]
    result = upsert_version_vectors(
        client=fake,
        document_id="d",
        version_id="v",
        items=items,
        active=False,
        index_id="idx",
    )
    fake.upsert_datapoints.assert_called_once()
    args = fake.upsert_datapoints.call_args[0][0]
    assert args[0]["datapoint_id"] == "d:v:0"
    assert result.datapoint_count == 1
    assert result.active is False


def test_set_active_reupserts_true() -> None:
    fake = MagicMock()
    items = [
        ChunkEmbeddingInput(index=0, text="t", char_count=1, embedding=[0.1])
    ]
    set_active_for_version(
        client=fake,
        document_id="d",
        version_id="v",
        items=items,
        active=True,
    )
    restricts = fake.upsert_datapoints.call_args[0][0][0]["restricts"]
    active = next(r for r in restricts if r["namespace"] == "active")
    assert active["allow_list"] == ["true"]


def test_upsert_inactive_after_embed_skipped_when_disabled() -> None:
    settings = Settings(vector_search_enabled=False, vector_search_index_id="")
    fs = MagicMock()
    # version_ref chain
    vref = MagicMock()
    fs.collection.return_value.document.return_value.collection.return_value.document.return_value = (
        vref
    )
    status = upsert_inactive_after_embed(
        settings=settings,
        gcs_client=MagicMock(),
        fs_client=fs,
        document_id="d",
        version_id="v",
        collection=None,
        title=None,
        filename=None,
        items=[
            ChunkEmbeddingInput(index=0, text="t", char_count=1, embedding=[0.1])
        ],
    )
    assert status == "skipped"


def test_upsert_inactive_after_embed_success() -> None:
    settings = Settings(
        vector_search_enabled=True,
        vector_search_index_id="idx-1",
    )
    fs = MagicMock()
    vref = MagicMock()
    fs.collection.return_value.document.return_value.collection.return_value.document.return_value = (
        vref
    )
    fake_idx = MagicMock()
    status = upsert_inactive_after_embed(
        settings=settings,
        gcs_client=MagicMock(),
        fs_client=fs,
        document_id="d",
        version_id="v",
        collection="c",
        title="T",
        filename="f.md",
        items=[
            ChunkEmbeddingInput(index=0, text="t", char_count=1, embedding=[0.1])
        ],
        index_client=fake_idx,
    )
    assert status == "upserted"
    fake_idx.upsert_datapoints.assert_called_once()
    patch = vref.update.call_args[0][0]
    assert patch["vector_status"] == "upserted"


def test_activate_and_deactivate_ops() -> None:
    settings = Settings(
        vector_search_enabled=True,
        vector_search_index_id="idx-1",
    )
    fs = MagicMock()
    vref = MagicMock()
    fs.collection.return_value.document.return_value.collection.return_value.document.return_value = (
        vref
    )
    items = [
        ChunkEmbeddingInput(index=0, text="t", char_count=1, embedding=[0.1])
    ]
    fake = MagicMock()
    with patch(
        "app.services.vector_ops.load_version_chunk_embeddings",
        return_value=items,
    ):
        assert (
            activate_version_vectors(
                settings=settings,
                gcs_client=MagicMock(),
                fs_client=fs,
                document_id="d",
                version_id="v",
                index_client=fake,
            )
            == "activated"
        )
        assert (
            deactivate_version_vectors(
                settings=settings,
                gcs_client=MagicMock(),
                fs_client=fs,
                document_id="d",
                version_id="v",
                index_client=fake,
            )
            == "deactivated"
        )
    assert fake.upsert_datapoints.call_count == 2
