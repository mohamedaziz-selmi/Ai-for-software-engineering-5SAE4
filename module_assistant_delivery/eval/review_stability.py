"""Review tuning summary (2026-10-19): accuracy and run-to-run stability of the live delivery reviews.

Reads the stored live runs (eval/results/review_live_<label>.json), scores them against their gold files and, for
each run, also RE-VERIFIES the findings the code had rejected using the CURRENT evidence verifier: the model outputs
are unchanged, only the code check is newer. No model is called. Writes eval/results/review_stability.md.

  .venv\\Scripts\\python.exe eval\\review_stability.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "backend"))

from app.review.pipeline import verify_finding  # noqa: E402

RESULTS = MODULE_ROOT / "eval" / "results"
GOLD_V1 = json.loads((MODULE_ROOT / "eval" / "datasets" / "review_demo_gold.json").read_text(encoding="utf-8"))
GOLD_V2 = json.loads((MODULE_ROOT / "eval" / "datasets" / "review_demo_v2_gold.json").read_text(encoding="utf-8"))
DELIVERABLES = {"v1": MODULE_ROOT / "demo" / "deliverables" / "M2_v1_with_defects", "v2": MODULE_ROOT / "demo" / "deliverables" / "M2_v2_fixed"}
# (label, deliverable, prompt, what changed)
RUNS = [
    ("demo-m2-v1-defects", "v1", "v1", "baseline prompt (2026-10-18)"),
    ("demo-m2-v2-fixed", "v2", "v1", "baseline prompt (2026-10-18)"),
    ("stab-v1-run1", "v1", "v2", "prompt v2 + seed 7"), ("stab-v1-run2", "v1", "v2", "prompt v2 + seed 7"),
    ("stab-v2-run1", "v2", "v2", "prompt v2 + seed 7"), ("stab-v2-run2", "v2", "v2", "prompt v2 + seed 7"),
    ("v3-v1-run1", "v1", "v3", "prompt v3 (rejected)"), ("v3-v1-run2", "v1", "v3", "prompt v3 (rejected)"),
    ("v3-v2-run1", "v2", "v3", "prompt v3 (rejected)"), ("v3-v2-run2", "v2", "v3", "prompt v3 (rejected)"),
]


def files_of(folder: Path) -> dict[str, str]:
    return {p.relative_to(folder).as_posix(): p.read_text(encoding="utf-8") for p in folder.rglob("*") if p.is_file()}


def verdicts(run: dict, files: dict[str, str], reverify: bool) -> dict[str, str]:
    out = {}
    for r in run["review"]["requirement_results"]:
        if r["status"] != "ok":
            out[r["code"]] = "review_failed"
            continue
        verdict = r["verdict"]
        if reverify and verdict == "cannot_determine" and r["model_verdict"] != "cannot_determine":
            rejected = json.loads(r["dropped"] or "[]")
            if any(verify_finding({**f, "line_start": f["line_start"], "line_end": f["line_end"]}, files) is None for f in rejected):
                verdict = r["model_verdict"]  # a finding now verifies -> the model's verdict stands
        out[r["code"]] = verdict
    return out


def main() -> None:
    lines = ["# Delivery review tuning: accuracy and stability (2026-10-19)", "",
             "Live runs of the hosted reviewer (`openai/gpt-oss-120b`, Groq free tier) on the two demo deliverables.",
             "*Original* = as stored by the app at the time. *Re-verified* = the same model outputs, with the rejected",
             "quotes checked again by the current evidence verifier (offline, no model call).", "",
             "| Run | Deliverable | Prompt / change | Original | Re-verified |", "|---|---|---|---|---|"]
    table: dict[str, dict[str, str]] = {}
    for label, deliv, prompt, change in RUNS:
        path = RESULTS / f"review_live_{label}.json"
        if not path.exists():
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        gold = (GOLD_V1 if deliv == "v1" else GOLD_V2)["gold"]
        files = files_of(DELIVERABLES[deliv])
        orig, rever = verdicts(run, files, False), verdicts(run, files, True)
        score = lambda v: sum(v.get(c) in ok for c, ok in gold.items())  # noqa: E731
        failed = sum(1 for x in orig.values() if x == "review_failed")
        lines.append(f"| {label} | {deliv} | {change} | {score(orig)}/13{f' ({failed} failed: rate limit)' if failed else ''} | {score(rever)}/13 |")
        table[label] = rever
    lines += ["", "## Re-verified verdict per requirement", "",
              "| Requirement | " + " | ".join(table) + " |", "|---|" + "---|" * len(table)]
    for code in GOLD_V1["gold"]:
        lines.append(f"| {code} | " + " | ".join(table[k].get(code, "?") for k in table) + " |")
    out = RESULTS / "review_stability.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:20]))


if __name__ == "__main__":
    main()
