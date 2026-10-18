"""Hosted API quality + quota check (Groq free tier candidate). Small on purpose: 4 calls, ~7K tokens.

Reads HOSTED_API_KEY from module_assistant_delivery/.env (never printed). Uses the app's own LLM layer
(PII masking, JSON schema, Pydantic validation, one repair retry, rate-limit handling):
  1-3. assistant backup format on held-out RAFT test examples (answerable, abstain, scope);
  4.   one review judgement (NN-1 on the synthetic M2 deliverable, planted capacity defect).
Writes eval/results/hosted_api_check.md with real latency, validity, token use and x-ratelimit headers.

Usage: .venv\\Scripts\\python.exe eval\\check_hosted_api.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone

from common import MODULE_ROOT, RESULTS, load_jsonl

from app.assistant.verify import quote_in_text
from app.config import load_settings
from app.llm.clients import ChatClient
from app.llm.prompts import Excerpt, render_review_messages
from app.llm.schemas import ASSISTANT_ANSWER_JSON_SCHEMA, REVIEW_JUDGEMENT_JSON_SCHEMA, AssistantAnswer, ReviewJudgement
from app.llm.service import AssistantUnavailable, LlmService
from app.review.pipeline import verify_finding

DELIVERABLE = MODULE_ROOT / "data" / "seed" / "deliverables" / "PRJ-DEMO-001_M2"


def main() -> int:
    settings = load_settings()
    if not settings.hosted_key_present:
        print("HOSTED_API_KEY is not set in module_assistant_delivery/.env. Add it there (never in chat), then rerun.")
        return 2
    extra = {"reasoning_effort": settings.hosted_reasoning_effort} if settings.hosted_reasoning_effort else {}
    events: list[dict] = []
    backup = ChatClient(name="backup", base_url=settings.hosted_base_url, model=settings.backup_model,
                        api_key=settings.hosted_api_key, timeout_s=settings.hosted_timeout_s, max_attempts=3, extra_body=extra)
    review = ChatClient(name="review", base_url=settings.hosted_base_url, model=settings.review_model,
                        api_key=settings.hosted_api_key, timeout_s=settings.review_timeout_s, max_attempts=6, extra_body=extra)
    llm = LlmService(local=backup, backup=None, backup_enabled=False, log_call=lambda **f: events.append(f),
                     review=review, review_served_by="hosted")

    rows = load_jsonl(MODULE_ROOT / "raft" / "data" / "generated" / "test.jsonl")
    picks = [next(r for r in rows if r["type"] == t) for t in ("fact", "abstain_absent", "scope")]
    results = []
    for row in picks:
        target = json.loads(row["messages"][2]["content"])
        started = time.perf_counter()
        try:
            out = llm._structured([("backup", backup)], row["messages"][:2], ASSISTANT_ANSWER_JSON_SCHEMA, AssistantAnswer,
                                  schema_name="assistant_answer", prompt_version="assistant_answer.v1", feature="hosted_check")
            pred: AssistantAnswer = out.parsed
            user = row["messages"][1]["content"]
            oracle_ok = None
            if target["grounded"]:
                gold = target["citations"][0]
                oracle_ok = any(c.chunk_id == gold["chunk_id"] and quote_in_text(c.quote, user) for c in pred.citations)
            results.append({"call": f"assistant/{row['type']}", "ok": True, "grounding_matches_label": pred.grounded == target["grounded"],
                            "oracle_cited_verified": oracle_ok, "scope": pred.scope_verdict, "expected_scope": target["scope_verdict"],
                            "latency_s": round(time.perf_counter() - started, 1)})
        except AssistantUnavailable as exc:
            results.append({"call": f"assistant/{row['type']}", "ok": False, "error": exc.attempts, "latency_s": round(time.perf_counter() - started, 1)})

    slots = (DELIVERABLE / "src" / "slots.py").read_text(encoding="utf-8")
    requirement = ("NN-1 (MUST): Pickup capacity: a shop accepts at most 20 orders per 15-minute pickup slot, "
                   "and booking for a slot closes 2 hours before the slot starts.")
    started = time.perf_counter()
    try:
        out = llm.review_json(render_review_messages(requirement, [Excerpt("src/slots.py", 1, slots)]), REVIEW_JUDGEMENT_JSON_SCHEMA,
                              ReviewJudgement, schema_name="review_judgement", prompt_version="review_judge.v1")
        judged: ReviewJudgement = out.parsed
        verified = [f for f in judged.findings if verify_finding({**f.model_dump(), "evidence_quote": out.masker.unmask(f.evidence_quote)},
                                                                 {"src/slots.py": slots}) is None]
        results.append({"call": "review/NN-1", "ok": True, "verdict": judged.verdict, "expected": "violates",
                        "findings": len(judged.findings), "verified_findings": len(verified), "latency_s": round(time.perf_counter() - started, 1)})
    except AssistantUnavailable as exc:
        results.append({"call": "review/NN-1", "ok": False, "error": exc.attempts, "latency_s": round(time.perf_counter() - started, 1)})

    tokens_in = sum(e.get("tokens_in") or 0 for e in events)
    tokens_out = sum(e.get("tokens_out") or 0 for e in events)
    statuses = [e["status"] for e in events]
    quota = review.last_rate_limit or backup.last_rate_limit
    lines = ["# Hosted API check", "", f"Ran {datetime.now(timezone.utc).isoformat(timespec='seconds')} against `{settings.hosted_base_url}`.",
             f"Models: backup `{settings.backup_model}`, review `{settings.review_model}`, reasoning_effort `{settings.hosted_reasoning_effort or 'default'}`.",
             f"Calls: {len(events)} (statuses {statuses}); tokens in/out: {tokens_in}/{tokens_out}.",
             f"Output format: strict JSON schema accepted = backup {backup._schema_mode}, review {review._schema_mode} "
             "(False means the client fell back to JSON mode).", "",
             "| Call | Result |", "|---|---|"] + [f"| {r['call']} | {json.dumps({k: v for k, v in r.items() if k != 'call'})} |" for r in results]
    lines += ["", "Rate-limit headers after the last call:", ""] + [f"- `{k}`: {v}" for k, v in sorted(quota.items())]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "hosted_api_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
