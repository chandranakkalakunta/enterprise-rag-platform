"""In-process BM25 index over published chunk text (Phase 4.2 / ADR-0011).

Minimal Okapi BM25 (no external dependency) so CI stays hermetic.
Corpus = currently published/active versions only; reload on publish/retire.

Datapoint id aligns with Vector Search: ``{document_id}:{version_id}:{chunk_index}``.
"""

from __future__ import annotations

import logging
import math
import re
import threading
from dataclasses import dataclass
from typing import Iterable

from app.services.vector_search import build_datapoint_id

logger = logging.getLogger("erp.api.bm25")

_TOKEN_RE = re.compile(r"[a-z0-9_]+(?:[-.][a-z0-9_]+)*", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Bm25Chunk:
    """One indexable published chunk."""

    document_id: str
    version_id: str
    chunk_index: int
    text: str
    title: str | None = None
    filename: str | None = None
    collection: str | None = None

    @property
    def datapoint_id(self) -> str:
        return build_datapoint_id(self.document_id, self.version_id, self.chunk_index)

    def search_text(self) -> str:
        parts = [self.text or ""]
        if self.title:
            parts.append(self.title)
        if self.filename:
            parts.append(self.filename)
        return "\n".join(parts)


def tokenize(text: str) -> list[str]:
    """Lowercased alphanumeric tokens (hyphen/dot kept inside tokens)."""
    if not text:
        return []
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


class InProcessBM25Index:
    """Thread-safe in-memory BM25 over published chunks."""

    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._lock = threading.RLock()
        self._chunks: dict[str, Bm25Chunk] = {}  # datapoint_id -> chunk
        self._doc_tokens: dict[str, list[str]] = {}
        self._df: dict[str, int] = {}
        self._avgdl: float = 0.0
        self._N: int = 0

    def clear(self) -> None:
        with self._lock:
            self._chunks.clear()
            self._doc_tokens.clear()
            self._df.clear()
            self._avgdl = 0.0
            self._N = 0

    def size(self) -> int:
        with self._lock:
            return len(self._chunks)

    def upsert_chunks(self, chunks: Iterable[Bm25Chunk]) -> int:
        """Add or replace chunks (by datapoint_id). Returns count upserted."""
        with self._lock:
            n = 0
            for ch in chunks:
                key = ch.datapoint_id
                if key in self._chunks:
                    self._remove_unlocked(key)
                self._chunks[key] = ch
                tokens = tokenize(ch.search_text())
                self._doc_tokens[key] = tokens
                seen: set[str] = set()
                for t in tokens:
                    if t not in seen:
                        self._df[t] = self._df.get(t, 0) + 1
                        seen.add(t)
                n += 1
            self._recompute_stats()
            logger.info("bm25_upsert count=%s index_size=%s", n, self._N)
            return n

    def remove_version(self, document_id: str, version_id: str) -> int:
        """Remove all chunks for a document version. Returns count removed."""
        with self._lock:
            keys = [
                k
                for k, ch in self._chunks.items()
                if ch.document_id == document_id and ch.version_id == version_id
            ]
            for k in keys:
                self._remove_unlocked(k)
            self._recompute_stats()
            logger.info(
                "bm25_remove_version document_id=%s version_id=%s removed=%s",
                document_id,
                version_id,
                len(keys),
            )
            return len(keys)

    def remove_datapoint(self, datapoint_id: str) -> bool:
        with self._lock:
            if datapoint_id not in self._chunks:
                return False
            self._remove_unlocked(datapoint_id)
            self._recompute_stats()
            return True

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        collection: str | None = None,
    ) -> list[tuple[Bm25Chunk, float]]:
        """Return top_k (chunk, score) sorted by BM25 score desc."""
        q = (query or "").strip()
        if not q or top_k < 1:
            return []
        q_tokens = tokenize(q)
        if not q_tokens:
            return []

        with self._lock:
            if self._N == 0:
                return []
            scores: list[tuple[str, float]] = []
            for key, tokens in self._doc_tokens.items():
                ch = self._chunks[key]
                if collection and (ch.collection or "") != collection:
                    continue
                s = self._score_doc(q_tokens, tokens)
                if s > 0:
                    scores.append((key, s))
            scores.sort(key=lambda x: (-x[1], x[0]))
            out: list[tuple[Bm25Chunk, float]] = []
            for key, s in scores[:top_k]:
                out.append((self._chunks[key], s))
            return out

    def _score_doc(self, q_tokens: list[str], doc_tokens: list[str]) -> float:
        if not doc_tokens or self._N == 0:
            return 0.0
        tf: dict[str, int] = {}
        for t in doc_tokens:
            tf[t] = tf.get(t, 0) + 1
        dl = len(doc_tokens)
        score = 0.0
        avgdl = self._avgdl or 1.0
        for qt in set(q_tokens):
            f = tf.get(qt, 0)
            if f == 0:
                continue
            df = self._df.get(qt, 0)
            # idf with +1 smoothing (Robertson/Sparck Jones style variant)
            idf = math.log(1.0 + (self._N - df + 0.5) / (df + 0.5))
            denom = f + self.k1 * (1.0 - self.b + self.b * dl / avgdl)
            score += idf * (f * (self.k1 + 1.0)) / denom
        return score

    def _remove_unlocked(self, key: str) -> None:
        tokens = self._doc_tokens.pop(key, [])
        self._chunks.pop(key, None)
        seen: set[str] = set()
        for t in tokens:
            if t in seen:
                continue
            seen.add(t)
            if t in self._df:
                self._df[t] -= 1
                if self._df[t] <= 0:
                    del self._df[t]

    def _recompute_stats(self) -> None:
        self._N = len(self._doc_tokens)
        if self._N == 0:
            self._avgdl = 0.0
            return
        total = sum(len(toks) for toks in self._doc_tokens.values())
        self._avgdl = total / self._N


# Process-wide singleton (one index per API instance)
_GLOBAL_INDEX: InProcessBM25Index | None = None
_GLOBAL_LOCK = threading.Lock()


def get_bm25_index() -> InProcessBM25Index:
    global _GLOBAL_INDEX
    with _GLOBAL_LOCK:
        if _GLOBAL_INDEX is None:
            _GLOBAL_INDEX = InProcessBM25Index()
        return _GLOBAL_INDEX


def reset_bm25_index_for_tests() -> InProcessBM25Index:
    """Replace global index (unit tests only)."""
    global _GLOBAL_INDEX
    with _GLOBAL_LOCK:
        _GLOBAL_INDEX = InProcessBM25Index()
        return _GLOBAL_INDEX
