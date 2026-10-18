"""Assistant evaluation: one model, the real pipeline (retrieval + prompt + verification), fallback OFF.

Usage (from module_assistant_delivery/):
  .venv\\Scripts\\python.exe eval\\run_assistant_eval.py --model qwen3:4b-instruct-2507-q4_K_M --label qwen3-4b

The same documents, retrieval settings and questions are used for every model, so runs are comparable.
Writes eval/results/assistant_<label>.json (per question) and .md (summary). Reports only what ran.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from datetime import datetime, timezone

from common import MODULE_ROOT, RESULTS, keyword_match, load_jsonl, percentile

from app.assistant.service import answer_question
from app.config import load_settings
from app.db import connect, init_db
from app.integrations.demo import DemoDirectory
from app.llm.clients import ChatClient
from app.llm.service import AssistantUnavailable, LlmService
from app.rag.embeddings import LlamaIndexEmbedder
from app.rag.ingest import ingest_document
from app.rag.vector_store import ChromaChunkStore

ABSTAIN_TYPES = {"unanswerable", "offtopic", "isolation"}


def gpu_memory_used_mib() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--dataset", default=str(MODULE_ROOT / "eval" / "datasets" / "assistant_dev.jsonl"))
    args = parser.parse_args()

    base = load_settings()
    work = MODULE_ROOT / "storage" / "eval" / base.embedding_model.replace("/", "__")
    settings = replace(base, database_path=work / "eval.sqlite3", chroma_path=work / "chroma", backup_enabled=False)
    init_db(settings.database_path)
    embedder = LlamaIndexEmbedder(settings.embedding_model, settings.embedding_device, settings.hf_home)
    store = ChromaChunkStore(settings.chroma_path)
    directory = DemoDirectory(settings.seed_dir / "projects.json")

    events: list[dict] = []
    local = ChatClient(name="local", base_url=settings.assistant_base_url, model=args.model, timeout_s=180)
    llm = LlmService(local=local, backup=None, backup_enabled=False, log_call=lambda **f: events.append(f))

    rows = load_jsonl(Path(args.dataset))
    records = []
    with connect(settings.database_path) as conn:
        for project in directory.all_projects():
            for name in project.documents:
                ingest_document(conn, embedder, store, project_id=project.id, title=name, doc_type="cahier_des_charges",
                                source_name=name, raw=(settings.seed_dir / "documents" / name).read_bytes(), uploaded_by="eval")

        # Warm-up call so model load time is not counted as answer latency.
        try:
            answer_question(conn, embedder, store, llm, project_id="PRJ-DEMO-001", user_id="eval", question="warm-up: what is the project?",
                            conversation_id=None, top_k=settings.top_k)
        except AssistantUnavailable as exc:
            raise SystemExit(f"Model not reachable: {exc.attempts}")
        events.clear()
        vram = gpu_memory_used_mib()

        for row in rows:
            start_event = len(events)
            started = time.perf_counter()
            try:
                result = answer_question(conn, embedder, store, llm, project_id=row["project_id"], user_id="eval",
                                         question=row["question"], conversation_id=None, top_k=settings.top_k)
                error = None
            except AssistantUnavailable as exc:
                result, error = None, exc.attempts
            wall_ms = int((time.perf_counter() - started) * 1000)
            calls = events[start_event:]
            record = {"id": row["id"], "type": row["type"], "lang": row["lang"], "question": row["question"],
                      "error": error, "wall_ms": wall_ms,
                      "json_first_try_ok": bool(calls) and calls[0]["status"] == "ok",
                      "llm_calls": [c["status"] for c in calls]}
            if result:
                sections = [r["section"] for r in result["retrieval"]]
                gold = row.get("gold_section")
                record.update({
                    "status": result["status"], "answer": result["answer"], "scope_verdict": result["scope_verdict"],
                    "citations": [{"label": c["label"], "section": c["section"], "quote": c["quote"]} for c in result["citations"]],
                    "dropped": result["dropped_citations"], "latency_ms": result["latency_ms"],
                    "retrieved_sections": sections,
                    "gold_retrieved": any(gold and gold in s for s in sections) if gold else None,
                    "cites_gold": any(gold and gold in c["section"] for c in result["citations"]) if gold else None,
                })
                if row["answerable"]:
                    record["correct"] = result["status"] == "answered" and keyword_match(result["answer"], row.get("keywords", []))
                    if row.get("expected_scope"):
                        record["scope_ok"] = result["scope_verdict"] in row["expected_scope"]
                else:
                    record["abstained"] = result["status"] != "answered"
            records.append(record)
            print(f"{row['id']}: {record.get('status', 'ERROR')} {record.get('correct', record.get('abstained', ''))} {wall_ms} ms", flush=True)

    answerable = [r for r in records if "correct" in r]
    abstain = [r for r in records if "abstained" in r]
    scope = [r for r in records if "scope_ok" in r]
    answered = [r for r in records if r.get("status") == "answered"]
    lat = [r["latency_ms"] for r in records if r.get("latency_ms")]
    summary = {
        "label": args.label, "model": args.model, "embedding_model": settings.embedding_model, "top_k": settings.top_k,
        "questions": len(records), "errors": sum(1 for r in records if r["error"]),
        "keyword_correct_answerable": f"{sum(r['correct'] for r in answerable)}/{len(answerable)}",
        "answered_with_gold_section_citation": f"{sum(bool(r.get('cites_gold')) for r in answerable)}/{len(answerable)}",
        "abstained_when_unsupported": f"{sum(r['abstained'] for r in abstain)}/{len(abstain)}",
        "scope_verdict_ok": f"{sum(r['scope_ok'] for r in scope)}/{len(scope)}",
        "json_valid_first_try": f"{sum(r['json_first_try_ok'] for r in records)}/{len(records)}",
        "answers_with_dropped_citations": f"{sum(1 for r in answered if r['dropped'])}/{len(answered)}",
        "withheld_after_verification": sum(1 for r in records if r.get("status") == "not_found_after_verification"),
        "latency_ms_p50": percentile(lat, 50), "latency_ms_p95": percentile(lat, 95),
        "gpu_memory_used_mib_after_warmup": vram,
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"assistant_{args.label}.json").write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# Assistant eval: {args.label}", "", "Real run of the full pipeline; hosted fallback disabled. "
             "`keyword_correct` is a crude proxy (all keyword groups present in an answered reply).", "",
             "| Metric | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in summary.items()]
    (RESULTS / f"assistant_{args.label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
