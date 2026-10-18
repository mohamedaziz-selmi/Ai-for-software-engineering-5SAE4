# Assistant eval: qwen3-4b-base

Real run of the full pipeline; hosted fallback disabled. `keyword_correct` is a crude proxy (all keyword groups present in an answered reply).

| Metric | Value |
|---|---|
| label | qwen3-4b-base |
| model | qwen3:4b-instruct-2507-q4_K_M |
| embedding_model | intfloat/multilingual-e5-base |
| top_k | 5 |
| questions | 33 |
| errors | 0 |
| keyword_correct_answerable | 24/24 |
| answered_with_gold_section_citation | 24/24 |
| abstained_when_unsupported | 9/9 |
| scope_verdict_ok | 2/5 |
| json_valid_first_try | 33/33 |
| answers_with_dropped_citations | 0/24 |
| withheld_after_verification | 0 |
| latency_ms_p50 | 1183 |
| latency_ms_p95 | 3304 |
| gpu_memory_used_mib_after_warmup | 4388 |
| ran_at | 2026-10-18T12:47:28+00:00 |
