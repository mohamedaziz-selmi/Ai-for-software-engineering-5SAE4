"""Ingest the synthetic demo documents listed in data/seed/projects.json.

Usage (cwd: module_assistant_delivery/backend):  ..\\.venv\\Scripts\\python.exe -m app.seed
Idempotent: unchanged documents are skipped; edited ones become a new version.
"""

from __future__ import annotations

import json
import uuid

from .config import load_settings
from .db import connect, init_db, utcnow
from .integrations.demo import DemoDirectory
from .rag.embeddings import LlamaIndexEmbedder
from .rag.ingest import ingest_document
from .rag.vector_store import ChromaChunkStore


def main() -> None:
    settings = load_settings()
    init_db(settings.database_path)
    directory = DemoDirectory(settings.seed_dir / "projects.json")
    embedder = LlamaIndexEmbedder(settings.embedding_model, settings.embedding_device, settings.hf_home)
    store = ChromaChunkStore(settings.chroma_path)
    with connect(settings.database_path) as conn:
        for project in directory.all_projects():
            for name in project.documents:
                path = settings.seed_dir / "documents" / name
                raw = path.read_bytes()
                text = raw.decode("utf-8")
                title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), name)
                result = ingest_document(
                    conn, embedder, store, project_id=project.id, title=title, doc_type="cahier_des_charges",
                    source_name=name, raw=raw, uploaded_by="seed", language="en",
                )
                state = "unchanged" if result["unchanged"] else f"v{result['version']}"
                print(f"{project.id}: {name} -> {result['chunks']} chunks ({state})")
        if not conn.execute("SELECT COUNT(*) FROM faq_entries").fetchone()[0]:
            faq = json.loads((settings.seed_dir / "projects.json").read_text(encoding="utf-8")).get("faq", [])
            with conn:
                conn.executemany("INSERT INTO faq_entries VALUES (?, ?, ?, ?, 'seed', ?, ?)",
                                 [(f"faq-{uuid.uuid4().hex[:10]}", e["question"], e["answer"], e["language"], utcnow(), utcnow()) for e in faq])
            print(f"FAQ: {len(faq)} entries")


if __name__ == "__main__":
    main()
