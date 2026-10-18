"""Build the semantic-only Chroma collection from rag/pdfs.

Run this after installing requirements:
    python ingest.py --reset
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass

import chromadb
from chromadb.errors import NotFoundError
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pypdf import PdfReader

from config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    PDF_SOURCE_DIRS,
)

ENTITY_PATTERN = re.compile(r"\b(?:JOB|PRP|FRE|PORT|REQ|AC|EVA|PRJ)-\d{3}(?:-[A-Z0-9]+)?\b")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    metadata: dict[str, str | int]


def category_for(pdf_name: str) -> str:
    if pdf_name.startswith("CR-"):
        return "client_requirements"
    if pdf_name.startswith("FP-"):
        return "freelancer_proposals"
    if pdf_name.startswith("EK-"):
        return "evaluation_knowledge_base"
    return "other"


def normalize(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def split_text(text: str) -> list[str]:
    """Split near paragraph/sentence boundaries with a deterministic overlap."""
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind("; ", start, end), text.rfind(" ", start, end))
            if boundary > start + CHUNK_SIZE // 2:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def extract_chunks(pdf_path) -> list[Chunk]:
    reader = PdfReader(str(pdf_path))
    category = category_for(pdf_path.name)
    chunks: list[Chunk] = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = normalize(page.extract_text() or "")
        if not page_text:
            continue
        source_ids = sorted(set(ENTITY_PATTERN.findall(page_text)))
        for chunk_number, body in enumerate(split_text(page_text), start=1):
            digest = hashlib.sha1(f"{pdf_path.name}:{page_number}:{chunk_number}:{body}".encode()).hexdigest()[:16]
            chunks.append(
                Chunk(
                    id=f"{pdf_path.stem}-p{page_number}-c{chunk_number}-{digest}",
                    text=body,
                    metadata={
                        "pdf_file": pdf_path.name,
                        "pdf_id": pdf_path.stem.split("_", 1)[0],
                        "category": category,
                        "page": page_number,
                        # Chroma metadata values must be scalar. This supports
                        # display and later structured metadata improvements.
                        "source_ids": ", ".join(source_ids),
                    },
                )
            )
    return chunks


def get_collection(reset: bool):
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except (ValueError, NotFoundError):
            pass
    print(f"Loading embedding model: {EMBEDDING_MODEL}", flush=True)
    embedding_function = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"embedding_model": EMBEDDING_MODEL, "retrieval": "semantic_only"},
    )


def ingest(reset: bool) -> int:
    # rag/pdfs currently holds a useful flat subset. The full set lives in the
    # three category directories. Filename de-duplication keeps identical PDFs
    # from being embedded twice if they appear in both locations.
    pdf_by_name = {
        pdf_path.name: pdf_path
        for source_dir in PDF_SOURCE_DIRS
        if source_dir.is_dir()
        for pdf_path in source_dir.glob("*.pdf")
    }
    pdf_files = [pdf_by_name[name] for name in sorted(pdf_by_name)]
    if not pdf_files:
        raise FileNotFoundError("No PDFs found in the configured Cerebro PDF source directories.")

    collection = get_collection(reset)
    print(f"Extracting text from {len(pdf_files)} PDFs", flush=True)
    all_chunks = [chunk for pdf_path in pdf_files for chunk in extract_chunks(pdf_path)]
    print(f"Embedding {len(all_chunks)} chunks", flush=True)
    for offset in range(0, len(all_chunks), 100):
        batch = all_chunks[offset : offset + 100]
        collection.upsert(
            ids=[chunk.id for chunk in batch],
            documents=[chunk.text for chunk in batch],
            metadatas=[chunk.metadata for chunk in batch],
        )
    print(f"Indexed {len(all_chunks)} chunks from {len(pdf_files)} PDFs into {CHROMA_DIR}")
    return len(all_chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index Cerebro PDFs into Chroma.")
    parser.add_argument("--reset", action="store_true", help="Replace the existing collection.")
    args = parser.parse_args()
    ingest(reset=args.reset)
