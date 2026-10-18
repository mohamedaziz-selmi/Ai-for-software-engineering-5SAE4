# Model selection: measured evidence (2026-10-18)

Candidates (shortlist and exclusions in `docs/MODULE_SPEC.md` §6.1): `Qwen/Qwen2.5-7B-Instruct` (served as
Ollama `qwen2.5:7b-instruct`, Q4_K_M) and `Qwen/Qwen3-4B-Instruct-2507` (Ollama `qwen3:4b-instruct-2507-q4_K_M`).
Same retrieval (e5-base, top-5), same documents, same prompts (`assistant_answer.v1`, `review_judge.v1`),
hosted fallback disabled, RTX 4060 Laptop 8 GB. Small test sets: one- or two-item differences are not significant.

## 1. Assistant, dev set (33 questions: EN/FR facts, scope, unanswerable, off-topic, cross-project)

Final verifier (table pipes and list bullets treated as formatting). Details: `assistant_qwen3-4b-base.md`, `assistant_qwen2.5-7b-base.md`.

| Metric | Qwen3-4B-Instruct-2507 | Qwen2.5-7B-Instruct |
|---|---|---|
| Correct with a verified gold-section citation (keyword proxy) | 24/24 | 23/24 |
| Withheld after citation verification | 0 | 1 |
| Abstained on unsupported questions | 9/9 | 9/9 |
| Scope verdict field correct | 2/5 | 4/5 |
| JSON valid on first try | 33/33 | 33/33 |
| Latency p50 / p95 | 1.2 s / 3.3 s | 1.9 s / 4.2 s |

## 2. Delivery review, live (13 requirements, 2 planted defects, prompt injection in README)

Details: `review_live_qwen3-4b-base.md`, `review_live_qwen2.5-7b-base.md`.

| Metric | Qwen3-4B-Instruct-2507 | Qwen2.5-7B-Instruct |
|---|---|---|
| Final verdicts matching gold | 9/13 | 13/13 |
| Planted defects found with verified evidence | 2/2 | 2/2 |
| False "violates" claims | 2 (absence-based reasoning, forbidden by the prompt) | 0 |
| Requirements failed (invalid JSON twice) | 1 | 0 |
| Wall time | 109 s | 82 s |

## 3. Retrieval (embedding model, independent of the LLM)

`intfloat/multilingual-e5-base`: hit@1 0.75, hit@3 1.00, hit@5 1.00, MRR 0.868 on the dev set (`retrieval_comparison.md`).

## 4. Training feasibility (Unsloth 4-bit QLoRA, max sequence 2048, batch 1, gradient checkpointing)

See `raft/results/*-smoke.json`. Filled in from real runs only.

| Metric | Qwen3-4B-Instruct-2507 | Qwen2.5-7B-Instruct |
|---|---|---|
| Smoke run (4 optimizer steps = 32 examples, LoRA r=16, grad. accumulation 8) | completed | completed |
| Peak VRAM reserved / allocated | 4,006 / 3,495 MiB (of 8,187) | 5,582 / 5,206 MiB (of 8,187) |
| Longest RAFT example / dropped at 2,048 | 1,303 tokens / 0 | 1,299 tokens / 0 |
| Time for 32 examples | 122.9 s (incl. first-ever kernel compilation) | 74.2 s (compiled kernels cached) |
| Loss after 4 steps (train / val) | 2.26 / 1.76 | 0.73 / 0.52 |

Losses are not comparable across the two models (different tokenizers and chat templates); they only show
that training ran. Sources: `raft/results/qwen3-4b-smoke.json`, `raft/results/qwen2.5-7b-smoke.json`.

## 5. Held-out RAFT test split, base models (132 examples, 4 projects never used for training)

Fixed context in the runtime prompt format. Sources: `raft_test_qwen3-4b-base.md`, `raft_test_qwen2.5-7b-base.md`.

| Metric | Qwen3-4B base | Qwen2.5-7B base |
|---|---|---|
| JSON valid | 132/132 | 132/132 |
| Answered when supported | 96/99 | 99/99 |
| Abstained when unsupported | 28/33 | 31/33 |
| Cited the oracle passage with a verified quote | 93/99 | 98/99 |
| Cited a distractor | 3/99 | 2/99 |
| Scope verdict correct | 14/33 | 28/33 |
| Numbers from the gold answer present | 43/68 | 41/68 |
| Latency p50 | 1.1 s | 1.7 s |

## Decision (D10): Qwen/Qwen2.5-7B-Instruct

Both candidates can be QLoRA-trained locally at the needed sequence length (no example dropped). The 7B
is clearly better where it matters for this module: delivery review (13/13 vs 9/13 verdicts, no false
"violates"), held-out abstention, oracle citation and scope verdicts. The two are roughly tied on the
small assistant dev set. The 4B's advantages are speed (~35 % lower latency) and memory. The RAFT
model is therefore trained on the same Qwen2.5-7B-Instruct checkpoint that is served as the base. This
confirms, by measurement, the model named in the owner's ChatGPT-written prompt.


**Update after the owner restored hosted review (D5):** the local model now answers questions only, and
reviews use the hosted model. The review comparison (§2) is kept as a record but no longer drives the
choice. The decision still holds on the assistant-only evidence: on the held-out RAFT test split the
7B base is better on abstention (31/33 vs 28/33), oracle citation (98/99 vs 93/99) and scope (28/33 vs 14/33).
