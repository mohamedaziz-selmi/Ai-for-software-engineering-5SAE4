from pathlib import Path

from app.rag.chunking import Page, approx_tokens, chunk_code, chunk_pages
from app.rag.ingest import passage_path

SEED = Path(__file__).resolve().parents[2] / "data" / "seed" / "documents" / "PRJ-DEMO-001_cahier_des_charges.md"


def test_markdown_sections_keep_heading_path_and_lines():
    text = "# Spec\n\n## 3. Scope\n\n### 3.2 Out of scope\n\n- Online card payment.\n- Native apps.\n\n## 4. Rules\n\nRule one.\n"
    chunks = chunk_pages([Page(text)], markdown=True)
    by_path = {c.heading_path: c for c in chunks}
    out = by_path["Spec > 3. Scope > 3.2 Out of scope"]
    assert "Online card payment" in out.text
    assert (out.line_start, out.line_end) == (7, 8)
    assert by_path["Spec > 4. Rules"].text == "Rule one."


def test_seed_document_chunks_respect_token_budget():
    chunks = chunk_pages([Page(SEED.read_text(encoding="utf-8"))], markdown=True, max_tokens=120)
    assert len(chunks) > 8
    assert all(approx_tokens(c.text) <= 120 for c in chunks)
    assert any(c.heading_path.endswith("4. Non-negotiable requirements") and "NN-1" in c.text for c in chunks)


def test_long_paragraph_is_split_without_losing_words():
    words = [f"w{i}" for i in range(500)]
    chunks = chunk_pages([Page(" ".join(words) + ".")], markdown=True, max_tokens=100)
    assert len(chunks) > 1
    rebuilt = " ".join(c.text for c in chunks).replace(".", "").split()
    assert rebuilt == words


def test_numbered_clause_headings_in_extracted_text_and_pages():
    pages = [Page("1. Context\nThe bakery has three shops.\n3.2 Out of scope\nHome delivery.", 1), Page("Native apps are excluded.", 2)]
    chunks = chunk_pages(pages, markdown=False)
    assert chunks[0].heading_path == "1. Context" and chunks[0].page == 1
    assert chunks[1].heading_path == "1. Context > 3.2 Out of scope"
    assert chunks[-1].page == 2 and chunks[-1].heading_path.endswith("3.2 Out of scope")


def test_passages_without_a_title_heading_carry_the_document_title():
    assert passage_path("CR-01.docx", "docx", "(untitled)") == "CR-01.docx"
    assert passage_path("CR-01.docx", "docx", "3. Estimate") == "CR-01.docx > 3. Estimate"
    assert passage_path("notes.txt", "text", "(untitled)") == "notes.txt"
    # Markdown (path starts with its H1) and code (path is the file name) are unchanged, as in every evaluation.
    assert passage_path("spec.md", "markdown", "Spec > 4. Rules") == "Spec > 4. Rules"
    assert passage_path("app.py", "code", "src/app.py") == "src/app.py"


def test_code_windows_have_line_provenance():
    code = "\n".join(f"line {i}" for i in range(1, 171))
    chunks = chunk_code(code, "src/app.py")
    assert [(c.line_start, c.line_end) for c in chunks] == [(1, 80), (71, 150), (141, 170)]
    assert chunks[0].heading_path == "src/app.py"
