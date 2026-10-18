# Held-out RAFT test split: qwen2.5-7b-base

132 examples from projects never used in training; runtime prompt format; fixed context (oracle + distractors, or distractors only).

| Metric | Value |
|---|---|
| label | qwen2.5-7b-base |
| model | qwen2.5:7b-instruct |
| split | test |
| examples | 132 |
| json_valid | 132/132 |
| answered_when_supported | 99/99 |
| abstained_when_unsupported | 31/33 |
| cites_oracle_with_verified_quote | 98/99 |
| cites_a_distractor | 2/99 |
| scope_verdict_ok | 28/33 |
| numbers_in_answer_ok | 41/68 |
| latency_ms_p50 | 1679 |
| latency_ms_p95 | 2564 |
| ran_at | 2026-10-18T13:04:54+00:00 |
