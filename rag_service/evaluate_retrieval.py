"""Evaluate the semantic-only Chroma retrieval baseline and create a Word report.

The expected references come from the supplied synthetic retrieval test set. A
result is relevant when its PDF matches an expected PDF, or when its detected
source/entity ids match an expected document id.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from docx import Document
from docx.shared import Inches, Pt

SERVICE_DIR = Path(__file__).resolve().parent
TEST_SET = SERVICE_DIR.parent / "rag" / "cerebro_rag_full_30" / "synthetic_dataset" / "retrieval_test_questions.csv"
REPORT_DIR = SERVICE_DIR / "evaluation_reports"
API_URL = "http://127.0.0.1:8000/search"
TOP_K = 10


def split_values(value: str) -> set[str]:
    return {item.strip() for item in value.split(";") if item.strip()}


def search(question: str, mode: str) -> list[dict]:
    payload = json.dumps({"query": question, "limit": TOP_K, "mode": mode}).encode()
    request = Request(API_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read())["results"]
    except URLError as error:
        raise RuntimeError("The local RAG API is not running on port 8000.") from error


def is_relevant(result: dict, expected_pdfs: set[str], expected_ids: set[str]) -> bool:
    source = result["source"]
    actual_ids = {item.strip() for item in source.get("source_ids", "").split(",") if item.strip()}
    return source.get("pdf_file") in expected_pdfs or bool(actual_ids & expected_ids)


def unique_relevances(results: list[dict], expected_pdfs: set[str], expected_ids: set[str]) -> list[int]:
    """Binary relevance, counting each expected evidence source only once.

    Many PDF pages can be relevant to one expected PDF; counting every such
    chunk as an independent ideal result would inflate nDCG above 1.0.
    """
    seen: set[str] = set()
    values: list[int] = []
    for result in results:
        source = result["source"]
        pdf = source.get("pdf_file")
        actual_ids = {item.strip() for item in source.get("source_ids", "").split(",") if item.strip()}
        label = f"pdf:{pdf}" if pdf in expected_pdfs else next((f"id:{item}" for item in sorted(actual_ids & expected_ids)), None)
        values.append(int(label is not None and label not in seen))
        if label is not None:
            seen.add(label)
    return values


def dcg(relevances: list[int]) -> float:
    return sum(relevance / math.log2(index + 2) for index, relevance in enumerate(relevances))


def evaluate(mode: str = "hybrid") -> tuple[list[dict], dict]:
    rows: list[dict] = []
    with TEST_SET.open(encoding="utf-8", newline="") as source:
        for test in csv.DictReader(source):
            expected_pdfs = split_values(test["expected_pdf_files"])
            expected_ids = split_values(test["expected_relevant_document_ids"])
            results = search(test["question"], mode)
            relevant = [is_relevant(result, expected_pdfs, expected_ids) for result in results]
            first_rank = next((index + 1 for index, value in enumerate(relevant) if value), None)
            rows.append({
                "id": test["question_id"],
                "question": test["question"],
                "expected_pdfs": expected_pdfs,
                "relevant": relevant,
				"ndcg_relevant": unique_relevances(results, expected_pdfs, expected_ids),
				"relevance_target_count": len(expected_pdfs | expected_ids),
                "first_rank": first_rank,
                "results": results,
            })

    metrics = {}
    for k in (1, 3, 5, 10):
        recall = sum(any(row["relevant"][:k]) for row in rows) / len(rows)
        precision = sum(sum(row["ndcg_relevant"][:k]) / k for row in rows) / len(rows)
        mrr = sum(1 / row["first_rank"] if row["first_rank"] and row["first_rank"] <= k else 0 for row in rows) / len(rows)
        ndcg = sum(
            dcg(row["ndcg_relevant"][:k]) / dcg([1] * min(k, row["relevance_target_count"]))
            for row in rows
        ) / len(rows)
        metrics[k] = {"accuracy": recall, "precision": precision, "recall": recall, "mrr": mrr, "ndcg": ndcg}
    return rows, metrics


def add_cell_text(cell, text: str, bold: bool = False) -> None:
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = Pt(8)


def create_report(rows: list[dict], metrics: dict, retrieval_name: str) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"{retrieval_name}_retrieval_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)

    document.add_heading(f"Cerebro RAG — {retrieval_name.replace('_', ' ').title()} Evaluation", 0)
    document.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    document.add_paragraph("Scope: 752 chunks from 30 PDFs using the active local retriever. Metrics evaluate evidence retrieval only, not LLM answer correctness.")

    document.add_heading("Method", level=1)
    document.add_paragraph("The supplied retrieval_test_questions.csv was queried against the local semantic-search API. A result was counted relevant when its source PDF matched an expected PDF or when its detected source/entity IDs overlapped with the expected document IDs. Metrics therefore measure retrieval evidence, not LLM answer correctness.")

    document.add_heading("Aggregate results", level=1)
    table = document.add_table(rows=1, cols=4)
    table.style = "Light Shading Accent 1"
    for cell, label in zip(table.rows[0].cells, ["K", "Recall@K", "MRR@K", "nDCG@K"]):
        add_cell_text(cell, label, True)
    for k, values in metrics.items():
        cells = table.add_row().cells
        for cell, value in zip(cells, [str(k), *(f"{values[key]:.1%}" for key in ("recall", "mrr", "ndcg"))]):
            add_cell_text(cell, value)

    top_one = metrics[1]["recall"]
    document.add_paragraph(f"Top-1 evidence accuracy (Recall@1): {top_one:.1%}.")

    document.add_heading("Per-question retrieval results", level=1)
    details = document.add_table(rows=1, cols=5)
    details.style = "Table Grid"
    for cell, label in zip(details.rows[0].cells, ["ID", "Question", "First relevant rank", "Expected PDF(s)", "Top retrieved PDF(s)"]):
        add_cell_text(cell, label, True)
    for row in rows:
        cells = details.add_row().cells
        retrieved = "; ".join(result["source"]["pdf_file"] for result in row["results"][:3])
        values = [row["id"], row["question"], str(row["first_rank"] or "Not in top 10"), "; ".join(sorted(row["expected_pdfs"])), retrieved]
        for cell, value in zip(cells, values):
            add_cell_text(cell, value)

    document.add_heading("Next decision", level=1)
    document.add_paragraph("Compare this run with the saved semantic-only baseline using the same test set and relevance rule. Inspect failed and low-rank questions before tuning RRF or adding further retrieval techniques.")
    document.save(report_path)
    return report_path


if __name__ == "__main__":
    retrieval_rows, retrieval_metrics = evaluate()
    output = create_report(retrieval_rows, retrieval_metrics, "hybrid_rrf")
    print(f"Evaluated {len(retrieval_rows)} questions")
    for k, values in retrieval_metrics.items():
        print(f"K={k}: Recall={values['recall']:.3f}, MRR={values['mrr']:.3f}, nDCG={values['ndcg']:.3f}")
    print(f"Word report: {output}")
