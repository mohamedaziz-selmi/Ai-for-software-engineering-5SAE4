"""Memory-capped, grounded product retrieval for the Amazon-2023-GenQ data."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from .llm import call_json, prompt

ROOT = Path(__file__).parents[1]
INDEX_PATH = ROOT / "artifacts" / "product_rag.joblib"

@lru_cache(maxsize=1)
def _catalog(stamp):
    return joblib.load(INDEX_PATH)


def retrieve(query: str, top_k: int = 3, category: str | None = None) -> list[dict]:
    if not INDEX_PATH.exists():
        return []
    artifact = _catalog(INDEX_PATH.stat().st_mtime_ns)
    matrix = artifact["vectorizer"].transform([query])
    dense_scores = (matrix @ artifact["matrix"].T).toarray()[0]
    query_terms = set(re.findall(r"[a-z0-9]+", query.lower())) - {'the','a','for','with','and','of','to','my','i','in','is'}
    if not query_terms: return []
    category_terms = set(re.findall(r"[a-z0-9]+", (category or "").lower()))
    hybrid_scores = []
    for i, row in enumerate(artifact["records"]):
        row_category = str(row.get("main_category", "")).lower()
        if category_terms and not category_terms.intersection(set(re.findall(r"[a-z0-9]+", row_category))):
            hybrid_scores.append(float("-inf"))
            continue
        text = (str(row.get('title',''))+' '+str(row.get('short_query',''))).lower()
        terms = set(re.findall(r"[a-z0-9]+", text))
        lexical = len(query_terms & terms) / max(1, len(query_terms))
        # Conservative abstention: no single incidental token may justify a result.
        if lexical < .6 or float(dense_scores[i]) < .08:
            hybrid_scores.append(float('-inf'))
            continue
        hybrid_scores.append(0.75 * float(dense_scores[i]) + 0.25 * lexical)
    indexes = [i for i in sorted(range(len(hybrid_scores)), key=lambda i: hybrid_scores[i], reverse=True) if hybrid_scores[i] > 0][:top_k]
    records = []
    for index in indexes:
        row = artifact["records"][int(index)]
        records.append({**row, "retrieval_score": round(float(hybrid_scores[index]), 4), "retrieval_method": "TF-IDF + title coverage; category filtered", "retrieval_reason": "Category and query-title coverage passed conservative heuristics; relevance is not a calibrated probability."})
    return records


def grounded_listing(query: str, category: str, specifications: dict[str, str], language: str, top_k: int) -> dict:
    if re.search(r"\bapple\s+15\b", query.lower()) and "iphone" not in query.lower():
        return {"status": "clarification_required", "suggestion": "Did you mean Apple iPhone 15?", "reason": "The query is ambiguous; confirm the product model before retrieval."}
    references = retrieve(query, top_k, category)
    context = json.dumps(references, ensure_ascii=False)
    payload = {"query": query, "category": category, "specifications": specifications, "language": language, "grounding_rule": "Use only user-provided specifications. No catalog specifications may be transferred to this product."}
    generated, source = call_json(prompt("listing_v1.txt") + '\nOnly user-provided facts are available. Do not invent missing specifications or imply catalog verification.', payload)
    if not generated or not isinstance(generated.get("title"), str) or not isinstance(generated.get("description"), str):
        return {"status": "unavailable", "reason": "A configured LLM is required for product listing generation.", "references": references, "provider_status": source}
    generated["status"] = "complete"
    generated["references"] = references
    generated["grounding_context"] = context
    generated["hallucination_guard"] = "User-provided facts only. Catalog references are comparison material, not verified product specifications."
    generated["retrieval_status"] = "comparison_references" if references else "No sufficiently relevant catalog references were found."
    generated["source"] = source
    return generated
