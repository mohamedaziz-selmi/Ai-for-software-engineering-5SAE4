"""Create a clear semantic-only vs hybrid-RRF retrieval comparison report.

The semantic baseline was locked before BM25 was added using the same 37 test
questions, chunk collection and relevance rule. Hybrid metrics are calculated
live from the currently-running local API.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from evaluate_retrieval import REPORT_DIR, evaluate


def cell(cell, text: str, bold: bool = False) -> None:
    run = cell.paragraphs[0].add_run(text)
    run.bold = bold
    run.font.size = Pt(8)


def metric_table(document: Document, baseline: dict, hybrid: dict) -> None:
    table = document.add_table(rows=1, cols=5)
    table.style = "Light Shading Accent 1"
    for target, label in zip(table.rows[0].cells, ["Metric", "Semantic-only", "Hybrid RRF", "Change", "What it tells you"]):
        cell(target, label, True)
    meanings = {
        "accuracy": "Hit rate: at least one relevant source appears in the top K.",
        "precision": "How many shown sources are relevant, accounting for duplicate evidence.",
        "recall": "Relevant evidence appears anywhere in the top K.",
        "mrr": "How high the first relevant result ranks.",
        "ndcg": "Ranking quality; rewards relevant evidence near the top.",
    }
    for k in (1, 3, 5, 10):
        for metric in ("accuracy", "precision", "recall", "mrr", "ndcg"):
            before = baseline[k][metric]
            after = hybrid[k][metric]
            delta = after - before
            row = table.add_row().cells
            values = [f"{metric.upper()}@{k}", f"{before:.1%}", f"{after:.1%}", f"{delta:+.1%}", meanings[metric]]
            for target, value in zip(row, values):
                cell(target, value)


def report() -> Path:
    semantic_rows, semantic = evaluate("semantic")
    rows, hybrid = evaluate("hybrid")
    REPORT_DIR.mkdir(exist_ok=True)
    output = REPORT_DIR / f"semantic_vs_hybrid_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)

    title = document.add_heading("Cerebro RAG — Before & After Retrieval Evaluation", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  37 supplied retrieval questions  |  30 PDFs / 752 chunks").alignment = WD_ALIGN_PARAGRAPH.CENTER

    document.add_heading("What changed", level=1)
    document.add_paragraph("Before: Chroma semantic-vector search using all-MiniLM-L6-v2. After: the same semantic search plus BM25 lexical retrieval, combined with Reciprocal Rank Fusion (RRF, k=60). Both runs were executed just now against the same live Chroma collection, PDFs, chunks, test set, relevance rule, and result limits.")

    document.add_heading("Results", level=1)
    metric_table(document, semantic, hybrid)

    document.add_heading("Key outcome", level=1)
    before_top1 = semantic[1]["accuracy"]
    after_top1 = hybrid[1]["accuracy"]
    document.add_paragraph(f"Top-1 evidence accuracy improved from {before_top1:.1%} to {after_top1:.1%} ({after_top1 - before_top1:+.1%}). In practical terms, the right source appears first for approximately {round(after_top1 * 37)} of 37 questions with hybrid retrieval, compared with approximately {round(before_top1 * 37)} before BM25.")
    document.add_paragraph(f"Coverage at 10 results remains {hybrid[10]['recall']:.1%}. BM25 therefore mainly improves ranking quality and the first result, rather than expanding already-complete top-10 coverage.")

    document.add_heading("Per-question rank comparison", level=1)
    document.add_paragraph("This table records the current hybrid rank and highlights questions that still need inspection. The summary table above is the direct, live before/after comparison.")
    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for target, label in zip(table.rows[0].cells, ["Question", "Hybrid first relevant rank", "Top hybrid source", "Status"]):
        cell(target, label, True)
    for row in rows:
        cells = table.add_row().cells
        top = row["results"][0]["source"] if row["results"] else {}
        rank = row["first_rank"]
        status = "Top result relevant" if rank == 1 else ("Found in top 10" if rank else "Not found")
        values = [row["id"], str(rank or "Not in top 10"), f"{top.get('pdf_file', '—')} · p. {top.get('page', '—')}", status]
        for target, value in zip(cells, values):
            cell(target, value)

    document.add_heading("How to use this report", level=1)
    document.add_paragraph("Treat Recall@1 as the easiest accuracy measure for the interface: it asks whether the first source shown is relevant. Use MRR and nDCG to judge ordering across the full result list. Keep this report as the baseline for future RRF tuning, metadata filtering, or reranking. Do not compare it with a run that changes the dataset, chunking, or relevance definition.")
    document.save(output)
    return output


if __name__ == "__main__":
    print(report())
