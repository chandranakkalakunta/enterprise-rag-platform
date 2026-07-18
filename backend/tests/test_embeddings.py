"""Unit tests for embedding service (Phase 3.1)."""

from __future__ import annotations

import pytest

from app.services.chunking import Chunk
from app.services.embeddings import (
    DEFAULT_EMBEDDING_MODEL_ID,
    EmbeddingError,
    build_embedding_records,
    embed_texts,
)
from tests.conftest import FakeEmbedder


def test_default_model_id() -> None:
    assert DEFAULT_EMBEDDING_MODEL_ID == "text-embedding-005"


def test_embed_texts_success() -> None:
    fake = FakeEmbedder(dim=4)
    vectors = embed_texts(
        ["hello", "world"],
        model_id="text-embedding-005",
        project_id="test-project",
        location="asia-south1",
        embedder=fake,
    )
    assert len(vectors) == 2
    assert len(vectors[0]) == 4
    assert len(fake.calls) == 1


def test_embed_texts_batches() -> None:
    fake = FakeEmbedder(dim=2)
    texts = [f"t{i}" for i in range(5)]
    vectors = embed_texts(
        texts,
        model_id="text-embedding-005",
        project_id="p",
        location="asia-south1",
        batch_size=2,
        embedder=fake,
    )
    assert len(vectors) == 5
    assert len(fake.calls) == 3  # 2+2+1


def test_embed_texts_empty_list() -> None:
    fake = FakeEmbedder()
    assert (
        embed_texts(
            [],
            model_id="text-embedding-005",
            project_id="p",
            location="l",
            embedder=fake,
        )
        == []
    )


def test_embed_texts_rejects_empty_string() -> None:
    with pytest.raises(EmbeddingError, match="Empty text"):
        embed_texts(
            ["ok", "  "],
            model_id="text-embedding-005",
            project_id="p",
            location="l",
            embedder=FakeEmbedder(),
        )


def test_embed_texts_propagates_client_error() -> None:
    with pytest.raises(EmbeddingError, match="Vertex embedding failed"):
        embed_texts(
            ["a"],
            model_id="text-embedding-005",
            project_id="p",
            location="l",
            embedder=FakeEmbedder(fail=True),
        )


def test_build_embedding_records() -> None:
    chunks = [
        Chunk(index=0, text="aa", char_count=2, start_offset=0, end_offset=2),
        Chunk(index=1, text="bb", char_count=2, start_offset=2, end_offset=4),
    ]
    records = build_embedding_records(
        chunks=chunks,
        vectors=[[0.1, 0.2], [0.3, 0.4]],
        document_id="d1",
        version_id="v1",
    )
    assert len(records) == 2
    d = records[0].to_jsonl_dict()
    assert d["chunk_id"] == "0"
    assert d["index"] == 0
    assert d["document_id"] == "d1"
    assert d["version_id"] == "v1"
    assert d["embedding"] == [0.1, 0.2]
    assert d["char_count"] == 2
