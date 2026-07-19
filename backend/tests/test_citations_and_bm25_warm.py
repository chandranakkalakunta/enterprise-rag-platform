"""Phase 4.3 — citation dedupe + BM25 warm-start rebuild."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.bm25_index import reset_bm25_index_for_tests
from app.services.bm25_ops import (
    list_published_pointers,
    rebuild_bm25_from_published,
)
from app.services.citations import dedupe_citations_by_document
from app.services.search import SearchResponse, SearchResultItem


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_bm25_index_for_tests()
    get_settings.cache_clear()
    yield
    reset_bm25_index_for_tests()
    get_settings.cache_clear()


@dataclass
class FakeCite:
    document_id: str | None
    version_id: str | None
    chunk_index: int | None
    title: str | None
    filename: str | None
    snippet: str
    score: float


def test_dedupe_keeps_best_score_per_doc() -> None:
    cites = [
        FakeCite("d1", "v1", 0, "T", "a.md", "first chunk", 0.5),
        FakeCite("d1", "v1", 1, "T", "a.md", "second chunk about tables", 0.9),
        FakeCite("d2", "v1", 0, "U", "b.md", "other doc", 0.7),
        FakeCite("d1", "v1", 2, "T", "a.md", "third", 0.4),
    ]
    out = dedupe_citations_by_document(cites, max_per_doc=1, merge_snippets=False)
    assert len(out) == 2
    by_doc = {c.document_id: c for c in out}
    assert by_doc["d1"].score == 0.9
    assert by_doc["d1"].snippet == "second chunk about tables"
    assert by_doc["d2"].document_id == "d2"


def test_dedupe_merge_snippets() -> None:
    cites = [
        FakeCite("d1", "v1", 0, "T", "a.md", "Alpha paragraph about leave policy", 0.95),
        FakeCite("d1", "v1", 1, "T", "a.md", "Beta paragraph about sick days", 0.8),
    ]
    out = dedupe_citations_by_document(cites, max_per_doc=1, merge_snippets=True)
    assert len(out) == 1
    assert "Alpha" in out[0].snippet
    assert "|" in out[0].snippet
    assert "Beta" in out[0].snippet


def test_dedupe_max_per_doc_two() -> None:
    cites = [
        FakeCite("d1", "v1", 0, None, None, "a", 0.9),
        FakeCite("d1", "v1", 1, None, None, "b", 0.8),
        FakeCite("d1", "v1", 2, None, None, "c", 0.7),
    ]
    out = dedupe_citations_by_document(cites, max_per_doc=2, merge_snippets=False)
    assert len(out) == 2
    assert out[0].score >= out[1].score


def test_list_published_pointers() -> None:
    fs = MagicMock()
    doc_snap = MagicMock()
    doc_snap.id = "doc-a"
    doc_snap.to_dict.return_value = {
        "active_version_id": "ver-1",
        "title": "Policy",
        "collection": "hr",
    }
    v_snap = MagicMock()
    v_snap.exists = True
    v_snap.to_dict.return_value = {"status": "published", "filename": "p.md"}

    col = MagicMock()
    fs.collection.return_value = col
    col.limit.return_value.stream.return_value = [doc_snap]
    col.document.return_value.collection.return_value.document.return_value.get.return_value = (
        v_snap
    )

    ptrs = list_published_pointers(fs, max_docs=10)
    assert len(ptrs) == 1
    assert ptrs[0]["document_id"] == "doc-a"
    assert ptrs[0]["version_id"] == "ver-1"
    assert ptrs[0]["filename"] == "p.md"


def test_rebuild_bm25_from_published_mocked() -> None:
    settings = Settings(
        hybrid_retrieval_enabled=True,
        gcs_docs_bucket="bkt",
        bm25_warm_start_max_docs=10,
    )
    idx = reset_bm25_index_for_tests()
    payload = b'{"index":0,"text":"warm start chunk about hybrid retrieval"}\n'

    gcs = MagicMock()
    blob = MagicMock()
    blob.download_as_bytes.return_value = payload
    gcs.bucket.return_value.blob.return_value = blob

    with patch(
        "app.services.bm25_ops.list_published_pointers",
        return_value=[
            {
                "document_id": "d1",
                "version_id": "v1",
                "title": "T",
                "collection": None,
                "filename": "a.md",
            }
        ],
    ):
        result = rebuild_bm25_from_published(
            settings=settings, gcs_client=gcs, fs_client=MagicMock(), index=idx
        )
    assert result["status"] == "ok"
    assert result["documents"] == 1
    assert result["chunks"] >= 1
    assert idx.size() >= 1
    hits = idx.search("hybrid retrieval", top_k=1)
    assert hits


def test_api_answer_dedupes_same_document_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "true")
    monkeypatch.setenv("CITATION_MAX_PER_DOC", "1")
    get_settings.cache_clear()

    hits = [
        SearchResultItem(
            text="Chunk one about leave accrual rates in the handbook.",
            score=0.5,
            document_id="doc1",
            version_id="v1",
            chunk_index=0,
            title="Handbook",
            filename="hr.md",
            collection=None,
            datapoint_id="doc1:v1:0",
            char_count=50,
        ),
        SearchResultItem(
            text="Chunk two about leave carryover rules in the handbook.",
            score=0.9,
            document_id="doc1",
            version_id="v1",
            chunk_index=1,
            title="Handbook",
            filename="hr.md",
            collection=None,
            datapoint_id="doc1:v1:1",
            char_count=50,
        ),
        SearchResultItem(
            text="Different document on expense policy.",
            score=0.6,
            document_id="doc2",
            version_id="v1",
            chunk_index=0,
            title="Expenses",
            filename="exp.md",
            collection=None,
            datapoint_id="doc2:v1:0",
            char_count=40,
        ),
    ]
    search_resp = SearchResponse(query="leave", top_k=5, results=hits)
    client = TestClient(app)
    with (
        patch("app.services.answer_graph.hybrid_search", return_value=search_resp),
        patch(
            "app.services.answer_graph.generate_grounded_answer",
            return_value="Leave is described in the handbook [1].",
        ),
    ):
        response = client.post(
            "/api/v1/query/answer",
            json={"query": "How does leave work?"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    docs = [c["document_id"] for c in body["citations"]]
    assert docs.count("doc1") == 1
    assert "doc2" in docs
    # Best score for doc1 should win (0.9)
    doc1 = next(c for c in body["citations"] if c["document_id"] == "doc1")
    assert doc1["score"] == 0.9
