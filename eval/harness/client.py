"""Live API and fixture clients for the eval harness."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol

from eval.harness.load import model_response_from_dict
from eval.harness.models import GoldenCase, ModelResponse, RetrievalHit


class AnswerClient(Protocol):
    def fetch(self, case: GoldenCase, *, top_k: int) -> ModelResponse: ...


class FixtureClient:
    """Map case ids to canned responses (CI / offline baseline)."""

    def __init__(self, mapping: dict[str, ModelResponse]) -> None:
        self._mapping = mapping

    def fetch(self, case: GoldenCase, *, top_k: int) -> ModelResponse:
        if case.id not in self._mapping:
            raise KeyError(f"No fixture response for case id={case.id}")
        # top_k unused for fixtures; hits already capped
        return self._mapping[case.id]


class LiveApiClient:
    """Call POST /api/v1/query/answer (and optionally search) on a running API."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout_s: float = 120.0,
        path: str = "answer",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("EVAL_BEARER_TOKEN") or os.getenv("GOOGLE_ID_TOKEN")
        self.timeout_s = timeout_s
        self.path = path  # answer | search

    def fetch(self, case: GoldenCase, *, top_k: int) -> ModelResponse:
        if self.path == "search":
            return self._search(case.question, top_k=top_k)
        return self._answer(case.question, top_k=top_k)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _post(self, url: str, body: dict) -> dict:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=self._headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Request failed for {url}: {exc}") from exc

    def _answer(self, query: str, *, top_k: int) -> ModelResponse:
        url = f"{self.base_url}/api/v1/query/answer"
        raw = self._post(url, {"query": query, "top_k": top_k})
        return model_response_from_dict(raw, source="live_answer")

    def _search(self, query: str, *, top_k: int) -> ModelResponse:
        url = f"{self.base_url}/api/v1/query/search"
        raw = self._post(url, {"query": query, "top_k": top_k})
        hits = [
            RetrievalHit(
                text=str(r.get("text") or ""),
                filename=r.get("filename"),
                title=r.get("title"),
                document_id=r.get("document_id"),
                score=float(r.get("score") or 0.0),
            )
            for r in (raw.get("results") or [])
            if isinstance(r, dict)
        ]
        # Search-only: no generation; treat as non-refuse with empty answer
        return ModelResponse(
            answer="",
            refused=False,
            hits=hits,
            source="live_search",
        )
