# Hosted API (Groq free tier): measured on 2026-10-18 with the owner's key

Model `openai/gpt-oss-120b`, `reasoning_effort=low`, strict JSON schema accepted (no JSON-mode downgrade).
Only synthetic data was sent; PII/secret masking was applied to every call.

| Check | Result | Source |
|---|---|---|
| Quality/quota check (3 held-out assistant examples + 1 review call) | 4/4 correct; oracle citations verified; abstention and scope correct; 0.6-1.1 s per call; 4,055 tokens in / 652 out | `hosted_api_check.md` |
| Assistant fallback (local model down during training) | Answered with a verified citation, `served_by: backup`, 3.5 s; unanswerable question → "not in the project documents" | live API through the gateway |
| Live delivery review, run 1 | 12/13 verdicts, 2/2 planted defects; the miss was a correct `conforms` whose elided evidence the verifier could not yet check | `review_live_groq-gpt-oss-120b-run1.md` |
| Live delivery review, run 2 (line-by-line check of numbered evidence) | **13/13 verdicts, 2/2 planted defects, 0 dropped findings**, 121 s, 13 calls, 22,334 tokens in / 3,909 out | `review_live_groq-gpt-oss-120b.md` |

Quota seen in the response headers: 1,000 requests/day and 8,000 tokens/minute for this model on this
account. One review of this 13-requirement deliverable costs about 26K tokens and ~2 minutes because of
the per-minute limit. Groq's published daily token limit for this model (about 200K/day at the time of the
kickoff check) is not in the headers; if it applies, it allows roughly 7 such reviews per day.

For comparison, the same review on local models (before hosted review was restored):
Qwen2.5-7B 13/13, Qwen3-4B 9/13 (`model_selection.md`). Small test: one deliverable, 13 requirements.
