"""Shared pytest fixtures (Phase 3.1+)."""

from __future__ import annotations

from typing import Sequence
from unittest.mock import patch

import pytest


class FakeEmbedder:
    """Deterministic embedder for unit tests (no Vertex calls)."""

    def __init__(self, dim: int = 8, fail: bool = False) -> None:
        self.dim = dim
        self.fail = fail
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        if self.fail:
            raise RuntimeError("simulated vertex failure")
        return [[float(i % 3) * 0.1] * self.dim for i, _ in enumerate(texts)]


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def mock_embed_texts_success(fake_embedder: FakeEmbedder):
    """Patch upload.embed_texts to use FakeEmbedder (avoids real Vertex)."""

    def _impl(texts, **kwargs):
        return fake_embedder.embed_texts(texts)

    with patch("app.services.upload.embed_texts", side_effect=_impl) as mock:
        yield mock, fake_embedder
