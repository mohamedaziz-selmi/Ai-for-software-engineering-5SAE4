"""Live delivery-review check through the HTTP API (backend on :8003, real local model).

Submits the synthetic M2 deliverable, runs a review, waits, and scores verdicts and planted-defect
detection against eval/datasets/review_demo_gold.json. Writes eval/results/review_live_<label>.md/json.

Usage: .venv\\Scripts\\python.exe eval\\run_review_live.py --label qwen2.5-7b-base [--base http://127.0.0.1:8003]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx

MODULE_ROOT = Path(__file__).resolve().parents[1]
DELIVERABLE = MODULE_ROOT / "data" / "seed" / "deliverables" / "PRJ-DEMO-001_M2"
GOLD = json.loads((MODULE_ROOT / "eval" / "datasets" / "review_demo_gold.json").read_text(encoding="utf-8"))
RESULTS = MODULE_ROOT / "eval" / "results"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--base", default="http://127.0.0.1:8003")
    args = parser.parse_args()
    api = httpx.Client(base_url=f"{args.base}/api/ai", timeout=60)
    freelancer, client = {"X-Demo-User": "demo-freelancer-a"}, {"X-Demo-User": "demo-client-b"}
    health = api.get("/health").json()

    files = [("files", (str(p.relative_to(DELIVERABLE)).replace("\\", "/"), p.read_bytes(), "text/plain"))
             for p in sorted(DELIVERABLE.rglob("*")) if p.is_file()]
    submitted = api.post("/deliverables", headers=freelancer, data={"project_id": GOLD["project_id"], "milestone_id": GOLD["milestone_id"]}, files=files)
    submitted.raise_for_status()
    api.post("/requirements/extract", headers=freelancer, params={"project_id": GOLD["project_id"]}).raise_for_status()
    started = time.perf_counter()
    review_id = api.post(f"/deliverables/{submitted.json()['deliverable_id']}/review", headers=client).json()["review_id"]
    while True:
        review = api.get(f"/reviews/{review_id}", headers=client).json()
        if review["status"] in {"done", "failed"}:
            break
        time.sleep(3)
    wall_s = round(time.perf_counter() - started, 1)

    results = {r["code"]: r for r in review["requirement_results"]}
    rows, correct = [], 0
    for code, acceptable in GOLD["gold"].items():
        r = results.get(code, {})
        verdict = r.get("verdict") if r.get("status") == "ok" else "review_failed"
        ok = verdict in acceptable
        correct += ok
        rows.append((code, "/".join(acceptable), r.get("model_verdict"), verdict, ok, r.get("note") or ""))
    detected = {}
    for code, spec in GOLD["must_find"].items():
        detected[code] = any(f["requirement_code"] == code and f["file_path"] == spec["file"] and any(s in f["evidence_quote"] for s in spec["any_of"])
                             and f["severity"] in {"blocker", "major"} for f in review["findings"])
    summary = {"label": args.label, "model": review.get("model"), "served_by": review.get("served_by"), "status": review["status"],
               "verdict_accuracy": f"{correct}/{len(GOLD['gold'])}", "planted_defects_detected": f"{sum(detected.values())}/{len(detected)}",
               "detected": detected, "findings": len(review["findings"]), "summary": review["summary"], "wall_s": wall_s,
               "assistant_model_at_health": health["assistant"]["model"]}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"review_live_{args.label}.json").write_text(json.dumps({"summary": summary, "review": review}, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Live review check: {args.label}", "", "Synthetic M2 deliverable with planted defects (see `eval/datasets/review_demo_gold.json`). "
             f"Real run through the HTTP API; review served by `{summary['served_by']}` model `{summary['model']}`. "
             "Verdicts are after code-side evidence verification.", "",
             f"- Verdict accuracy: **{summary['verdict_accuracy']}**", f"- Planted defects detected with verified evidence (blocker/major): **{summary['planted_defects_detected']}**",
             f"- Findings kept: {summary['findings']}; dropped unverified: {review['summary'].get('dropped_unverified_findings') if review['summary'] else None}",
             f"- Wall time: {wall_s} s for {len(GOLD['gold'])} requirements; model `{summary['model']}`", "",
             "| Requirement | Gold | Model said | Final verdict | OK | Note |", "|---|---|---|---|---|---|"]
    lines += [f"| {c} | {g} | {m} | {v} | {'yes' if ok else 'no'} | {n} |" for c, g, m, v, ok, n in rows]
    lines += ["", "## Findings", ""] + [f"- **{f['severity']}** {f['requirement_code']} `{f['file_path']}:{f['line_start']}-{f['line_end']}`: {f['explanation']}  \n  evidence: `{f['evidence_quote'][:140]}`" for f in review["findings"]]
    (RESULTS / f"review_live_{args.label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
