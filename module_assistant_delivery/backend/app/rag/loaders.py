"""Turn uploaded files into text pages + chunks. PDF and DOCX use LlamaIndex's local file readers.

Only text-based files are supported (spec 4): scanned PDFs yield no text and are rejected.
"""

from __future__ import annotations

import tempfile
from pathlib import Path, PurePath

from .chunking import Chunk, Page, TokenCounter, approx_tokens, chunk_code, chunk_pages

MARKDOWN = {".md", ".markdown"}
PLAIN = {".txt"}
CODE = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".cs", ".go", ".rb", ".php", ".c", ".h", ".cpp",
        ".hpp", ".rs", ".swift", ".sql", ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".xml", ".sh", ".ps1"}
BINARY_DOCS = {".pdf", ".docx"}
SUPPORTED = MARKDOWN | PLAIN | CODE | BINARY_DOCS


class UnsupportedDocument(ValueError):
    pass


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnsupportedDocument("The file is not UTF-8 text.") from exc


def _read_with_llamaindex(suffix: str, raw: bytes) -> list[Page]:
    # LlamaIndex readers take a path, so the upload goes to a private temp file that is deleted after.
    with tempfile.TemporaryDirectory(prefix="assistant-upload-") as tmp:
        path = Path(tmp) / f"upload{suffix}"
        path.write_bytes(raw)
        if suffix == ".pdf":
            from llama_index.readers.file import PDFReader

            docs = PDFReader(return_full_document=False).load_data(file=path)
            pages = []
            for i, doc in enumerate(docs, start=1):
                label = str(doc.metadata.get("page_label", i))
                pages.append(Page(doc.text, int(label) if label.isdigit() else i))
            return pages
        from llama_index.readers.file import DocxReader

        return [Page("\n".join(d.text for d in DocxReader().load_data(file=path)))]


def load_chunks(filename: str, raw: bytes, *, count: TokenCounter = approx_tokens) -> tuple[str, list[Chunk]]:
    """Return (kind, chunks) for an uploaded file. kind is markdown|text|pdf|docx|code."""
    suffix = PurePath(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise UnsupportedDocument(f"Unsupported file type '{suffix or filename}'.")
    if suffix in CODE:
        return "code", chunk_code(_decode(raw), PurePath(filename).name)
    if suffix in MARKDOWN | PLAIN:
        kind = "markdown" if suffix in MARKDOWN else "text"
        return kind, chunk_pages([Page(_decode(raw))], markdown=kind == "markdown", count=count)
    pages = _read_with_llamaindex(suffix, raw)
    if not any(p.text.strip() for p in pages):
        raise UnsupportedDocument("No extractable text (scanned or image-only documents are not supported).")
    return suffix[1:], chunk_pages(pages, markdown=False, count=count)
