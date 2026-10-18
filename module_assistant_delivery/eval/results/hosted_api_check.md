# Hosted API check

Ran 2026-10-18T13:30:17+00:00 against `https://api.groq.com/openai/v1`.
Models: backup `openai/gpt-oss-120b`, review `openai/gpt-oss-120b`, reasoning_effort `low`.
Calls: 4 (statuses ['ok', 'ok', 'ok', 'ok']); tokens in/out: 4055/681.
Output format: strict JSON schema accepted = backup True, review True (False means the client fell back to JSON mode).

| Call | Result |
|---|---|
| assistant/fact | {"ok": true, "grounding_matches_label": true, "oracle_cited_verified": true, "scope": null, "expected_scope": null, "latency_s": 0.9} |
| assistant/abstain_absent | {"ok": true, "grounding_matches_label": true, "oracle_cited_verified": null, "scope": null, "expected_scope": null, "latency_s": 0.6} |
| assistant/scope | {"ok": true, "grounding_matches_label": true, "oracle_cited_verified": true, "scope": "in_scope", "expected_scope": "in_scope", "latency_s": 0.6} |
| review/NN-1 | {"ok": true, "verdict": "violates", "expected": "violates", "findings": 2, "verified_findings": 2, "latency_s": 1.3} |

Rate-limit headers after the last call:

- `x-ratelimit-limit-requests`: 1000
- `x-ratelimit-limit-tokens`: 8000
- `x-ratelimit-remaining-requests`: 992
- `x-ratelimit-remaining-tokens`: 1828
- `x-ratelimit-reset-requests`: 11m31.2s
- `x-ratelimit-reset-tokens`: 46.29s
