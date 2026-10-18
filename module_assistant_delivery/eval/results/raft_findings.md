# RAFT run 1: findings (2026-10-18)

## What was trained
- Checkpoint: `Qwen/Qwen2.5-7B-Instruct` (Unsloth 4-bit `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`), LoRA r=16/alpha 16 on
  q,k,v,o,gate,up,down; 2 epochs; batch 1 × grad. accumulation 8; lr 2e-4; max length 2,048 (no example dropped).
- Data: 1,056 synthetic FR/EN examples from 32 generated projects (`raft/data_gen.py`, seed 7); validation 132 (4 projects);
  test 132 (4 other projects). Labels correct by construction; same prompt and JSON schema as the app.
- RTX 4060 Laptop 8 GB: 264 optimizer steps in 80 min, peak 5.6 GB reserved. Validation loss 0.0025 → 0.0007 (best = epoch 2).
  A loss this low mainly shows the templates were learned: validation projects come from the same generator.

## How it was served and compared
Ollama 0.40.6 rejects LoRA adapters and cannot quantize a Qwen2 import, so both models were built through the
same offline path (`raft/export_gguf.ps1`): NF4 → bf16 (+ LoRA for RAFT) → bf16 GGUF → Q5_0 GGUF → Ollama.
`assistant-base-requant:qwen2.5-7b` and `assistant-raft:qwen2.5-7b` therefore differ only by the adapter.
Fallback disabled in all runs. Full tables: `base_vs_raft.md`.

## Results

| | Held-out RAFT test (132, generator-shaped, unseen projects) | | Hand-written dev doc (33, full pipeline) | |
|---|---|---|---|---|
| Metric | Base (matched) | RAFT | Base (matched) | RAFT |
| Abstained when unsupported | 23/33 | **33/33** | 9/9 | 9/9 |
| Cited a distractor | 4/99 | **0/99** | | |
| Oracle cited with verified quote | 96/99 | 98/99 | 20/24 (gold section) | 21/24 |
| Scope verdict correct | 22/33 | **32/33** | 4/5 | 3/5 |
| Numbers / keywords correct | 43/68 | **68/68** | 23/24 | 20/24 |
| Withheld after verification | | | 1 | 2 |
| Latency p50 / p95 | 2.0 / 4.2 s | 1.9 / 2.9 s | 2.3 / 6.0 s | 1.9 / 7.0 s |

The official Ollama build of the base (`qwen2.5:7b-instruct`, Q4_K_M from the original bf16) scored on the held-out
split: abstention 31/33, oracle citation 98/99, scope 28/33 (`raft_test_qwen2.5-7b-base.md`). The requantization
path alone lowers the base's abstention (31 → 23), so RAFT must be compared with the matched base.

## Per-question analysis of the dev-set differences
- **Q03** (booking closes): base withheld, RAFT correct. Gain.
- **Q08** (milestone M2): RAFT paraphrased the Markdown table ("M2 Due: End of week 7; Deliverables: …"), so the quote failed
  verification and the answer was withheld. Training documents never contained tables.
- **S01** (card payment): RAFT gave the right verdict, but with the "not listed → change request" template, although the
  document explicitly excludes card payment. The reasoning is copied from the template.
- **S03** (CSV export): RAFT cited the wrong chunk label and was withheld. The base's answer was also wrong in substance:
  it called an in-scope SHOULD requirement out of scope, and only the crude keyword proxy counted it correct.
- **F03** (French, home delivery): **RAFT answered "Oui, c'est inclus"**. It reused the in-scope answer template while
  quoting the out-of-scope list. The quote is real, so citation verification passed, but the conclusion is wrong.
  This harmful failure shows that a verified quote does not prove a supported claim.

## Conclusion
RAFT run 1 achieved its trained behaviours on data shaped like its training set: abstaining without evidence and
ignoring distractors. It **overfitted the generator's templates** (answer phrasings, document structure) and did not
transfer to a differently written document, where it introduced one wrong scope verdict. **The app keeps serving the
base model** (`ASSISTANT_MODEL=qwen2.5:7b-instruct`). Switching requires a run that does not regress the
hand-written dev set.

## Next iteration (proposed, not done)
1. More diverse data: several document styles (tables, numbered articles, prose contracts, mixed FR/EN), varied section
   names, and answers phrased in several ways. Optionally, answers paraphrased by the hosted model and still validated in code.
2. Counter-template examples: explicit out-of-scope items asked as "is it included?", so "listed" is never mistaken for "included".
3. 1 epoch (validation loss was already 0.0025 after epoch 1), lower learning rate (1e-4), early stopping on a
   **held-out hand-written** set rather than generator-shaped validation.
4. Add an LLM-judge faithfulness check (hosted model, small sample) so a "verified quote, wrong conclusion" case such as F03 is counted.

## Storage note (2026-10-18)
To keep the module folder small (owner's decision), the evaluated Ollama models (`assistant-raft:qwen2.5-7b`,
`assistant-base-requant:qwen2.5-7b`), the 4-bit training weights, `.venv-raft` and the epoch checkpoints were
deleted after this evaluation. The trained adapter, the dataset, all scripts and every result file above are
kept. `raft/export_gguf.ps1` rebuilds both models from the adapter.
