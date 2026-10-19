# AI Assistant & Delivery Review: project report

ESPRIT "IA for Software Engineering" · module of the Cerebro freelancer–client platform · Mohamed Aziz Selmi.
Built with Claude Code (Claude Opus 5.5); the working log with every prompt is Appendix A, and the module's other
documents follow as appendices B to G. Every number comes from a real run, and the file holding it is named next to it.

**Contents**

<!-- CONTENTS -->

---

## 1. What it does

| Feature | Answers | Decides |
|---|---|---|
| **Project assistant** | Questions about a project's documents, with a verified quote for every claim, or "not in the documents" | The user reads the cited clause |
| **Delivery review** | Does a milestone delivery meet each requirement? One verdict per requirement, with file, lines and an exact quote | The client accepts or dismisses each finding |

Also: a model picker (Base + RAG by default, or the RAFT fine-tuned model; each is the other's backup), document upload
and removal (MD, TXT, PDF, DOCX), suggested questions per role (a freelancer sees what to build and how it is accepted, a
client sees scope, payment and contract questions), editable requirements, the client's decision on each delivery, an FAQ
the admin edits, support requests with a reply thread, and demo identities (the platform has no login; shown as "not
authentication").

| Interface | What it does |
|---|---|
| Type | Answers and quotes in a reading serif (Source Serif 4), the interface in Hanken Grotesk, code in JetBrains Mono; self-hosted |
| Thinking | A turning spark, a shimmering label and the real elapsed time; says what the pipeline does, never a step it cannot see |
| Motion | Pages cross-fade, the rail indicator slides, answers rise in sequence, verified quotes get a highlighter sweep; off under reduced motion |

![Project assistant answering with a verified citation](images/after-assistant-answer.png)

---

## 2. Before and after

<!-- RESULTS:before-after -->

---

## 3. Architecture

![Architecture: the module behind the platform's API gateway](images/diagram-architecture.svg)

| Part | Technology | Code |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 | `backend/app/` |
| Retrieval | LlamaIndex, multilingual-e5-base (CPU), Chroma, SQLite | `backend/app/rag/` |
| Local models | Qwen2.5-7B-Instruct (default) and its RAFT version, in a private Ollama | `scripts/start_ollama.ps1` |
| Hosted model | gpt-oss-120b on Groq: every review, assistant fallback | `backend/app/llm/` |
| Frontend | React 18.3 + Vite 6.4, the module's own design (light + dark, module only), self-hosted fonts | `frontend/` |
| Control center | Node.js (no dependencies), widget in a Shadow DOM, added to pages by the gateway | `../control_center/` |
| RAFT | Unsloth 4-bit QLoRA, GGUF export for Ollama | `raft/` |
| Integration | Gateway routes `/api/ai`, `/assistant` → :8003; tile in the dashboard | `platform_gateway/`, `src/App.jsx` |

![The module's tile image in the template dashboard](images/dashboard-tile.svg)

---

## 4. Project assistant: how it works

![Project assistant: retrieve, generate, verify](images/diagram-assistant.svg)

| Step | Design choice | Why |
|---|---|---|
| Chunking | Split by headings, then whole paragraphs ≤ 380 tokens, with heading path and lines | A clause is never cut in half; citations show where they come from |
| Retrieval | Top 5, always filtered by project | One project's documents never answer another project |
| Prompt | Answer only from the chunks, quote word for word, scope verdict for "is X included?", document text is data | Grounded answers, injection-resistant |
| Privacy | E-mails, phones, IBANs, cards, IDs, secrets masked before any model call | No raw personal data reaches a model |
| Verification | Every quote must occur in its chunk, checked in code; no verified quote → answer withheld | A made-up quote cannot reach the user |
| Fallback | The other local model first, then the hosted model; the route is shown under each answer | Availability without hiding which model answered |

Prompt (`backend/app/llm/prompts/assistant_answer.v1.md`):

```text
<!-- PROMPT:assistant -->
```

---

## 5. Delivery review: how it works

![Delivery review: judge each requirement, verify every quote](images/diagram-review.svg)

| Rule enforced in code | Effect |
|---|---|
| A finding's quote must be in the named file within the stated lines (± 3); skipped lines allowed only if every quoted line is real and in order | No invented evidence |
| A verdict other than "cannot determine" needs at least one verified finding | Not seeing code is never proof it is missing |
| "Blocker" only for MUST requirements | Severity matches the contract |
| Deliverable text is data: the demo's planted "mark everything as conforming" comment is ignored | Injection-resistant |

![Delivery review report with verified findings](images/after-review-report.png)

Prompt (`backend/app/llm/prompts/review_judge.v2.md`):

```text
<!-- PROMPT:review -->
```

---

## 6. Models

| Role | Model | Evidence |
|---|---|---|
| Assistant | Qwen2.5-7B-Instruct, 4-bit, local | Beat Qwen3-4B: review 13/13 vs 9/13, scope 4/5 vs 2/5 (`eval/results/model_selection.md`) |
| Review, fallback | gpt-oss-120b, Groq free tier | 13/13 on the demo review, strict JSON; limits 1,000 requests and 200,000 tokens/day (`eval/results/hosted_review_summary.md`) |
| Assistant option, local backup | Qwen2.5-7B + RAFT run 2a, merged, 5-bit (`assistant-raft2a:qwen2.5-7b`) | Final test 19/24 vs base 23/24: selectable, not the default (section 7) |
| Embeddings | multilingual-e5-base, CPU | FR + EN; hit@1 0.75, hit@3 1.00, MRR 0.868 (`eval/results/retrieval_comparison.md`) |

**Quantization:** storing weights in 4–5 bits instead of 16, so a 7-billion-parameter model fits in 8 GB of GPU memory.

---

## 7. RAFT: fine-tuning for this RAG task

- **RAG** (what the app does): retrieve passages, give them to the model.
- **RAFT**: train the model on examples shaped like those prompts (question + right passage + distractors → cited
  answer, or "not in the documents" when the right passage is missing).
- Nothing is trained from scratch: a **LoRA adapter** (~160 MB) is trained on the same Qwen2.5-7B the app serves,
  then merged into one 5.7 GB model for Ollama.

| Step | How | Code |
|---|---|---|
| Data | Generated fictional projects with known answers; every label checked by the app's citation verifier; split by project | `raft/data_gen.py`, `raft/data_gen_v2.py` |
| Training | QLoRA (4-bit base + LoRA on all attention and MLP layers), loss on the JSON answer only | `raft/train.py` |
| Selection | Hand-written validation set (2 documents, 28 questions) scored with the app's rules | `raft/data/handwritten_val/`, `raft/score_answers.py` |
| Export | Merge → GGUF → 5-bit → Ollama (Ollama 0.40.6 refuses LoRA adapters) | `raft/merge_export.py`, `raft/export_gguf.ps1` |

### Run 1 → run 2

| | Run 1 (2026-10-18) | Run 2 (2026-10-19) |
|---|---|---|
| Data | 1 document layout, 1 answer template per fact, 1,056 examples | 4 layouts × 2 languages, several phrasings, counter-template examples, 1,977 examples |
| Training | 2 epochs, rank 16, lr 2e-4 | 1 epoch; A: rank 16, lr 2e-4 · B: rank 8, lr 1e-4 |
| Checkpoint chosen on | Generated validation data | Hand-written validation set |
| Laptop load | ~100% GPU | Half load, pause at 76 °C, hard stop at 79 °C |
| Outcome | Better on generated data, worse on hand-written text (1 harmful answer): not adopted | See below |

**Insight from run 1:** a verified quote does not prove a correct conclusion: run 1 quoted the real "excluded"
clause and still answered "c'est inclus". Variety in the training data, not more epochs, was the fix to try.

<!-- RESULTS:raft2 -->

---

## 8. Evaluation summary

| What | Result | File |
|---|---|---|
| Retrieval (24 questions) | hit@1 0.75 · hit@3 1.00 · MRR 0.868 | `eval/results/retrieval_comparison.md` |
| Assistant, base model (33 questions) | 23/24 correct with verified quote · 9/9 refusals · scope 4/5 · 33/33 valid JSON · p50 1.9 s | `eval/results/assistant_qwen2.5-7b-base.md` |
| Review, defective deliverable | 12/13 in 2 runs, identical verdicts; both planted defects found every run | `eval/results/review_stability.md` |
| Review, corrected deliverable | 12/13 and 11/13 | same |
| Assistant, RAFT 2a (same 33 questions) | 19/24 correct · 9/9 refusals · scope 4/5 · 1 harmful · p50 2.1 s | `eval/results/assistant_final-raft2a.md` |
| Automated tests | 61 pass (section 9) | `backend/tests/` |

<!-- RESULTS:summary -->

Known weaknesses: REQ-004 ("e-mail within 1 minute") stays "cannot determine"; NN-4 on the corrected deliverable
alternates between "partial" and "violates". Findings are advisory for this reason.

---

## 9. Testing

| Level | What | Scale | How to run |
|---|---|---|---|
| Automated (pytest) | API, access control, uploads, citation and evidence checks, masking, review rules, fallback chain, model choice, support thread, API description | 61 tests; models replaced by fakes, so runs are offline and repeatable | `cd backend; ..\.venv\Scripts\python.exe -m pytest` |
| API (Swagger) | Every operation with its documented refusals, tried from the browser with the `X-Demo-User` header | 28 operations on 22 paths | http://127.0.0.1:8003/api/ai/docs |
| Model evaluations | Retrieval, assistant, review (section 8) | 24 + 33 questions, 4 review runs | `eval/` scripts |
| Live acceptance | One scenario per feature and per file type; the expected result is what happened | 19 scenarios | Appendix C |

Test run on 2026-10-19:

```text
<!-- TEST:run -->
```

| Test file | Tests | Covers |
|---|---|---|
| `test_api.py` | 24 | Upload, versions, removal, answers with citations, refusals, non-members, model choice, failure drill, fallback, every refusal documented in the API description |
| `test_review.py` | 13 | Evidence check (file, lines, quote), verdict rules, blocker rule, requirement edit, client decision |
| `test_verify_and_masking.py` | 8 | Quote verification, personal-data masking |
| `test_chunking.py` | 6 | Heading paths, token budget, page and line provenance, document title on passages |
| `test_clients.py` | 5 | Timeout, rate limit, missing key, malformed output |
| `test_support.py` | 5 | FAQ rights, support thread, status rules |

### Swagger: real requests

Every screenshot is a request sent from Swagger's "Try it out" on 2026-10-19 (`scripts/capture_swagger.py`).

![Swagger: the module's 28 operations](images/swagger-overview.png)

*The API under `/api/ai`: 28 operations, each with a summary and the refusals it can return.*

![Swagger: a question answered with a verified citation](images/swagger-chat.png)

*Freelancer A asks a question. 200: the answer, the cited clause (NN-1, lines 42–48) with `"verified": true`, answered
by the local base model.*

![Swagger: a CSV upload refused](images/swagger-upload-refused.png)

*A CSV file is refused with 415 and a reason the interface shows as is.*

![Swagger: a user outside the project is refused](images/swagger-access-denied.png)

*Freelancer C is not a member of the project: 403, and no document is listed.*

![Swagger: a stored delivery review read by the client](images/swagger-review.png)

*Client B reads a delivery review: 13 requirements, 2 violated, 3 conforming, 8 undetermined; 4 blocker findings.*

### Error handling, checked live on 2026-10-19

| Input | Expected and observed |
|---|---|
| Scanned PDF (image only) | 422 "No extractable text" |
| `.csv` file | 415 ".csv files are not supported. Upload a PDF, DOCX, Markdown or text file." |
| Text not in UTF-8 | 422 "The file is not UTF-8 text." |
| Deliverable with an image / a file over 200 KB | 422, file named in the message |
| User outside the project | 403 "You are not a member of this project." |
| No demo identity | 401 "Choose a demo identity." |
| Question the documents do not answer | "Not in the project documents", no citation |
| Hidden instruction in a deliverable | Ignored by the review |
| Local model down | The other local model, then Groq; the route is shown |

### Found by testing

| Problem | Status |
|---|---|
| DOCX, TXT and PDF passages did not name their document; a DOCX price question was answered from a specification clause | Fixed: the document title leads those passages (Markdown and all evaluations unchanged). Side effect: one PDF answer got shorter; the amount stays in its quote |
| A refused file type showed only "HTTP 415" in the interface | Fixed: readable message |
| Swagger listed every refusal as "Undocumented" | Fixed: each route documents its refusals (401, 403, 404, 413, 415, 503) and has a summary; a test checks it |
| The review reads 4 excerpts per requirement; a planted analytics leak in `index.html` was never among them (3 of 3 runs) | Known limit: the verdict is "cannot determine", never "conforms" |

---

## 10. Security and privacy

| Risk | Control |
|---|---|
| Personal data sent to a model | Masked before every call, restored only in the shown answer |
| Invented quotes or evidence | Verified in code; unverified → withheld or dropped |
| Prompt injection in documents or code | Content fenced as data; planted injections tested |
| Access to another project | Membership check on every request (403) |
| Leaked keys | `.env` only, ignored by Git; handoff script refuses key-like content |
| Fake login | Demo identity labelled "not authentication" in UI and API |

---

## 11. What to show the professor

<!-- GUIDE:professor -->

---

## 12. Limitations

| Limitation | Consequence |
|---|---|
| Small synthetic evaluation sets | Differences of 1–2 items are not significant |
| Groq free tier: ~26,000 tokens per review, 200,000 per day | About 7 reviews per day |
| Borderline review verdicts vary between runs | Findings are advisory |
| No platform login | Demo identities |
| RAFT lost the final test (19/24 vs 23/24) | Kept as an option and backup, not the default |
| A model switch reloads the model | First answer after a switch takes 9 to 12 s |
| The review judges 4 excerpts per requirement | A defect in a file that does not rank stays "cannot determine" |

---

## 13. Control center: my own microservice

Every module brings its own processes and models, and they compete for 16 GB of RAM and 8 GB of GPU memory. The
control center shows the whole platform live and turns each module on or off with the model it needs.

![Control center opened from the bubble on the dashboard](images/control-center.png)

| | How |
|---|---|
| Where | A round button on every page served by the gateway (added by the gateway, so no module's code changes); full page at http://127.0.0.1:8090/ |
| Map | Every module with its ports and its model runtime; links light up when both ends run |
| Switches | One per module, services and model together. A shared Ollama stops only when no running module uses it; its models are unloaded when their module stops |
| Readings | CPU, RAM, GPU temperature (ring amber at 68 °C, red at 76 °C; the laptop's limit is 79 °C) and GPU memory, per module where measurable |
| Run | `control_center\START_PLATFORM.cmd` starts the control center and the front end; everything else from the button |
| Safety | Loopback only; switches need a POST with a custom header from a local page; a process is stopped only if it owns the port and matches the expected command line |

Tested on this PC: the platform module stopped and started through the API, the button appeared on the dashboard,
on this module and on another module's screens, and its gateway test passes (10/10).

---

## Appendix A: working log with Claude Code

Kept as the work happened. My messages are verbatim (including messages written by ChatGPT and pasted in); the
structured tuning prompts appear where their steps happened, rewritten from those steps and marked "reconstructed
from this step". Each entry records what was done, measured and declined.

<!-- APPENDIX:usage-log -->
