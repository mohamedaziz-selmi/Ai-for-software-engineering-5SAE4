# Base vs RAFT (same checkpoint, same retrieval, documents, questions and prompts; fallback off)

Base: `qwen2.5-7b-base-requant`. RAFT: `qwen2.5-7b-raft` (base + LoRA adapter trained on the RAFT train split).
Small test sets: report differences with that caveat.

## Held-out RAFT test split (132 examples, projects never used for training, fixed context)

| Metric | Base | RAFT |
|---|---|---|
| json_valid | 132/132 | 132/132 |
| answered_when_supported | 98/99 | 98/99 |
| abstained_when_unsupported | 23/33 | 33/33 |
| cites_oracle_with_verified_quote | 96/99 | 98/99 |
| cites_a_distractor | 4/99 | 0/99 |
| scope_verdict_ok | 22/33 | 32/33 |
| numbers_in_answer_ok | 43/68 | 68/68 |
| latency_ms_p50 | 1971 | 1873 |
| latency_ms_p95 | 4204 | 2854 |
| model | `assistant-base-requant:qwen2.5-7b` | `assistant-raft:qwen2.5-7b` |

## Assistant dev set (33 questions on the seed project, full pipeline: retrieval + verification)

| Metric | Base | RAFT |
|---|---|---|
| keyword_correct_answerable | 23/24 | 20/24 |
| answered_with_gold_section_citation | 20/24 | 21/24 |
| abstained_when_unsupported | 9/9 | 9/9 |
| scope_verdict_ok | 4/5 | 3/5 |
| json_valid_first_try | 33/33 | 33/33 |
| withheld_after_verification | 1 | 2 |
| errors | 0 | 0 |
| latency_ms_p50 | 2330 | 1897 |
| latency_ms_p95 | 6029 | 6952 |
| model | `assistant-base-requant:qwen2.5-7b` | `assistant-raft:qwen2.5-7b` |
