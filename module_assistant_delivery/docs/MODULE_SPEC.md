# Module Spec: AI Assistant & Delivery Review (working copy)

> **Working copy v6, 2026-10-19.** Derived from draft v2 (`reference/MODULE_SPEC.original.md`, unchanged).
> Labels: **[TBD]** needs an owner decision · **[ASSUMPTION]** default chosen so work can continue ·
> **[DEMO]** stand-in for platform functionality that does not exist (`AUDIT.md`) ·
> **[PENDING CONFIRMATION]** a change proposed by a later prompt that reverses an earlier owner decision.
>
> **Change log**
> - v3 (session 1, morning): repository facts from `AUDIT.md`; separate service on :8003 behind the gateway; demo adapters.
> - v5 (session 1, later): owner restored hosted review + hosted fallback (D5); model decision recorded (D10); template conventions followed (D8, D12).
> - v4 (session 1, afternoon): the owner supplied a ChatGPT-written implementation prompt (verbatim in `AI_USAGE_LOG.md`), marked "not final", and asked Claude Code to adopt good suggestions and pick a better model for RAG/RAFT if one exists. Changes: local-only model policy **[PENDING CONFIRMATION]**; LlamaIndex + Chroma for retrieval; React frontend; Unsloth for RAFT; generative model chosen **by measurement** between two candidates (§6.1).
> - v6 (2026-10-19): statuses brought up to date. Every endpoint is built (§9); the model is chosen at runtime
>   (Base + RAG default, RAFT selectable and the local backup); the interface has its own design (D8); the review
>   runs on the hosted model (§5.2); Git repository and dashboard link done (§13).

## 0. Decisions in force

| # | Decision | Source | Status |
|---|---|---|---|
| D1 | Separate service :8003, API `/api/ai/*`, UI and assets `/assistant/`, behind the existing gateway :8080; teammates' modules behind the facade :8081 | Owner, msg 1 | Settled |
| D2 | Teammate files, shared config, environments, datasets and databases are read-only. No integration edits. Gateway read-only this milestone | Owner, msg 1 | Settled |
| D3 | Assistant = local open model, base first, RAFT-tuned later on the same endpoint | Owner, msg 1; ChatGPT prompt | Settled. Since 2026-10-19 Base + RAG is the default and RAFT a runtime choice and backup (owner; RAFT lost the final test) |
| D4 | No intent classifier | Owner, msg 1 | Settled |
| D5 | **Hosted delivery review + hosted assistant fallback (Groq free tier, `openai/gpt-oss-120b`)**. The local model answers; the hosted model is used only when the local model fails (assistant) and always for reviews. Fallback disabled in every evaluation. Without a key: the app starts, health reports `review: degraded`, review requests return a clear 503, the assistant keeps working; the review never falls back to the local model | Owner msg 1, **re-confirmed in msg 4** ("Restore my first decision"), replacing the ChatGPT prompt's local-only policy | **Settled**. `REVIEW_PROVIDER=local` remains only as an explicit offline/demo option |
| D6 | Zero paid services; no cloud GPU rentals or promotional credits | Both | Settled |
| D7 | Retrieval: LlamaIndex local components + module-private persistent Chroma; SQLite for app data | ChatGPT prompt | Adopted |
| D8 | Frontend: separate React app (React 18.3 + Vite 6.4, the team's stack) built and served under `/assistant/`, **following the template's module pattern** (the Business Intelligence workspace: `review-workspace` shell, eyebrow path, status pill, numbered tabs, Arial + Consolas, the template palette) | ChatGPT prompt; owner msg 3 ("follow the template that is already in the freelance folder") | **Replaced 2026-10-19** by the module's own design (owner: "bold new look", this module's interface only) |
| D9 | RAFT: Unsloth 4-bit QLoRA on the **same checkpoint** that is served as the base model; same output schema in training and inference | ChatGPT prompt | Adopted |
| D10 | Generative model: **`Qwen/Qwen2.5-7B-Instruct`**, chosen by measurement against `Qwen/Qwen3-4B-Instruct-2507` (§6.1, `eval/results/model_selection.md`): both train locally, and the 7B is clearly better at review, held-out abstention, citation and scope | Owner, msg 2 ("if you can find a better model… use it") | **Decided** |
| D11 | Embedding model: `intfloat/multilingual-e5-base` (CPU) | ChatGPT prompt; owner msg 2 | **Kept**: on the dev set the gold section is in the top 3 for every question (hit@3 = hit@5 = 1.00, MRR 0.868, `eval/results/retrieval_comparison.md`), so a different embedder has no measurable headroom there. Re-check on the multi-document RAFT test split |
| D12 | Backend run convention like the other platform services: `backend/api.py`, `uvicorn api:app --port 8003`, `/health` reports `ready` | Template (module5, rag_service, sentiment) | Adopted |

## 1. Context

- ESPRIT mini-project "IA for Software Engineering", 2026-2027: a web application with AI modules. 6 students; group defense 15 min demo + Q&A for the whole team. Individual grading may use Git contribution. Since 2026-10-18 the application root is a Git repository (private GitHub `mohamedaziz-selmi/freelance-platform`).
- Platform: freelancer-client projects. Agreed documents (cahier des charges, contract), deliverables, client review.
- **What exists (verified):** a React 18 + Vite portfolio shell, a proposal retrieval service, a sentiment service, a BI module, and a Node gateway + facade. **No** authentication, users, roles, projects, membership, milestones, deliverables or shared database. This module uses **[DEMO]** adapters for them.
- Brief rules: no raw personal data to an LLM; validate AI output before display; handle API errors (timeout, quota, missing key); deliverables include versioned code, a working demo, prompts/models presentation and a technical report. With the hosted API (D5), all of these cases are real and handled: timeout and 429 with `Retry-After` (waits capped at 60 s, then a clear rate-limited error), missing key (review degraded, assistant unaffected), malformed output (one repair retry, Pydantic validation), local model down (fallback when enabled).

## 2. Module in one paragraph

Users (freelancer or client) chat with a **project assistant** that answers only from the project's agreed documents, with **verified citations**, and abstains ("not found in the project documents") when the documents do not support an answer. When a freelancer submits a **deliverable** (text or code), the module runs a **conformance review** against the project's requirements and produces evidence-backed **findings**. Findings are advisory: the client decides.

## 3. Actors and user stories

Unchanged from v2: freelancer (requirements, scope checks, checklists, grounded drafts, submit deliverables, explain findings), client (what was agreed, decide on findings, accept/reject delivery), both (FAQ, support). All identities are **[DEMO]** until real authentication exists.

## 4. Scope and non-goals

Out of scope (unchanged): automatic acceptance/rejection; intent classification; legal advice (document text prevails, with a disclaimer); modifying deliverables or agreed documents; binary files, images, scanned PDFs; payments/milestones/contracts as platform features. Also: building real authentication or a platform project database. (Runtime model choice was a non-goal until the owner asked for it on 2026-10-19.)

## 5. Features

### 5.1 Project assistant
Retrieve from the project's active documents → generate a grounded JSON answer → verify citations in code → display. Covers requirements, non-negotiables, scope checks (`in_scope`/`out_of_scope`/`ambiguous` + clause), contract terms, checklists, grounded drafts, summaries. French and English. Unrelated questions get a polite refusal from the prompt (no classifier). "Explain this finding" reuses the assistant.

### 5.2 Delivery review
Freelancer submits text/code files for a **[DEMO]** milestone → module loads requirements → per-requirement retrieval over the deliverable → hosted-model judge (D5) → evidence verification → findings + conformance summary → client marks findings accepted/dismissed. Retrieval not finding something is **not proof of absence**: use `cannot_determine` when evidence is insufficient.

### 5.3 Screens (React, `/assistant/`)
One workspace built like the template's Business Intelligence workspace (`../../src/BusinessIntelligence.jsx` + `bi-workspace.css`): header with the eyebrow path "Cerebro / AI assistant · delivery review", title, model status pill and close button; sticky numbered tabs **01 Project assistant · 02 Delivery review · 03 Help & support**; a demo-identity/project bar labelled "Not authentication"; two-column bodies like the template's review workspace (inputs left, results right).
- 01: project documents (upload, versions), earlier conversations, chat with expandable verified sources.
- 02: deliverable submission (freelancer), deliverable versions, requirements, conformance report (severity tiles, coverage table), findings with evidence, "Explain this finding", accept/dismiss (client only).
- 03: FAQ (admin edits), support requests (users create, admin triages).

Since 2026-10-19 the module has its own design (owner: "bold new look", module only): a left rail (pages, system status), a top bar (demo identity, project, model status, theme) and a model picker in the composer (Base + RAG or RAFT, plus the failure drill). All styles are scoped to `.ad-app`, so nothing leaks into the dashboard. `AssistantWorkspace` still accepts an `onClose` prop; standalone, "Cerebro dashboard" returns to `/`.

## 6. Architecture

```
Browser ── :8080 platform_gateway (read-only) ──┬── /api/ai/*, /assistant/*  → this service :8003 (path preserved)
                                                └── everything else          → existing-platform facade :8081

module_assistant_delivery/
  backend/app (FastAPI :8003)
    api/           REST under /api/ai
    assistant/     retrieve + generate + citation verification
    review/        delivery review pipeline
    rag/           loaders (MD/TXT/PDF/DOCX/code) → clause-preserving chunker → LlamaIndex
                   HuggingFaceEmbedding (CPU) → LlamaIndex ChromaVectorStore (storage/chroma)
    llm/           LLM layer: PII masking, OpenAI-compatible client, JSON-schema output,
                   validation + one repair retry, call log (no content), versioned prompts
    integrations/  [DEMO] identity + project directory
    db.py          SQLite (storage/assistant.sqlite3): documents, versions, chunks + provenance,
                   conversations, messages, llm_call_log, requirements, deliverables, reviews,
                   findings, FAQ, support requests and their messages
  frontend/        React 18.3 + Vite 6.4, base /assistant/, built to frontend/dist
  raft/            dataset generation, Unsloth training, export to GGUF/Ollama
  eval/            datasets + runners; results in eval/results/
  storage/         git-ignored: SQLite, Chroma, private Ollama store, HF cache
Private Ollama :11435 (store in storage/ollama) serves the base model and the RAFT model, one loaded at a time
```

The shared Ollama on :11434 is not used: the teammates' chat auto-selects its first installed model (`AUDIT.md`).

**Identity:** the UI sends `X-Demo-User`; the backend resolves it with `DemoDirectory` and checks project membership **before** any retrieval. A browser-supplied `project_id` is never authorization on its own. Health and the UI state `authentication: false`.

### 6.1 Generative model selection (D10)

Requirements: French + English; JSON output with citations; local inference on 8 GB VRAM with room for an 8k context; **4-bit QLoRA training of the same checkpoint on the same GPU**; Ollama-servable quantization; open licence.

| Candidate | Serve (Q4_K_M) | QLoRA minimum (Unsloth table) | Notes | Status |
|---|---|---|---|---|
| `Qwen/Qwen2.5-7B-Instruct` | ~4.7 GB | 5 GB (7B row), absolute minimum | ChatGPT prompt's pick; mature; Apache-2.0 | Candidate |
| `Qwen/Qwen3-4B-Instruct-2507` | ~2.5 GB | ~3.5-4 GB (3B row 3.5 GB; third-party calculator 3.7 GB at 2048 tokens) | Newer (2025); non-thinking instruct variant; Apache-2.0; Ollama tag `qwen3:4b-instruct-2507-q4_K_M` | Candidate |
| Qwen3.5-4B / 9B (2026) | ~4 / 5.3 GB | Unsloth: QLoRA **not recommended** for Qwen3.5; bf16 LoRA 10 GB / 22 GB | Does not fit 8 GB training | Excluded |
| Gemma 4 E4B (2026) | — | Unsloth: ~10 GB | Does not fit 8 GB training | Excluded |
| Qwen3-8B | ~5.2 GB | 6 GB minimum | Hybrid thinking mode; tight on a laptop with ~6.9 GB free | Excluded |

**Result:** Qwen2.5-7B-Instruct (see `eval/results/model_selection.md`). Procedure as run:
1. Same retrieval, same documents, same dev questions (`eval/datasets/assistant_dev.jsonl`), fallback disabled: JSON validity, verified-citation rate, keyword correctness, abstention on unanswerable/off-topic/cross-project questions, latency.
2. Unsloth QLoRA smoke run for each at the planned RAFT sequence length: peak VRAM, step time, OOM or not.
3. Pick the candidate that trains locally at the planned sequence length and performs at least comparably. If both train, prefer better measured quality. The RAFT model is then trained on that **same** checkpoint.

## 7. Data model

As v2, implemented in SQLite: `documents` (id, project_id, title, doc_type, file_kind, source_name, version, status active/superseded, sha256), `chunks` (text, heading_path, page, line_start, line_end, embedding_model; vectors in Chroma under the same id), `conversations`, `messages` (citations, grounded, status, scope_verdict, served_by, model, prompt_version, retrieval, verification), `llm_call_log` (metadata only). Also (built): `requirements`, `deliverables`, `deliverable_files`, `reviews`, `requirement_results`, `findings`, `faq_entries`, `support_requests`, `support_messages`. User/project/milestone ids are **[DEMO]** strings.

## 8. AI components

### 8.1 Ingestion and retrieval
- Loaders: Markdown, TXT, source code; text-based PDF (LlamaIndex `PDFReader`, page provenance) and DOCX (LlamaIndex `DocxReader`). Scanned/image-only files are rejected.
- Chunking preserves clauses: Markdown headings or numbered clause headings first, then whole paragraphs packed to a token budget **counted with the embedding model's tokenizer** (≤ 380 of e5's 512). Code: 80-line windows, 10 overlap. Each chunk keeps heading path, page and line range.
- Embedding: `query:` / `passage:` prefixes for e5, normalized vectors, CPU.
- Retrieval: membership check → active document ids for the project from SQLite → Chroma query filtered by `project_id` AND `document_id IN active` AND `embedding_model` → re-join with SQLite and drop any hit whose project differs (defence in depth). Top-k = 5.
- **[ASSUMPTION]** Keyword/BM25 hybrid only if the eval shows a gain. If added, it is built per project from SQLite rows **after** the same access check.
- Embedding comparison (D11): e5-base measured on the dev set (hit@5 = 1.00). Alternatives (Qwen3-Embedding-0.6B, bge-m3) are only worth comparing on a harder, multi-document set; switch only for a clear gain.

### 8.2 Assistant answer generation
Prompt `backend/app/llm/prompts/assistant_answer.v1.md` (system + user template). Context chunks are labelled `C1..Ck` per request, each with document title and section, inside `<chunk>` delimiters that document text cannot close. Output JSON schema `{answer, citations[{chunk_id, quote}], grounded, scope_verdict}`, requested with JSON-schema constrained decoding, plus one repair retry. Code checks: cited chunk was provided; quote occurs in it after normalization; otherwise the citation is dropped; `grounded` with no surviving citation → answer withheld ("not_found_after_verification"). A quote existing does not prove support. The faithfulness eval measures that. **RAFT training data is rendered with this same function.**

### 8.3 Delivery review (hosted model, D5)
Load files (≤ 50 files, ≤ 200 KB each **[ASSUMPTION]**), chunk (code windows / headings), per requirement (must → should → could) retrieve deliverable chunks, judge with JSON schema `{requirement_id, verdict conforms|partial|violates|cannot_determine, findings[{file_path, line_start, line_end, severity, explanation, suggested_fix, evidence_quote, confidence}]}`, verify `evidence_quote` at the stated location, one repair retry, aggregate. Deliverable text is untrusted (prompt-injection test). Requirements are judged sequentially to respect the free-tier token-per-minute limit; `x-ratelimit-*` headers are recorded. Only synthetic deliverables are sent while on the free tier (PII/secret masking still applies).

### 8.4 LLM layer
PII masking before every call (emails, Tunisian and international phones, IBAN, Luhn-valid cards, labelled CIN, secrets), stable placeholders restored for display; Pydantic validation; timeouts; hosted fallback for the assistant only on local failure; JSON-schema output with a one-time downgrade to JSON mode if the provider rejects the strict schema; `served_by`; call log without content; versioned prompts.

### 8.5 RAFT
- **Data:** procedurally generated synthetic French/English project documents (cahiers des charges, contracts, briefs) with randomized but recorded facts, so every label is **correct by construction** and traceable to an exact passage. Each example: question + oracle chunk + 3-4 distractors (same and other documents), ~20% without the oracle → abstain. Targets use the exact runtime JSON schema with exact quotes. Paraphrased questions may come from the local model; every label is validated in code (quote ∈ oracle chunk, schema valid). Train/eval split **by source document/project**; the dev documents in `data/seed/` are never used for training.
- **Training:** Unsloth 4-bit QLoRA on the chosen checkpoint; batch size 1, gradient accumulation, gradient checkpointing, conservative sequence length set from the measured token length of examples (no truncation of evidence or targets: long examples are dropped and counted, not cut). Private Ollama stopped during training. Smoke run first, then the planned run.
- **Serve (as built, `raft/export_gguf.ps1`):** Ollama 0.40.6 rejects LoRA `ADAPTER` lines, its quantizing safetensors importer does not support Qwen2, and GGUF imports must be pre-quantized. Path used: offline merge (NF4 dequantized on the GPU + LoRA delta) → bf16 safetensors → bf16 GGUF (llama.cpp v0.5.0 converter, pure Python) → Q5_0 GGUF (gguf-py, pure Python; Q8_0 embeddings/output) → `ollama create`. The base goes through the **identical** path (`assistant-base-requant:qwen2.5-7b`), so base vs RAFT differs only by the adapter. The official Ollama build (`qwen2.5:7b-instruct`, Q4_K_M from the original bf16) is reported separately.
- **Evaluate:** base vs RAFT, identical retrieval/documents/questions, fallback disabled: correctness, citation support, abstention, JSON validity, latency. Report actual numbers only. If training cannot run locally, report the exact blocker.
- **Status after run 1 (2026-10-18, `eval/results/raft_findings.md`):** trained locally (80 min, 5.6 GB). Large gains on the generator-shaped held-out test (abstention 33/33 vs 23/33, no distractor citations). No gain on the hand-written dev document (20/24 vs 23/24), with one harmful template error. **The app keeps the base model**; run 2 needs more diverse data, 1 epoch and hand-written validation.
- **Status after run 2 (2026-10-19, report section 7):** RAFT 2a won the hand-written validation set (24/28 vs 16/28) but lost
  the final test in the real app (19/24 vs 23/24, 1 harmful answer). Base + RAG stays the default; RAFT 2a is served as
  `assistant-raft2a:qwen2.5-7b`, selectable in the interface and the base model's first backup.

## 9. API (`/api/ai`)

| Method | Path | Status |
|---|---|---|
| GET | `/health` | done |
| GET | `/demo/identities` | done ([DEMO]) |
| GET | `/projects` | done |
| GET/POST/DELETE | `/documents`, `/documents/{id}` | done (MD, TXT, PDF, DOCX, code; removal restores the previous version) |
| POST | `/chat` | done (`model`: base or raft; `simulate_failure`: the failure drill) |
| GET | `/conversations`, `/conversations/{id}` | done |
| GET/POST/PUT | `/requirements`, `/requirements/extract`, `/requirements/{id}` | done |
| GET/POST | `/deliverables`, `/deliverables/{id}/review`; GET `/reviews/{id}` | done |
| PATCH/POST | `/findings/{id}`, `/deliverables/{id}/decision`; POST `/findings/{id}/explain` | done |
| GET/POST/PUT/DELETE | `/faq`, `/faq/{id}` | done |
| GET/POST/PATCH | `/support-requests`, `/support-requests/{id}`, `/support-requests/{id}/messages` | done |

28 operations; Swagger (`/api/ai/docs`) documents each one's refusals.

## 10. Evaluation
Datasets in `eval/datasets/*.jsonl`, results in `eval/results/*.md`. Assistant: keyword correctness (a crude proxy, labelled as such), verified-citation rate, gold-section citation rate, abstention accuracy (unanswerable, off-topic, cross-project), JSON validity first try, latency p50/p95. Retrieval: hit@k, MRR. Review: conformance accuracy, severity macro F1 + detection recall. Robustness: injection, model down, malformed JSON, cross-project isolation. All thresholds are proposals **[TBD]**.

## 11. Security and privacy
Loopback binding only; demo identity is not a security boundary; membership check before retrieval; project filter + active-version filter + post-filter; uploads: type allow-list, 5 MB limit, temp files deleted; model output rendered as text; no content in logs; secrets only in the module `.env`.

## 12. Build order
1. ~~Audit~~ (`AUDIT.md`). 2. Working upload → retrieval → cited answer flow with React UI. 3. Model + embedding comparison (§6.1, §8.1). 4. RAFT smoke → dataset → planned training → base vs RAFT eval. 5. Delivery review + findings UI. 6. FAQ/support CRUD, history, remaining screens. 7. Report and demo rehearsal.

## 13. Open decisions

| # | Decision | Status |
|---|---|---|
| 1 | D5 hosted review + fallback | **Settled** (owner msg 4). Groq checked with the owner's key: strict JSON schema accepted; live review 13/13; fallback verified (`eval/results/hosted_review_summary.md`) |
| 2 | Generative model (D10) | Decided: Qwen2.5-7B-Instruct (measured) |
| 3 | Embedding model (D11) | Kept e5-base (dev-set retrieval saturated) |
| 4 | Team Git repository | **Settled**: private GitHub repository (2026-10-18) |
| 5 | Dashboard link to `/assistant/` | **Done** 2026-10-18 with the owner's approval (`docs/integration/dashboard_link.patch`) |
| 6 | Macro F1 on severity vs verdict | [ASSUMPTION] severity + detection recall |
| 7 | Deliverable limits | [ASSUMPTION] 50 files, 200 KB each |
| 8 | Demo segment length within the team's 15 min | **[TBD]** with team |
