"""Phase 3.3 — dense search API tests (mocked embed + Vector Search)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.search import SearchServiceError, SearchValidationError, dense_search
from app.services.vector_search import (
    NeighborHit,
    build_active_restricts,
    neighbor_from_match,
    parse_datapoint_id,
)


@pytest.fixture(autouse=True)
def _clear_settings() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "true")
    monkeypatch.setenv("VECTOR_SEARCH_ENABLED", "true")
    monkeypatch.setenv("VECTOR_SEARCH_ENDPOINT_ID", "ep-1")
    monkeypatch.setenv("VECTOR_SEARCH_DEPLOYED_INDEX_ID", "rag_docs_dev")
    monkeypatch.setenv("VECTOR_SEARCH_REGION", "asia-south1")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "5")
    get_settings.cache_clear()
    return TestClient(app)


def test_parse_datapoint_id() -> None:
    d, v, i = parse_datapoint_id("doc-a:ver-b:2")
    assert d == "doc-a"
    assert v == "ver-b"
    assert i == 2


def test_build_active_restricts_with_collection() -> None:
    r = build_active_restricts("policies")
    assert r[0] == {"namespace": "active", "allow_list": ["true"]}
    assert r[1] == {"namespace": "collection", "allow_list": ["policies"]}


def test_neighbor_from_match_uses_restricts() -> None:
    hit = neighbor_from_match(
        datapoint_id="d1:v1:0",
        distance=0.92,
        restricts=[
            {"namespace": "document_id", "allow_list": ["d1"]},
            {"namespace": "version_id", "allow_list": ["v1"]},
            {"namespace": "chunk_index", "allow_list": ["0"]},
            {"namespace": "payload_text", "allow_list": ["Hello chunk"]},
            {"namespace": "title", "allow_list": ["Policy"]},
            {"namespace": "filename", "allow_list": ["p.md"]},
            {"namespace": "collection", "allow_list": ["policies"]},
            {"namespace": "char_count", "allow_list": ["11"]},
        ],
    )
    assert hit.score == 0.92
    assert hit.text == "Hello chunk"
    assert hit.document_id == "d1"
    assert hit.version_id == "v1"
    assert hit.chunk_index == 0
    assert hit.title == "Policy"
    assert hit.filename == "p.md"
    assert hit.collection == "policies"
    assert hit.char_count == 11


def test_dense_search_success() -> None:
    settings = Settings(
        vector_search_enabled=True,
        vector_search_endpoint_id="ep",
        vector_search_deployed_index_id="dep",
        retrieval_top_k=5,
    )
    fake_embedder = MagicMock()
    fake_embedder.embed_texts.return_value = [[0.1] * 8]

    hits = [
        NeighborHit(
            datapoint_id="d1:v1:0",
            score=0.9,
            document_id="d1",
            version_id="v1",
            chunk_index=0,
            text="alpha",
            title="T",
            filename="a.md",
            collection="c",
            char_count=5,
        )
    ]
    fake_query = MagicMock()
    fake_query.find_neighbors.return_value = hits

    with patch("app.services.search.embed_texts") as emb:
        emb.return_value = [[0.1] * 8]
        # dense_search uses find_neighbors helper which calls client
        with patch(
            "app.services.search.find_neighbors",
            return_value=hits,
        ):
            resp = dense_search(
                settings=settings,
                query="what is policy",
                top_k=3,
                collection="c",
                query_client=fake_query,
            )

    assert resp.query == "what is policy"
    assert resp.top_k == 3
    assert len(resp.results) == 1
    assert resp.results[0].text == "alpha"
    assert resp.results[0].document_id == "d1"


def test_dense_search_empty_neighbors() -> None:
    settings = Settings(
        vector_search_enabled=True,
        vector_search_endpoint_id="ep",
        vector_search_deployed_index_id="dep",
    )
    with (
        patch("app.services.search.embed_texts", return_value=[[0.2] * 4]),
        patch("app.services.search.find_neighbors", return_value=[]),
    ):
        resp = dense_search(
            settings=settings,
            query="nothing",
            query_client=MagicMock(),
        )
    assert resp.results == []


def test_dense_search_empty_query() -> None:
    with pytest.raises(SearchValidationError, match="non-empty"):
        dense_search(settings=Settings(), query="   ")


def test_api_search_success(client: TestClient) -> None:
    hits = [
        NeighborHit(
            datapoint_id="doc1:ver1:0",
            score=0.88,
            document_id="doc1",
            version_id="ver1",
            chunk_index=0,
            text="Published chunk text",
            title="Doc",
            filename="doc.md",
            collection="policies",
            char_count=20,
        )
    ]
    with (
        patch("app.services.search.embed_texts", return_value=[[0.1] * 8]),
        patch("app.services.search.find_neighbors", return_value=hits),
        patch("app.services.search._match_client", return_value=MagicMock()),
    ):
        response = client.post(
            "/api/v1/query/search",
            json={"query": "policy leave", "top_k": 5, "collection": "policies"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["query"] == "policy leave"
    assert body["top_k"] == 5
    assert len(body["results"]) == 1
    r0 = body["results"][0]
    assert r0["text"] == "Published chunk text"
    assert r0["score"] == 0.88
    assert r0["document_id"] == "doc1"
    assert r0["version_id"] == "ver1"
    assert r0["chunk_index"] == 0
    assert r0["title"] == "Doc"
    assert r0["filename"] == "doc.md"
    assert r0["datapoint_id"] == "doc1:ver1:0"


def test_api_search_empty_results(client: TestClient) -> None:
    with (
        patch("app.services.search.embed_texts", return_value=[[0.1] * 8]),
        patch("app.services.search.find_neighbors", return_value=[]),
        patch("app.services.search._match_client", return_value=MagicMock()),
    ):
        response = client.post(
            "/api/v1/query/search",
            json={"query": "no hits"},
        )
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_api_search_missing_query_422(client: TestClient) -> None:
    response = client.post("/api/v1/query/search", json={})
    assert response.status_code == 422


def test_api_search_empty_string_query(client: TestClient) -> None:
    # Pydantic min_length=1 → 422; empty after strip → 400 if whitespace-only
    response = client.post("/api/v1/query/search", json={"query": ""})
    assert response.status_code == 422

    with (
        patch("app.services.search.embed_texts", return_value=[[0.1] * 4]),
        patch("app.services.search.find_neighbors", return_value=[]),
        patch("app.services.search._match_client", return_value=MagicMock()),
    ):
        # whitespace-only passes pydantic min_length but dense_search validates
        response2 = client.post("/api/v1/query/search", json={"query": "   "})
    assert response2.status_code == 400
    assert "non-empty" in response2.json()["detail"]


def test_api_search_service_unavailable(client: TestClient) -> None:
    with patch(
        "app.api.v1.query.dense_search",
        side_effect=SearchServiceError("Vector Search is not enabled"),
    ):
        response = client.post(
            "/api/v1/query/search",
            json={"query": "hello"},
        )
    assert response.status_code == 503
