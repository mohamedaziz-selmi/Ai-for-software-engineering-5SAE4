# Assistant eval: qwen2.5-7b-raft

Real run of the full pipeline; hosted fallback disabled. `keyword_correct` is a crude proxy (all keyword groups present in an answered reply).

| Metric | Value |
|---|---|
| label | qwen2.5-7b-raft |
| model | assistant-raft:qwen2.5-7b |
| embedding_model | intfloat/multilingual-e5-base |
| top_k | 5 |
| questions | 33 |
| errors | 0 |
| keyword_correct_answerable | 20/24 |
| answered_with_gold_section_citation | 21/24 |
| abstained_when_unsupported | 9/9 |
| scope_verdict_ok | 3/5 |
| json_valid_first_try | 33/33 |
| answers_with_dropped_citations | 1/22 |
| withheld_after_verification | 2 |
| latency_ms_p50 | 1897 |
| latency_ms_p95 | 6952 |
| gpu_memory_used_mib_after_warmup | 6313 |
| ran_at | 2026-10-18T15:14:22+00:00 |
