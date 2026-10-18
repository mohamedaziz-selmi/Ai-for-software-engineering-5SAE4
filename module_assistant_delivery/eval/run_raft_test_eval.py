"""Fixed-context evaluation on the held-out RAFT test split (projects never used for training).

Each example already contains the runtime-format prompt (oracle + distractors, or distractors only).
The model is called through the same OpenAI-compatible endpoint with the same JSON schema as the app,
and scored against the label: answer vs abstain, citation of the oracle passage (verified quote),
citations of distractors, scope verdict, numbers in the answer, JSON validity, latency.

Usage: .venv\\Scripts\\python.exe eval\\run_raft_test_eval.py --model <ollama tag> --label <name> [--split test]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from common import MODULE_ROOT, RESULTS, load_jsonl, percentile
from pydantic import ValidationError

from app.assistant.verify import quote_in_text
from app.llm.clients import ChatClient, LlmError
from app.llm.schemas import ASSISTANT_ANSWER_JSON_SCHEMA, AssistantAnswer

CHUNK = re.compile(r'<chunk id="(C\d+)"[^>]*section="([^"]*)">\n(.*?)\n</chunk>', re.S)


def numbers(text: str) -> set[str]:
    return {n.replace(",", "").replace(" ", "") for n in re.findall(r"\d[\d, ]*\d|\d", text)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--split", default="test")
    parser.add_argument("--base-url", default="http://127.0.0.1:11435/v1")
    args = parser.parse_args()
    rows = load_jsonl(MODULE_ROOT / "raft" / "data" / "generated" / f"{args.split}.jsonl")
    client = ChatClient(name="eval", base_url=args.base_url, model=args.model, timeout_s=180)
    records = []
    for row in rows:
        messages, target = row["messages"][:2], json.loads(row["messages"][2]["content"])
        chunks = {m.group(1): f"{m.group(2)}\n{m.group(3)}" for m in CHUNK.finditer(messages[1]["content"])}
        gold_labels = {c["chunk_id"] for c in target["citations"]}
        started = time.perf_counter()
        rec = {"id": row["id"], "type": row["type"], "doc_lang": row["doc_lang"], "q_lang": row["q_lang"], "target_grounded": target["grounded"]}
        try:
            completion = client.complete_json(messages, ASSISTANT_ANSWER_JSON_SCHEMA, schema_name="assistant_answer")
            pred = AssistantAnswer.model_validate(json.loads(completion.content))
            rec["json_ok"] = True
        except (LlmError, ValueError, ValidationError) as exc:
            rec.update({"json_ok": False, "error": type(exc).__name__, "latency_ms": int((time.perf_counter() - started) * 1000)})
            records.append(rec)
            continue
        rec["latency_ms"] = int((time.perf_counter() - started) * 1000)
        verified = [c for c in pred.citations if c.chunk_id in chunks and quote_in_text(c.quote, chunks[c.chunk_id])]
        rec.update({
            "pred_grounded": pred.grounded,
            "grounding_ok": pred.grounded == target["grounded"],
            "cites_oracle_verified": any(c.chunk_id in gold_labels for c in verified) if target["grounded"] else None,
            "cites_distractor": any(c.chunk_id not in gold_labels for c in verified) if target["grounded"] else None,
            "unverified_citations": len(pred.citations) - len(verified),
            "scope_ok": (pred.scope_verdict == target["scope_verdict"]) if target.get("scope_verdict") else None,
            "numbers_ok": (numbers(target["answer"]) <= numbers(pred.answer)) if target["grounded"] and numbers(target["answer"]) else None,
            "answer": pred.answer[:300],
        })
        records.append(rec)

    def rate(key: str, subset=None) -> str:
        vals = [r[key] for r in (subset or records) if r.get(key) is not None]
        return f"{sum(vals)}/{len(vals)}" if vals else "n/a"

    answerable = [r for r in records if r["target_grounded"]]
    unsupported = [r for r in records if not r["target_grounded"]]
    lat = [r["latency_ms"] for r in records if r.get("latency_ms")]
    summary = {
        "label": args.label, "model": args.model, "split": args.split, "examples": len(records),
        "json_valid": rate("json_ok"),
        "answered_when_supported": rate("grounding_ok", answerable),
        "abstained_when_unsupported": rate("grounding_ok", unsupported),
        "cites_oracle_with_verified_quote": rate("cites_oracle_verified"),
        "cites_a_distractor": rate("cites_distractor"),
        "scope_verdict_ok": rate("scope_ok"),
        "numbers_in_answer_ok": rate("numbers_ok"),
        "latency_ms_p50": percentile(lat, 50), "latency_ms_p95": percentile(lat, 95),
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"raft_{args.split}_{args.label}.json").write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# Held-out RAFT {args.split} split: {args.label}", "",
             f"{len(records)} examples from projects never used in training; runtime prompt format; fixed context (oracle + distractors, or distractors only).", "",
             "| Metric | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in summary.items()]
    (RESULTS / f"raft_{args.split}_{args.label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
