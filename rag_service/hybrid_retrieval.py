"""BM25 lexical retrieval and reciprocal-rank fusion for Cerebro RAG."""

from __future__ import annotations

import re
from collections import Counter

from rank_bm25 import BM25Okapi

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RRF_K = 60


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class BM25Index:
    def __init__(self, records: list[dict]):
        self.records = records
        self.bm25 = BM25Okapi([tokenize(record["text"]) for record in records])

    def search(self, query: str, limit: int, category: str | None = None) -> list[dict]:
        scores = self.bm25.get_scores(tokenize(query))
        matches = [
            {**record, "bm25_score": float(score)}
            for record, score in zip(self.records, scores)
            if category is None or record["source"].get("category") == category
        ]
        return sorted(matches, key=lambda result: result["bm25_score"], reverse=True)[:limit]


def fuse_rrf(semantic: list[dict], lexical: list[dict], limit: int) -> list[dict]:
    """Merge rankings, preserving source content and exposing fusion evidence."""
    merged: dict[str, dict] = {}
    for method, results in (("semantic", semantic), ("bm25", lexical)):
        for rank, result in enumerate(results, start=1):
            key = result["id"]
            entry = merged.setdefault(key, {**result, "rrf_score": 0.0, "ranks": {}})
            entry["rrf_score"] += 1 / (RRF_K + rank)
            entry["ranks"][method] = rank
    return sorted(merged.values(), key=lambda result: result["rrf_score"], reverse=True)[:limit]


def distribution(records: list[dict]) -> dict[str, int]:
    return dict(Counter(record["source"].get("category", "other") for record in records))
