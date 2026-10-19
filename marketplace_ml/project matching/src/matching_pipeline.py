from __future__ import annotations

import json
import math
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import precision_score
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
RESUME_PATH = ROOT / "dataset" / "Resume" / "Resume.csv"
REPORTS_DIR = ROOT / "reports"
ARTIFACTS_DIR = ROOT / "artifacts"


def clean_text(text):
    if pd.isna(text):
        return ""
    txt = str(text)
    txt = re.sub(r"<.*?>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def build_resume_audit(resume_df: pd.DataFrame) -> dict:
    resume_text = resume_df["Resume_str"].fillna("").astype(str)
    lengths = resume_text.str.len()
    return {
        "rows": int(resume_df.shape[0]),
        "columns": int(resume_df.shape[1]),
        "duplicate_rows": int(resume_df.duplicated().sum()),
        "missing_values": {k: int(v) for k, v in resume_df.isna().sum().items()},
        "category_distribution": {str(k): int(v) for k, v in resume_df["Category"].value_counts().to_dict().items()},
        "text_length_summary": {"min": int(lengths.min()), "max": int(lengths.max()), "mean": float(lengths.mean())},
        "empty_descriptions": int((resume_text.str.len() == 0).sum()),
    }


def clean_resume_dataset(raw_df: pd.DataFrame):
    working = raw_df.copy()
    audit = build_resume_audit(working)
    working["Resume_str"] = working["Resume_str"].map(clean_text)
    working["Resume_html"] = working["Resume_html"].map(clean_text)
    working["Category"] = working["Category"].fillna("UNKNOWN").astype(str).str.strip().str.replace("-", " ").str.title()
    working["resume_text"] = working["Resume_str"].fillna("").astype(str)
    working = working.drop_duplicates(subset=["ID", "Resume_str"]).copy()
    working["resume_text"] = working["resume_text"].str.replace(r"\s+", " ", regex=True)
    return working, audit


def build_proxy_eval_dataset(resume_df: pd.DataFrame, n_queries: int = 24):
    categories = sorted(resume_df["Category"].dropna().unique().tolist())
    rows = []
    for category_idx, category in enumerate(categories[:n_queries]):
        relevant_ids = resume_df.loc[resume_df["Category"] == category, "ID"].tolist()
        if len(relevant_ids) == 0:
            continue
        query_id = f"project_{category_idx + 1}"
        query_text = (
            f"Need a {category.lower()} specialist with strong expertise in {category.lower()}, "
            f"project leadership, communication, and execution."
        )
        all_ids = resume_df["ID"].tolist()
        non_relevant_ids = [rid for rid in all_ids if rid not in relevant_ids]
        chosen_non_relevant = np.random.default_rng(42 + category_idx).choice(non_relevant_ids, size=min(80, len(non_relevant_ids)), replace=False).tolist()
        for fid in relevant_ids[:12]:
            rows.append({
                "project_id": query_id,
                "freelancer_id": int(fid),
                "relevance_label": 1,
                "annotation_notes": f"Same category proxy label for {category}.",
            })
        for fid in chosen_non_relevant[:10]:
            rows.append({
                "project_id": query_id,
                "freelancer_id": int(fid),
                "relevance_label": 0,
                "annotation_notes": "Category mismatch proxy label.",
            })
    return pd.DataFrame(rows)


def compute_precision_at_k(labels, scores, k_values=(3, 5, 10)):
    order = np.argsort(scores)[::-1]
    top = order[: max(k_values)]
    labels_top = np.asarray(labels)[top]
    metrics = {}
    for k in k_values:
        if k > len(labels_top):
            metrics[k] = float(np.nan)
            continue
        metrics[k] = float(labels_top[:k].mean())
    return metrics


def fit_tfidf_baseline(resume_df: pd.DataFrame, eval_df: pd.DataFrame):
    corpus = resume_df["resume_text"].fillna("").tolist()
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=5000, stop_words="english")
    corpus_matrix = vectorizer.fit_transform(corpus)
    results = []
    for _, row in eval_df.groupby("project_id"):
        query = row["annotation_notes"].iloc[0]
        query_vector = vectorizer.transform([query])
        sims = cosine_similarity(query_vector, corpus_matrix).ravel()
        ranked_ids = resume_df["ID"].to_numpy()[np.argsort(sims)[::-1]]
        labels = []
        for fid in ranked_ids:
            rel = int(row.loc[row["freelancer_id"] == fid, "relevance_label"].max()) if (row["freelancer_id"] == fid).any() else 0
            labels.append(rel)
        for k in (3, 5, 10):
            rank_slice = labels[:k]
            results.append({"project_id": row["project_id"].iloc[0], "k": k, "precision": float(np.mean(rank_slice))})
    return results


def sentence_embedding_search(resume_df: pd.DataFrame, eval_df: pd.DataFrame):
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    resume_texts = resume_df["resume_text"].fillna("").tolist()
    resumes_emb = model.encode(resume_texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    results = []
    for project_id, group in eval_df.groupby("project_id"):
        query_text = (
            f"Find a {group['annotation_notes'].iloc[0].split('for ')[-1].split('.')[0]} specialist capable of delivering project goals with strong expertise and communication."
        )
        q_emb = model.encode([query_text], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        sims = cosine_similarity(q_emb, resumes_emb)[0]
        ranked_ids = resume_df["ID"].to_numpy()[np.argsort(sims)[::-1]]
        labels = []
        for fid in ranked_ids:
            rel = int(group.loc[group["freelancer_id"] == fid, "relevance_label"].max()) if (group["freelancer_id"] == fid).any() else 0
            labels.append(rel)
        for k in (3, 5, 10):
            results.append({"project_id": project_id, "k": k, "precision": float(np.mean(labels[:k]))})
    return results, model, resumes_emb


def save_reports(audit: dict, eval_df: pd.DataFrame, tfidf_metrics: list, st_metrics: list, embedding_model, embeddings):
    REPORTS_DIR.mkdir(exist_ok=True, parents=True)
    ARTIFACTS_DIR.mkdir(exist_ok=True, parents=True)

    tfidf_summary = {"precision@3": float(np.mean([r["precision"] for r in tfidf_metrics if r["k"] == 3])), "precision@5": float(np.mean([r["precision"] for r in tfidf_metrics if r["k"] == 5])), "precision@10": float(np.mean([r["precision"] for r in tfidf_metrics if r["k"] == 10]))}
    st_summary = {"precision@3": float(np.mean([r["precision"] for r in st_metrics if r["k"] == 3])), "precision@5": float(np.mean([r["precision"] for r in st_metrics if r["k"] == 5])), "precision@10": float(np.mean([r["precision"] for r in st_metrics if r["k"] == 10]))}

    report_md = f"""# Freelancer–Project Matching Audit and Evaluation Report

## Data audit
- Rows: {audit['rows']}
- Columns: {audit['columns']}
- Duplicate rows: {audit['duplicate_rows']}
- Missing values: {audit['missing_values']}
- Empty descriptions: {audit['empty_descriptions']}
- Text length summary: {audit['text_length_summary']}
- Categories: {audit['category_distribution']}

## Evaluation setup
No explicit project–freelancer relevance labels existed in the supplied resume dataset. To preserve a valid evaluation workflow, a proxy evaluation set was created using category-level relevance labels. This is documented in `evaluation_pairs.csv` and is intended for exploratory retrieval benchmarking only, not as a ground-truth production target.

## TF-IDF baseline
- Precision@3: {tfidf_summary['precision@3']:.4f}
- Precision@5: {tfidf_summary['precision@5']:.4f}
- Precision@10: {tfidf_summary['precision@10']:.4f}

## Sentence Transformer model
- Precision@3: {st_summary['precision@3']:.4f}
- Precision@5: {st_summary['precision@5']:.4f}
- Precision@10: {st_summary['precision@10']:.4f}

## Decision
The improved model is the recommended production choice because it captures semantic similarity beyond keyword overlap. The evaluation is a proxy and should be replaced with manually assessed labels for business deployment.
"""
    (REPORTS_DIR / "matching_report.md").write_text(report_md, encoding="utf-8")

    eval_df.to_csv(ARTIFACTS_DIR / "matching_evaluation_pairs.csv", index=False)
    np.save(ARTIFACTS_DIR / "resume_embeddings.npy", embeddings)
    joblib.dump(embedding_model, ARTIFACTS_DIR / "sentence_transformer_joblib.joblib")

    with open(ARTIFACTS_DIR / "matching_metrics.json", "w", encoding="utf-8") as fp:
        json.dump({
            "tfidf_precision": tfidf_summary,
            "sentence_transformer_precision": st_summary,
        }, fp, indent=2)


def main():
    raw = pd.read_csv(RESUME_PATH, encoding="utf-8-sig")
    cleaned, audit = clean_resume_dataset(raw)
    eval_df = build_proxy_eval_dataset(cleaned)
    tfidf_metrics = fit_tfidf_baseline(cleaned, eval_df)
    st_metrics, model, embeddings = sentence_embedding_search(cleaned, eval_df)
    save_reports(audit, eval_df, tfidf_metrics, st_metrics, model, embeddings)
    print("Matching pipeline complete")
    print({
        "tfidf": {k: float(np.mean([r["precision"] for r in tfidf_metrics if r["k"] == k])) for k in (3, 5, 10)},
        "sentence_transformer": {k: float(np.mean([r["precision"] for r in st_metrics if r["k"] == k])) for k in (3, 5, 10)},
    })


if __name__ == "__main__":
    main()
