"""Phase 4.2 — RRF, BM25 index, hybrid flag behaviour (no live Vertex)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings, get_settings
from app.services.bm25_index import (
    Bm25Chunk,
    InProcessBM25Index,
    reset_bm25_index_for_tests,
    tokenize,
)
from app.services.bm25_ops import (
    bm25_index_published_version,
    bm25_remove_version,
    chunks_from_jsonl_rows,
    parse_chunks_jsonl,
)
from app.services.hybrid_search import hybrid_search
from app.services.rrf import RankedItem, fuse_rrf, rrf_score
from app.services.search import SearchResponse, SearchResultItem


@pytest.fixture(autouse=True)
def _reset_bm25() -> None:
    reset_bm25_index_for_tests()
    get_settings.cache_clear()
    yield
    reset_bm25_index_for_tests()
    get_settings.cache_clear()


def test_rrf_score_basic() -> None:
    assert rrf_score(1, k=60) == pytest.approx(1.0 / 61)
    assert rrf_score(2, k=60) == pytest.approx(1.0 / 62)


def test_fuse_rrf_prefers_shared_and_top_ranks() -> None:
    """Item in both lists ranks above single-list items with same best rank."""
    a = "shared"
    b = "dense-only"
    c = "bm25-only"
    dense = [
        RankedItem(key=a, item="A", rank=1, score=0.9),
        RankedItem(key=b, item="B", rank=2, score=0.8),
    ]
    bm25 = [
        RankedItem(key=c, item="C", rank=1, score=5.0),
        RankedItem(key=a, item="A", rank=2, score=4.0),
    ]
    fused = fuse_rrf([dense, bm25], k=60, top_k=3)
    keys = [k for k, _, _ in fused]
    assert keys[0] == a  # RRF: 1/61 + 1/62
    assert set(keys) == {a, b, c}


def test_tokenize() -> None:
    tokens = tokenize("See datapoint.json bootstrap")
    assert "datapoint.json" in tokens
    assert "bootstrap" in tokens
    assert "rag-oauth-client-id" in tokenize("secret rag-oauth-client-id here")


def test_bm25_search_hits_lexical() -> None:
    idx = InProcessBM25Index()
    idx.upsert_chunks(
        [
            Bm25Chunk(
                document_id="d1",
                version_id="v1",
                chunk_index=0,
                text="Tenant isolation uses collection filters on Vector Search.",
                filename="security.md",
                title="Security",
            ),
            Bm25Chunk(
                document_id="d2",
                version_id="v1",
                chunk_index=0,
                text="The bootstrap contents must be datapoint.json not .keep files.",
                filename="vector-search.md",
                title="Vector Search",
            ),
        ]
    )
    hits = idx.search("datapoint.json bootstrap", top_k=2)
    assert hits
    assert hits[0][0].document_id == "d2"
    assert hits[0][0].datapoint_id == "d2:v1:0"


def test_bm25_remove_version() -> None:
    idx = InProcessBM25Index()
    idx.upsert_chunks(
        [
            Bm25Chunk("d1", "v1", 0, "alpha beta"),
            Bm25Chunk("d1", "v1", 1, "gamma"),
            Bm25Chunk("d1", "v2", 0, "delta"),
        ]
    )
    assert idx.size() == 3
    n = idx.remove_version("d1", "v1")
    assert n == 2
    assert idx.size() == 1
    assert idx.search("delta", top_k=1)[0][0].version_id == "v2"


def test_chunks_from_jsonl_rows() -> None:
    raw = b'{"index":0,"text":"hello world"}\n{"index":1,"text":"  "}\n'
    rows = parse_chunks_jsonl(raw)
    chunks = chunks_from_jsonl_rows(
        rows, document_id="d", version_id="v", filename="a.md"
    )
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].filename == "a.md"


def test_bm25_ops_publish_and_retire_mocked_gcs() -> None:
    settings = Settings(
        hybrid_retrieval_enabled=True,
        gcs_docs_bucket="bucket",
    )
    idx = reset_bm25_index_for_tests()
    payload = b'{"index":0,"text":"RRF fusion for hybrid retrieval"}\n'

    gcs = MagicMock()
    blob = MagicMock()
    blob.download_as_bytes.return_value = payload
    gcs.bucket.return_value.blob.return_value = blob

    status = bm25_index_published_version(
        settings=settings,
        gcs_client=gcs,
        document_id="d1",
        version_id="v2",
        title="Hybrid",
        filename="adr.md",
        previous_version_id="v1",
        index=idx,
    )
    assert status == "indexed"
    assert idx.size() == 1
    assert idx.search("RRF hybrid", top_k=1)[0][0].version_id == "v2"

    status2 = bm25_remove_version(
        document_id="d1", version_id="v2", index=idx, enabled=True
    )
    assert status2 == "removed"
    assert idx.size() == 0


def _item(dp: str, text: str, score: float) -> SearchResultItem:
    doc, ver, idx = dp.split(":")
    return SearchResultItem(
        text=text,
        score=score,
        document_id=doc,
        version_id=ver,
        chunk_index=int(idx),
        title=None,
        filename=f"{doc}.md",
        collection=None,
        datapoint_id=dp,
        char_count=len(text),
    )


def test_hybrid_flag_off_dense_only() -> None:
    settings = Settings(hybrid_retrieval_enabled=False, retrieval_top_k=3)

    def fake_dense(**kwargs):
        return SearchResponse(
            query=kwargs["query"],
            top_k=3,
            results=[_item("d1:v1:0", "dense only", 0.99)],
        )

    resp = hybrid_search(
        settings=settings,
        query="anything",
        dense_fn=fake_dense,
        bm25_index=InProcessBM25Index(),
    )
    assert len(resp.results) == 1
    assert resp.results[0].text == "dense only"


def test_hybrid_fuses_bm25_and_dense() -> None:
    settings = Settings(
        hybrid_retrieval_enabled=True,
        retrieval_top_k=2,
        retrieval_top_k_dense=5,
        retrieval_top_k_bm25=5,
        rrf_k=60,
    )
    idx = InProcessBM25Index()
    idx.upsert_chunks(
        [
            Bm25Chunk("d_bm25", "v1", 0, "exact heading datapoint.json bootstrap"),
            Bm25Chunk("d_other", "v1", 0, "unrelated filler text about weather"),
        ]
    )

    def fake_dense(**kwargs):
        return SearchResponse(
            query=kwargs["query"],
            top_k=5,
            results=[
                _item("d_dense", "v1", 0) if False else _item("d_dense:v1:0", "semantic neighbor", 0.9),
                _item("d_bm25:v1:0", "also dense", 0.5),
            ],
        )

    resp = hybrid_search(
        settings=settings,
        query="datapoint.json bootstrap",
        dense_fn=fake_dense,
        bm25_index=idx,
    )
    assert len(resp.results) <= 2
    keys = [r.datapoint_id for r in resp.results]
    # Shared d_bm25:v1:0 or strong BM25 should appear
    assert "d_bm25:v1:0" in keys


def test_hybrid_empty_bm25_falls_back_dense() -> None:
    settings = Settings(hybrid_retrieval_enabled=True, retrieval_top_k=2)

    def fake_dense(**kwargs):
        return SearchResponse(
            query=kwargs["query"],
            top_k=2,
            results=[_item("d1:v1:0", "only dense", 0.88)],
        )

    resp = hybrid_search(
        settings=settings,
        query="hello",
        dense_fn=fake_dense,
        bm25_index=InProcessBM25Index(),
    )
    assert resp.results[0].text == "only dense"


def test_search_api_uses_hybrid_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("AUTH_DEV_BYPASS", "true")
    monkeypatch.setenv("HYBRID_RETRIEVAL_ENABLED", "true")
    get_settings.cache_clear()

    fake = SearchResponse(
        query="q",
        top_k=5,
        results=[_item("d1:v1:0", "hit", 0.1)],
    )
    with patch("app.api.v1.query.hybrid_search", return_value=fake) as mock_h:
        client = TestClient(app)
        res = client.post("/api/v1/query/search", json={"query": "q"})
    assert res.status_code == 200
    assert res.json()["results"][0]["datapoint_id"] == "d1:v1:0"
    mock_h.assert_called_once()
