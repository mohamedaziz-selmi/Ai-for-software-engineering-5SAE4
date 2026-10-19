"""Build a representative, disk-persisted product retrieval index."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.resource_guard import ResourceGuard  # noqa: E402


def main() -> None:
    guard = ResourceGuard()
    if not guard.safe_to_start():
        raise RuntimeError("ResourceGuard denied index build")
    files = sorted((ROOT / "data/phase2/huggingface/product_listing/data").glob("*.parquet"))
    if not files:
        raise FileNotFoundError("Amazon-2023-GenQ Parquet files are unavailable")
    parts = [pd.read_parquet(path).head(1250) for path in files]
    frame = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["parent_asin", "title"])
    frame["retrieval_text"] = frame[["main_category", "title", "description", "brand", "short_query", "long_query"]].fillna("").astype(str).agg(" ".join, axis=1)
    vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1, 2), min_df=2, stop_words="english")
    matrix = vectorizer.fit_transform(frame["retrieval_text"])
    columns = ["parent_asin", "main_category", "title", "description", "features", "embellished_description", "brand", "short_query", "long_query"]
    records = frame[columns].fillna("").to_dict("records")
    output = ROOT / "ai-service/artifacts/product_rag.joblib"
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "records": records, "rows": len(records), "source": "smartcat/Amazon-2023-GenQ", "representative_subset": True}, output)
    report = {"status": "complete", "rows": len(records), "features": matrix.shape[1], "source": "smartcat/Amazon-2023-GenQ", "subset_policy": "1250 rows per Parquet shard, duplicate parent_asin/title removed", "resource": guard.as_dict()}
    (ROOT / "data/phase5_rag_index.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
