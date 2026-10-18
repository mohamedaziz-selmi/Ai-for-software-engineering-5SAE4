# Held-out RAFT test split: qwen2.5-7b-base-requant

132 examples from projects never used in training; runtime prompt format; fixed context (oracle + distractors, or distractors only).

| Metric | Value |
|---|---|
| label | qwen2.5-7b-base-requant |
| model | assistant-base-requant:qwen2.5-7b |
| split | test |
| examples | 132 |
| json_valid | 132/132 |
| answered_when_supported | 98/99 |
| abstained_when_unsupported | 23/33 |
| cites_oracle_with_verified_quote | 96/99 |
| cites_a_distractor | 4/99 |
| scope_verdict_ok | 22/33 |
| numbers_in_answer_ok | 43/68 |
| latency_ms_p50 | 1971 |
| latency_ms_p95 | 4204 |
| ran_at | 2026-10-18T15:06:12+00:00 |
