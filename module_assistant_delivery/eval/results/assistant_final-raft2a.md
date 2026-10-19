# Assistant eval: final-raft2a

Real run of the full pipeline; hosted fallback disabled. `keyword_correct` is a crude proxy (all keyword groups present in an answered reply).

| Metric | Value |
|---|---|
| label | final-raft2a |
| model | assistant-raft2a:qwen2.5-7b |
| embedding_model | intfloat/multilingual-e5-base |
| top_k | 5 |
| questions | 33 |
| errors | 0 |
| keyword_correct_answerable | 19/24 |
| answered_with_gold_section_citation | 21/24 |
| abstained_when_unsupported | 9/9 |
| scope_verdict_ok | 4/5 |
| json_valid_first_try | 33/33 |
| answers_with_dropped_citations | 0/23 |
| withheld_after_verification | 1 |
| latency_ms_p50 | 2073 |
| latency_ms_p95 | 7240 |
| gpu_memory_used_mib_after_warmup | 6415 |
| ran_at | 2026-10-19T06:22:47+00:00 |
