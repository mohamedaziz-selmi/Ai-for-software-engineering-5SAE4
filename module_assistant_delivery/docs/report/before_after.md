Each change, the metric it was meant to move, and what happened. Changes that made things worse were rejected.

| # | Change (prompt) | Metric | Before | After | Kept? |
|---|---|---|---|---|---|
| 1 | Pick the model by measurement (A.1) | Review verdicts · scope verdicts | Qwen3-4B 9/13 · 2/5 | Qwen2.5-7B 13/13 · 4/5 | ✅ |
| 2 | RAFT run 1 (A.2) | Held-out "not found" · hand-written dev | Base 23/33 · 23/24 | 33/33 · 20/24, 1 harmful | ❌ overfit |
| 3 | Review prompt v2, temperature 0, seed (A.3) | Defective deliverable over 2 runs · false "partial" | 13/13 (1 run) · present | 12/13 + 12/13, identical · gone | ✅ |
| 4 | Evidence check accepts skipped lines (A.4) | Same model output | 11/13 | 12/13 | ✅ |
| 5 | Review prompt v3 (A.5) | Verdicts flipping between runs | 1 | 2 | ❌ worse |
| 6 | Reviews wait out the per-minute limit | Requirements lost to rate limits in a run | up to 3 | waits ≤ 2 min instead of failing (not yet re-measured: daily quota reached) | ✅ |
| 7 | Warm-up at start-up | First answer after start | 114 s | 3.0 s (model in memory 30 s after start) | ✅ |
| 8 | Review progress bar | What the user sees for 2–3 min | "N requirement(s) judged so far…" | "Requirement N of 13" + bar | ✅ |
| 9 | Gentle GPU mode, 79 °C cap | GPU load · peak temperature | ~100% · not limited | ~half · 61 °C over 2 h 43 min, 0 heat pauses | ✅ |
| 10 | Training data v2 + 1 epoch (A.6–A.8) | Hand-written set: correct · scope · harmful | Run 1: 22/28 · 6/8 · 0 | Run 2a: 24/28 · 8/8 · 0 | ✅ as RAFT candidate |
| 11 | Switch decision on the 33-question test (A.9) | Real app, fallback off: correct · harmful | Base 23/24 · 0 | RAFT 2a 19/24 · 1 | ❌ base stays default |
| 12 | RAFT as a choice and a backup | Ways to reach RAFT from the app | none | model picker + backup chain; drill: RAFT answered in 9.1 s | ✅ |
| 13 | Module UI redesign (module only) | Model choice, route and evidence visible | hidden in a meta line | picker in the composer, route under each answer, highlighted quotes, light + dark | ✅ |
| 14 | Unfinished flows closed | Things a role could not do | support: status only; FAQ: no edit; no new conversation; no document removal; no requirement edit; no delivery decision | reply threads, edit, new conversation, remove (previous version restored), edit kept on re-extraction, accept or request changes | ✅ |
| 15 | Fonts and motion | Look and feedback while the model works | system fonts, mono caps tags, a static skeleton | reading serif + grotesk, sentence-case tags, thinking spark with real elapsed time, transitions | ✅ |
| 16 | Control center (my microservice) | Seeing and stopping what uses the PC | one terminal per service | one button on every page: live map, readings, a switch per module | ✅ |
| 17 | Suggested questions per role | Suggestions that fit the user's role | the same 5 for everyone | 6 per role; all 12 asked live: 10 cited answers, 2 correct "not in the documents" | ✅ |
| 18 | Passages name their document (found by testing every file type) | DOCX question "How much does CR-01 cost, and is it approved?" | wrong: answered from a specification clause | 1,500 TND, approved, cited from the DOCX | ✅ |
| 19 | Refusals documented in Swagger | Refusal kinds described in the API docs | none ("Undocumented") | 401, 403, 404, 413, 415, 503 on every route that returns them, plus a summary per operation | ✅ |

![RAFT candidates on the hand-written validation set](images/raft_validation.svg)

![Final test in the real app: base vs RAFT 2a](images/rag_vs_raft_final.svg)

| Before (template style) | After (module's own design) |
|---|---|
| ![Old assistant page](images/before-assistant-answer.png) | ![New assistant page](images/after-assistant-answer.png) |
| ![Old review report](images/before-review-report.png) | ![New review report](images/after-review-report.png) |

**Takeaways**
- The biggest single gain came from measuring before choosing (row 1), not from fine-tuning.
- Validation gains did not transfer (rows 10 and 11): RAFT 2a won in the training environment and lost in the app. Measure in the serving path.
- A prompt change can lower stability even when it reads better (row 5): every prompt was tested twice before keeping it.
- A code check fixed what prompting could not (row 4): verification rules are deterministic, model behaviour is not.
