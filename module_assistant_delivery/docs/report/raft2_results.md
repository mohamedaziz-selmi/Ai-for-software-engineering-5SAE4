### Run 2 results (validation)

Hand-written validation set, 28 questions, scored with the app's rules (`raft/results/scores_prompts.json`).
Answers generated in the training environment (4-bit, Hugging Face).

| Model | Correct | Facts | Scope | Not in docs | Harmful | Time per answer |
|---|---|---|---|---|---|---|
| Base | 16/28 | 10/14 | 0/8 | 6/6 | 2 | 3.2 s |
| RAFT run 1 | 22/28 | 10/14 | 6/8 | 6/6 | 0 | 11.8 s |
| **RAFT run 2a** | **24/28** | 10/14 | **8/8** | 6/6 | 0 | 3.8 s |

Run 2a: 1,977 examples, 1 epoch, 2 h 43 min at half load, GPU peak 61 °C, 0 heat pauses (`raft/results/qwen2.5-7b-raft2a.json`).
The whole gain is on scope questions; facts did not move.

### Final test: RAG (base) vs RAFT in the real app

Same app, same retrieval and prompt; only the model changes. 33 questions, fallback off, served by Ollama
(`eval/results/assistant_final-base.md`, `assistant_final-raft2a.md`).

| Criterion | Why it matters | Base + RAG | RAFT 2a |
|---|---|---|---|
| Correct answer (24 answerable) | The facts the user needs | **23/24** | 19/24 |
| Cites the right section | The user can check the clause | **23/24** | 21/24 |
| Says "not in the documents" when true (9) | No invented answers | 9/9 | 9/9 |
| Scope verdict ("is X included?", 5) | The module's main use case | 4/5 | 4/5 |
| Harmful answers (confident and wrong) | Worse than no answer | **0** | 1 |
| Valid JSON first try (33) | No repair round-trip | 33/33 | 33/33 |
| Latency p50 / p95 | Feels instant or not | 2.1 / **4.8 s** | 2.1 / 7.2 s |
| GPU memory after warm-up | Fits the 8 GB laptop | **5,800 MiB** | 6,415 MiB |

What RAFT got wrong (from the records):
- **Harmful:** "Is exporting the daily order list as CSV part of the project?" → "out of scope". It is in scope
  (REQ-007, section 5). The training documents never had a separate functional-requirements list
  (`raft/data_gen_v2.py`, `HEADINGS`), so the model learned "in scope = listed under Scope".
- **Template leakage:** training phrases reused where they do not fit ("anything not listed is out of scope",
  "There are five mandatory requirements").
- **Language drift:** one French answer switched to Chinese mid-sentence.

**Insights**
- Validation gains did not transfer. RAFT won 24/28 to 16/28 in the training environment, then lost 19/24 to 23/24 in
  the app. Base's scope score depended on the path (0/8 there, 4/5 in the app), so the gain was partly measured
  against an artifact.
- Validate in the serving path. The deciding numbers are the ones from Ollama, with the real prompt and retrieval.
- More variety fixed run 1's errors but created new templates. The next step is coverage of document structures
  (functional-requirement lists), not more examples of the same ones.

### Decision and how to switch

**Base + RAG is the default.** RAFT stays installed as a choice and as the base model's first backup.

| | How |
|---|---|
| Choose in the UI | Model button in the composer: **Base + RAG** (default) or **RAFT fine-tuned**; remembered per browser |
| Choose in the API | `POST /api/ai/chat` with `"model": "base"` or `"raft"`; anything else is refused (422) |
| Make RAFT the default for everyone | Not needed for the demo; the UI choice is enough. To remove RAFT: `ASSISTANT_RAFT_MODEL=` in `.env` |
| Backup chain (backups on) | Chosen local model → the other local model → hosted gpt-oss-120b; each answer shows the route |
| Evaluations (backups off) | Chosen model only: a failure is a failure |
| One model at a time | `OLLAMA_MAX_LOADED_MODELS=1` (`scripts/start_ollama.ps1`): loading one unloads the other. After a RAFT answer, `/api/ps` listed only RAFT |
| Cost of a switch | First answer after a switch: 9.1 s and 11.6 s in our captures (model load); warm answers 2 to 3 s |
| Failure drill | Model menu → **Failure drill**: the chosen model is skipped as if it had crashed (`"simulate_failure": true`) |

![Failure drill: the base model is skipped and RAFT answers](images/after-failure-drill.png)

Why a drill and not Ctrl+C: both models run in the same private Ollama, so stopping it stops both, and the hosted
model answers instead. A real local crash takes the same code path as the drill; both are covered by tests
(`backend/tests/test_api.py`: `test_failure_drill_falls_back_to_the_other_local_model`,
`test_real_local_failure_falls_back_to_raft`, `test_no_backup_of_any_kind_when_backups_are_disabled`).
