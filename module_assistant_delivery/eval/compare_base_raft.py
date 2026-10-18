"""Write eval/results/base_vs_raft.md from existing result files (no model calls, no invented numbers).

Usage: .venv\\Scripts\\python.exe eval\\compare_base_raft.py --base qwen2.5-7b-base --raft qwen2.5-7b-raft
"""

from __future__ import annotations

import argparse
import json

from common import RESULTS


def load(name: str) -> dict:
    path = RESULTS / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))["summary"] if path.exists() else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--raft", required=True)
    args = parser.parse_args()
    sections = [
        ("Held-out RAFT test split (132 examples, projects never used for training, fixed context)", "raft_test_",
         ["json_valid", "answered_when_supported", "abstained_when_unsupported", "cites_oracle_with_verified_quote",
          "cites_a_distractor", "scope_verdict_ok", "numbers_in_answer_ok", "latency_ms_p50", "latency_ms_p95"]),
        ("Assistant dev set (33 questions on the seed project, full pipeline: retrieval + verification)", "assistant_",
         ["keyword_correct_answerable", "answered_with_gold_section_citation", "abstained_when_unsupported", "scope_verdict_ok",
          "json_valid_first_try", "withheld_after_verification", "errors", "latency_ms_p50", "latency_ms_p95"]),
    ]
    lines = ["# Base vs RAFT (same checkpoint, same retrieval, documents, questions and prompts; fallback off)", "",
             f"Base: `{args.base}`. RAFT: `{args.raft}` (base + LoRA adapter trained on the RAFT train split).",
             "Small test sets: report differences with that caveat.", ""]
    for title, prefix, keys in sections:
        base, raft = load(prefix + args.base), load(prefix + args.raft)
        lines += [f"## {title}", "", "| Metric | Base | RAFT |", "|---|---|---|"]
        lines += [f"| {k} | {base.get(k, 'missing')} | {raft.get(k, 'missing')} |" for k in keys]
        lines += [f"| model | `{base.get('model', 'missing')}` | `{raft.get('model', 'missing')}` |", ""]
    (RESULTS / "base_vs_raft.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
