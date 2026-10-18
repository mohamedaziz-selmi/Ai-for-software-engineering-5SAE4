# Held-out RAFT test split: qwen3-4b-base

132 examples from projects never used in training; runtime prompt format; fixed context (oracle + distractors, or distractors only).

| Metric | Value |
|---|---|
| label | qwen3-4b-base |
| model | qwen3:4b-instruct-2507-q4_K_M |
| split | test |
| examples | 132 |
| json_valid | 132/132 |
| answered_when_supported | 96/99 |
| abstained_when_unsupported | 28/33 |
| cites_oracle_with_verified_quote | 93/99 |
| cites_a_distractor | 3/99 |
| scope_verdict_ok | 14/33 |
| numbers_in_answer_ok | 43/68 |
| latency_ms_p50 | 1105 |
| latency_ms_p95 | 1547 |
| ran_at | 2026-10-18T13:00:58+00:00 |
