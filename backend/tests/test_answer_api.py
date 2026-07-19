"""Phase 3.4 — grounded answer API tests (mocked retrieve + generate)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.generation import SAFE_REFUSAL_ANSWER, GenerationError
from app.services.search import SearchResponse, SearchResultItem, SearchServiceError
from app.services.answer_graph import run_grounded_answer


@pytest.fixture(autouse=True)
def _clear_settings() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "true")
    monkeypatch.setenv("GENERATION_MODEL_ID", "gemini-2.0-flash-001")
    monkeypatch.setenv("GENERATION_TEMPERATURE", "0.2")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "5")
    get_settings.cache_clear()
    return TestClient(app)


def _hit(
    text: str = "Employees may take 20 days leave per year.",
    score: float = 0.9,
) -> SearchResultItem:
    return SearchResultItem(
        text=text,
        score=score,
        document_id="doc1",
        version_id="ver1",
        chunk_index=0,
        title="Leave Policy",
        filename="leave.md",
        collection="policies",
        datapoint_id="doc1:ver1:0",
        char_count=len(text),
    )


def test_run_grounded_answer_success() -> None:
    settings = Settings(generation_model_id="gemini-2.0-flash-001")
    search_resp = SearchResponse(query="leave?", top_k=5, results=[_hit()])

    def fake_search(**_kwargs):
        return search_resp

    fake_gen = MagicMock()
    fake_gen.generate.return_value = "Staff can take 20 days of leave annually [1]."

    result = run_grounded_answer(
        settings=settings,
        query="How much leave?",
        search_fn=fake_search,
        generator=fake_gen,
    )
    assert result.refused is False
    assert "20 days" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].document_id == "doc1"
    assert result.citations[0].snippet
    assert result.hit_count == 1
    fake_gen.generate.assert_called_once()


def test_run_grounded_answer_refusal_empty_retrieval() -> None:
    settings = Settings()
    empty = SearchResponse(query="x", top_k=5, results=[])

    result = run_grounded_answer(
        settings=settings,
        query="unknown topic",
        search_fn=lambda **_k: empty,
        generator=MagicMock(),
    )
    assert result.refused is True
    assert result.answer == SAFE_REFUSAL_ANSWER
    assert result.citations == []
    assert result.refusal_reason


def test_run_grounded_answer_generation_failure() -> None:
    settings = Settings()
    search_resp = SearchResponse(query="q", top_k=5, results=[_hit()])

    class BadGen:
        def generate(self, prompt: str, *, temperature: float) -> str:
            raise GenerationError("model down")

    with pytest.raises(SearchServiceError, match="model down"):
        run_grounded_answer(
            settings=settings,
            query="leave?",
            search_fn=lambda **_k: search_resp,
            generator=BadGen(),
        )


def test_api_answer_success(client: TestClient) -> None:
    search_resp = SearchResponse(query="leave", top_k=5, results=[_hit()])
    fake_gen = MagicMock()
    fake_gen.generate.return_value = "Answer grounded in policy [1]."

    with (
        patch(
            "app.services.answer_graph.dense_search",
            return_value=search_resp,
        ),
        patch(
            "app.services.answer_graph.generate_grounded_answer",
            return_value="Answer grounded in policy [1].",
        ),
    ):
        response = client.post(
            "/api/v1/query/answer",
            json={"query": "How much leave?", "top_k": 5},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refused"] is False
    assert body["answer"]
    assert body["refusal_reason"] is None
    assert len(body["citations"]) >= 1
    assert body["citations"][0]["document_id"] == "doc1"
    assert body["retrieval"]["top_k"] == 5
    assert body["retrieval"]["hit_count"] == 1


def test_api_answer_refused_empty(client: TestClient) -> None:
    empty = SearchResponse(query="x", top_k=5, results=[])
    with patch("app.services.answer_graph.dense_search", return_value=empty):
        response = client.post(
            "/api/v1/query/answer",
            json={"query": "nothing known"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is True
    assert body["citations"] == []
    assert body["answer"] == SAFE_REFUSAL_ANSWER


def test_api_answer_missing_query_422(client: TestClient) -> None:
    assert client.post("/api/v1/query/answer", json={}).status_code == 422


def test_api_answer_whitespace_query_400(client: TestClient) -> None:
    response = client.post("/api/v1/query/answer", json={"query": "   "})
    assert response.status_code == 400


def test_api_answer_service_error_503(client: TestClient) -> None:
    with patch(
        "app.api.v1.query.run_grounded_answer",
        side_effect=SearchServiceError("generation failed"),
    ):
        response = client.post(
            "/api/v1/query/answer",
            json={"query": "hello"},
        )
    assert response.status_code == 503
    assert "generation failed" in response.json()["detail"]
