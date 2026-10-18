# Held-out RAFT test split: qwen2.5-7b-raft

132 examples from projects never used in training; runtime prompt format; fixed context (oracle + distractors, or distractors only).

| Metric | Value |
|---|---|
| label | qwen2.5-7b-raft |
| model | assistant-raft:qwen2.5-7b |
| split | test |
| examples | 132 |
| json_valid | 132/132 |
| answered_when_supported | 98/99 |
| abstained_when_unsupported | 33/33 |
| cites_oracle_with_verified_quote | 98/99 |
| cites_a_distractor | 0/99 |
| scope_verdict_ok | 32/33 |
| numbers_in_answer_ok | 68/68 |
| latency_ms_p50 | 1873 |
| latency_ms_p95 | 2854 |
| ran_at | 2026-10-18T15:12:37+00:00 |
