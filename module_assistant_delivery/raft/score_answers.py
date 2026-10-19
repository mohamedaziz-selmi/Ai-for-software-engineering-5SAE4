"""Scores generated answers with the runtime rules (service venv): the reply must be valid against the runtime JSON
schema, citations must pass the runtime check, and a grounded answer without a verified citation becomes "not found",
exactly as the app shows it.

Hand-written validation set (prompts.jsonl): correct =
  fact -> answered and every keyword group found in the answer; scope -> answered with the expected scope verdict;
  unanswerable / offtopic -> not answered. Harmful = an answered scope question with the OPPOSITE verdict, or an
  unanswerable question answered with a "verified" claim.
Generator test split (test.jsonl): correct = same answered/abstained decision and scope verdict as the target.

  .venv\\Scripts\\python.exe raft\\score_answers.py --prompts raft\\data\\handwritten_val\\prompts.jsonl base run2a run2b
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "backend"))

from app.assistant.verify import quote_in_text  # noqa: E402
from app.llm.schemas import AssistantAnswer  # noqa: E402

RESULTS = MODULE_ROOT / "raft" / "results"


def runtime_outcome(reply: str, chunks: dict[str, str]) -> tuple[str, AssistantAnswer | None, int]:
    text = reply.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        parsed = AssistantAnswer.model_validate(json.loads(text))
    except Exception:
        return "invalid_json", None, 0
    verified = [c for c in parsed.citations if c.chunk_id in chunks and quote_in_text(c.quote, chunks[c.chunk_id])]
    if parsed.grounded and verified and parsed.answer.strip():
        return "answered", parsed, len(verified)
    return ("not_found_after_verification" if parsed.grounded else "not_found"), parsed, len(verified)


CHUNK = re.compile(r'<chunk id="(C\d+)"[^>]*>\n(.*?)\n</chunk>', re.S)


def chunks_of(row: dict) -> dict[str, str]:
    if "chunks" in row:
        return row["chunks"]
    user = next(m["content"] for m in row["messages"] if m["role"] == "user")  # generator rows: parse the rendered context
    return dict(CHUNK.findall(user))


def score(prompts: list[dict], answers: dict[str, dict]) -> dict:
    by_type, total, harmful, invalid, seconds = defaultdict(Counter), Counter(), [], 0, []
    for row in prompts:
        a = answers.get(row["id"])
        if a is None:
            continue
        seconds.append(a["seconds"])
        status, parsed, _ = runtime_outcome(a["reply"], chunks_of(row))
        invalid += status == "invalid_json"
        answered = status == "answered"
        kind = row["type"]
        if "keywords" in row or "scope" in row or kind in ("unanswerable", "offtopic"):  # hand-written set
            if kind == "fact":
                ok = answered and all(any(k.casefold() in parsed.answer.casefold() for k in group) for group in row["keywords"])
            elif kind == "scope":
                ok = answered and parsed.scope_verdict == row["scope"]
                if answered and parsed.scope_verdict and parsed.scope_verdict != row["scope"]:
                    harmful.append(row["id"])
            else:
                ok = not answered
                if answered:
                    harmful.append(row["id"])
        else:  # generator test split: compare with the target decision
            target = json.loads(next(m["content"] for m in row["messages"] if m["role"] == "assistant"))
            ok = answered == target["grounded"] and (not answered or parsed.scope_verdict == target["scope_verdict"])
            kind = row["type"]
        by_type[kind]["correct"] += ok
        by_type[kind]["n"] += 1
        total["correct"] += ok
        total["n"] += 1
    return {"correct": total["correct"], "n": total["n"], "by_type": {k: f"{v['correct']}/{v['n']}" for k, v in sorted(by_type.items())},
            "harmful": harmful, "invalid_json": invalid, "mean_seconds": round(sum(seconds) / max(1, len(seconds)), 2)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default=str(MODULE_ROOT / "raft" / "data" / "handwritten_val" / "prompts.jsonl"))
    parser.add_argument("labels", nargs="+")
    args = parser.parse_args()
    prompts = [json.loads(l) for l in Path(args.prompts).read_text(encoding="utf-8").splitlines() if l.strip()]
    stem = Path(args.prompts).stem
    report = {}
    for label in args.labels:
        path = RESULTS / f"answers_{stem}_{label}.jsonl"
        answers = {r["id"]: r for r in (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip())}
        report[label] = score(prompts, answers)
    (RESULTS / f"scores_{stem}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
