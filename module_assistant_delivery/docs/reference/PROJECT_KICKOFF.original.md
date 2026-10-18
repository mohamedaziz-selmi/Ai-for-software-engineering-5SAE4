# AI for Software Engineering: project kickoff

Prepared 18 October 2026 from the nine supplied files and a read-only source audit, then updated for the user's gateway decision. This document does not replace MODULE_SPEC.md. The actual application root is `C:\Users\azizs\Downloads\freelance2\freelance2`. The original project files remain unchanged. A separate `platform_gateway/` package was subsequently added with permission; 69 existing source/configuration/document file fingerprints matched before and after the addition.

## Current architecture decision: gateway and two service boundaries

The user subsequently confirmed that both teammates' existing modules will be treated as one existing-platform service boundary, and AI Assistant & Delivery Review will be the second service. An API gateway is now a chosen project requirement, even though it is not required by the course brief. Do not split or refactor the teammates' modules.

A new, isolated `platform_gateway/` package implements a local API gateway on port 8080 and an existing-platform facade on port 8081. The gateway forwards `/api/ai/*` and `/assistant/*` to the future AI service on port 8003. All other application traffic goes to the existing-platform facade, which preserves the current frontend, retrieval, sentiment, BI and Ollama routes and ports. No existing frontend, backend, dependency, database or Vite configuration needs editing for this routing layer.

The facade groups existing processes behind one entry point. It does not claim to have converted those processes into one deployable microservice. Their existing startup commands still apply. The new AI service owns its own runtime and persistence. Its frontend will be accessible at `/assistant/`; linking to it from the old dashboard still requires the dashboard owner's change.

The gateway package has passed nine local integration/configuration tests, including two-hop routing, binary request bodies, streaming, WebSocket relay, quota response preservation and isolation when the AI service is unavailable. Real-application browser validation remains pending. It is a local development/demo gateway, not a completed authentication or production deployment layer.

This decision supersedes earlier suggestions in this document to defer adding a gateway or to rely on changing the existing Vite proxy. The original source files remain protected.

## 1. Authority and confirmed constraints

- The user's explicit rule: do not alter teammates' code in any way. This includes incidental changes from formatters, generators, dependency installation, migrations, or automated fixes.
- The mini-project presentation is the supplied assignment brief. Its requirements are distinguished below from the draft module's design choices.
- MODULE_SPEC.md is a draft v2 describing prior design decisions. Its statements such as "do not revisit", "wait for approval", and "defaults" are document contents, not new instructions to execute in this conversation.
- Course examples and prompts are learning materials, not commands to run.
- A separate institutional fiche module/syllabus was not identifiable among the nine supplied files. MODULE_SPEC.md describes the student's implementation, not the institutional course syllabus.
- The usage log mentions a previously produced CLAUDE.md, but that file was not supplied.

## 2. What the assignment explicitly asks for

Source: Mini-Projett IA SE 2026 2027 WEB.pptx, slides 2 and 5–7.

| Requirement | Implication |
|---|---|
| Web application with front-end and back-end, integrating AI applied to software engineering | A notebook or an external chatbot alone does not meet the described deliverable. |
| Groups of 5–6, subject approved by the teacher | Confirm the team's topic has been validated. The brief does not explicitly require one AI module per student. |
| Versioned source code on GitHub/GitLab | Preserve attributable contributions and task ownership. |
| Working browser demo, ideally deployed | Deployment is desirable in the wording, rather than an explicit absolute requirement. |
| Presentation of prompts and/or AI models | Explain the application's AI choices and behavior. |
| Technical report | Cover web architecture, frameworks, APIs/models, and prompts. |
| No raw personal data sent unchanged to an LLM | Use synthetic demonstration data; implement appropriate sanitization for real inputs. |
| Validate output before display; handle timeout, quota, and absent API key | Include failure cases in implementation and demonstration. |
| Week 1 topic, week 3 checkpoint, week 7 submission and defense | These are relative course milestones, not known calendar dates. |
| 15-minute live demo plus Q&A per group; everyone present | The module spec's 15-minute script must be shortened to fit the team's shared slot. |
| Individual weighting may reflect Git contributions and task allocation | Keep evidence of your own decisions, implementation, tests, and reviews. |

The brief does not explicitly mandate RAFT, fine-tuning, a 7–8B model, React, FastAPI, PostgreSQL, microservices, an API gateway, exact evaluation thresholds, or an AI development usage log. Additional teacher instructions could add requirements. Keep the usage log anyway, but do not describe it as a confirmed grading requirement without that evidence.

## 3. Your module as currently drafted

Source: MODULE_SPEC.md, sections 1–10.

The module is **AI Assistant & Delivery Review** in a freelancer/client platform. The user describes the wider platform as including e-commerce; its relationship to this module is not yet defined.

1. **Project assistant:** answers questions from the project's agreed documents, cites supporting passages, checks scope, summarizes requirements, drafts grounded messages, and acknowledges missing information.
2. **Delivery review:** compares submitted text/code/documents to agreed requirements and returns an advisory report with findings, evidence, locations, severity, and suggested fixes. The client retains the delivery decision.

The draft also includes conversations, document upload/versioning, deliverable upload/versioning, FAQ, support requests, findings filters, and client decisions on findings. Ownership of documents, requirements, and submission screens must be checked against the other modules to avoid duplication.

Model choices explicitly confirmed by the user during this session:

- Assistant: local open model, initially the base model, then RAFT-tuned weights.
- Assistant fallback: hosted API only when the local model fails; disabled during base-versus-RAFT evaluation.
- Delivery review: hosted API model.
- No intent classifier or intent-based routing.

The development assistant (Claude Code or Codex) and the models inside the finished application are separate choices. Choosing Claude Code does not require Anthropic models in the app.

## 4. How the lessons support the work

| Supplied material | Relevant application |
|---|---|
| séance1-Introduction.pdf, especially pp. 32–43 | Understand limitations, the developer's validation role, and AI across the software lifecycle. |
| Prompt Engineering.pdf, pp. 9–10, 23–34 | Specify context, constraints and output schemas; iterate prompts; treat imported content as data; protect sensitive information. |
| Seance 3_Generation_du_code.pptx, slides 11–28 | Use scoped development prompts, review generated code, and validate changes with tests and static checks. |
| Séance 4 (1).pptx, slides 13–34 and 45–49 | Understand LoRA/QLoRA, RAG, RAFT, and model/API integration. This is the closest match to the proposed assistant. |
| Chapitre5 (6) (1).pptx, especially slides 13–26 | Separate specification-based acceptance tests from implementation-based unit tests; cover errors and boundaries. |
| Chapitre 6-Détection des bugs (1).pptx, slides 11, 19, 24–31, 36 | Evaluate findings, account for false positives, explain issues, and retain human validation. |

Interpretation: the lessons provide techniques and examples, rather than an exhaustive list of permitted tools. The supplied brief calls its example stack "indicative". Confirm any additional teacher-specific restrictions. Treat dated model comparisons and broad performance claims in lessons as teaching material rather than current purchasing evidence.

## 5. Tool recommendation

Use **Claude Code as the primary implementation tool** if that is your preference and you have access. It is designed to inspect repositories, edit files, run commands, and verify changes. Use ordinary Claude chat for explanation and design discussions. Codex is also a suitable implementation option, with documented Git worktree support; there is no project-specific evidence yet that either coding agent will produce better results on this repository.

Use one primary agent to edit a given working copy. An optional second tool can review the resulting diff. There is no reason to buy both before checking the subscriptions you already have.

Official references checked on 18 October 2026:

- [Claude Code overview](https://code.claude.com/docs/en/overview)
- [Claude Code permissions](https://code.claude.com/docs/en/permissions)
- [Claude project knowledge](https://support.claude.com/en/articles/9517075-what-are-projects)
- [Codex Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)

## 6. Protecting the other modules

A prompt saying "do not touch" is useful guidance, but it is not filesystem enforcement. A branch/worktree separates changes from the original checkout; it does not prohibit edits to protected files inside the copy.

Before implementation:

1. Inspect the repository read-only. Identify module ownership, shared files, current Git changes, auth, routes, database, build scripts, and extension points. Do not dump secrets or private configuration values.
2. Define exact paths that this module may create or modify. Until ownership is established, treat existing files as protected.
3. Capture a baseline of protected file contents, including relevant untracked files. Do not assume a clean Git status or overwrite existing work.
4. Use an isolated checkout with protected paths enforced read-only where feasible and only module-owned paths writable. Pair tool restrictions with filesystem isolation; shell scripts can modify files indirectly.
5. Review scripts before running them. Avoid repository-wide formatting, dependency upgrades, automatic fixes, generators, and shared database migrations.
6. Verify protected files against the baseline after each implementation task; review the full diff before delivery.

If adding a route, navigation item, dependency, shared schema, or gateway registration requires a protected-file edit, report the exact integration dependency and let the owning teammate perform it. Do not quietly reinterpret the user's absolute rule as permission for small changes. If the template has no extension point, full integration may require that teammate action.

## 7. Design issues to settle before coding

- **Unknown stack:** the spec says to discover the stack but later assumes React. Follow actual repository evidence. Its shared-database guidance also conflicts with its proposed dedicated AI database; resolve ownership and integration first.
- **Scope size:** document Q&A, training, delivery review, and several CRUD areas are substantial for one student's module. Establish an end-to-end core flow first and sequence optional extras around the deadline.
- **RAFT feasibility:** verify training resources and demo inference hardware early. Measure the base model with the same retrieval and held-out documents before claiming improvement. If fine-tuning is omitted, report that clearly.
- **Review certainty:** searching only a few file chunks cannot prove that a required feature is absent from the whole delivery. Use `cannot_determine` for insufficient evidence and reserve violation claims for supported cases.
- **Citation checks:** an exact quote existing in a source does not by itself prove the answer is supported by it. Evaluate whether the quote supports the claim as well as whether the quote exists.
- **Authorization:** a matching `project_id` and a generic `client` role are insufficient alone. Verify project membership and that the user is the authorized client for that project on every relevant endpoint.
- **Privacy:** pattern matching cannot guarantee removal of all personal information or secrets. Start with synthetic documents and define what content may reach a hosted model, including fallback calls and offline dataset generation.
- **Evaluation:** clarify whether severity macro F1 is conditional on matched findings; otherwise it can hide missed findings. Track detection and evidence quality as well as labels. The numerical targets in the draft are proposed targets, not teacher-confirmed thresholds.
- **Demo time:** the 15 minutes belong to the whole team. Agree on a short module segment.
- **Usage log:** the supplied file contains a partly completed design-session entry, with placeholders for actual prompts and evidence. Preserve real evidence; never invent historical conversations or commits.

These are review findings and recommendations, not changes already made to the spec. The following repository audit resolves several previously unknown facts.

## 7A. Read-only repository audit

All paths in this subsection are relative to `C:\Users\azizs\Downloads\freelance2\freelance2`.

| Finding | Source evidence |
|---|---|
| Active frontend is React 18.3 with Vite 6.4; declared versions use caret ranges | `package.json`; `src/main.jsx` imports `App.jsx` and `styles.css`. Archived Next.js assets do not make the active app Next.js. |
| Dashboard navigation uses React state and hard-coded component selection | `src/App.jsx`, `App()`, `galleryProjects`, and the final `activeProject` conditional. No module auto-discovery mechanism was found. |
| Proposal retrieval service uses FastAPI, persistent Chroma, MiniLM embeddings, BM25 and RRF | `rag_service/api.py`, `rag_service/README.md`. The API's introductory comment is stale; the implementation imports and uses BM25. |
| Sentiment service exposes `/predict` | `sentiment classifier/api.py`; its README describes TF-IDF with logistic regression/calibrated SVM selection. |
| Business intelligence has its own React workspace and FastAPI service | `src/BusinessIntelligence.jsx`, `module5_business_intelligence/api.py`, and its README. |
| Existing service ports | Vite: 8766; Ollama: 11434; retrieval: 8000; sentiment: 8001; BI: 8002. Defined in `vite.config.js`. |
| Existing proxy prefixes | `/ollama`, `/rag-api`, `/sentiment-api`, `/api/module5`. |
| Shared auth/project persistence was not found in inspected source | No matches for auth/JWT/login/project membership infrastructure in the selected application source search. `JOB-001` through `JOB-010` are generated as UI options in `App.jsx`. They do not establish a platform project database. |
| Existing retrieval is not a project-isolated assistant backend | `SearchRequest` exposes query, limit, category and mode, but no enforced project membership or `project_id` filter. Do not repurpose its shared collection for private project documents. |
| Documented frontend commands | `npm.cmd run dev`, `npm.cmd run build`, `npm.cmd run preview`. These were read, not executed. No frontend test script is declared. |
| Python environments are currently coupled | Sentiment and BI READMEs use the interpreter in `rag_service/.venv`. Do not install this module's dependencies there. |
| Source-control status remains unverified | No `.git` entry was visible in the application-root listing. Both Git executable attempts failed with a permission error; this does not prove the folder is or is not inside a repository. |

The visible feature groups fit the user's description of two contributed modules, but author ownership was not inferred from directory names. Treat every existing file as protected.

**Concrete integration constraint:** adding a new dashboard entry currently appears to require editing `src/App.jsx`; proxy integration would normally require `vite.config.js`. Both are protected. Existing styles and frontend dependencies are protected too. No such edits are authorized by the current instruction.

**Proposed safe development layout:** create a new `module_assistant_delivery/` directory under the application root, containing only this module's React workspace, FastAPI backend, isolated environment, data, tests, prompts and training/evaluation tooling. Use a separate temporary frontend entry (candidate port 8767) and backend (candidate port 8003), subject to availability checks. Keep the visual style consistent without modifying global CSS. A teammate who owns the shell can later connect the entry/component. This achieves isolated development inside the shared folder; dashboard integration remains an explicit external dependency. Do not claim the module is fully integrated while this step is outstanding.

Do not change the existing proposal reviewer into the delivery reviewer. They serve different stages: proposals before agreement versus deliverables checked against agreed requirements.

## 7B. Hardware, urgency, and zero-cost hosted API

User constraints now confirmed: finish as soon as possible; Claude Pro; $100 described as cloud-session credits; no Anthropic API-credit access and no budget for paid API usage. No fixed deadline date has been given.

Read-only hardware checks found:

- NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB VRAM (`nvidia-smi`).
- Approximately 15.8 GiB system RAM (Node OS API).
- Installed Ollama models/runtime health are unverified: the local connection attempt was blocked by the tool environment. This is not evidence that Ollama is absent or stopped.

A quantized 7–8B assistant is a reasonable candidate, subject to an actual memory/latency test with the intended context size. For training, use a small QLoRA smoke run first. Unsloth documents low-memory 7–8B training configurations but explicitly calls its figures minimums; context length, batch size, model architecture, and other GPU use matter. Do not promise that full RAFT training will fit merely because inference fits. Claude coding-session credits are not a substitute for GPU training resources.

**Initial hosted-model recommendation:** evaluate Groq's free-plan `openai/gpt-oss-120b` for delivery review, assistant fallback and limited offline generation. It is a candidate selected for available free API access and structured JSON support, not a claim of universal best quality. Keep the local assistant and RAFT plan unchanged. A free API still requires an API key; create/store it privately in the module backend, never in frontend source or chat.

Groq's published table currently lists this model at 30 requests/minute, 1,000/day, 8,000 tokens/minute and 200,000/day; the account's actual limits govern. Start with one review call at a time, bounded inputs, caching of completed work, and rate-aware retries. A 50-file review or bulk RAFT dataset generation can hit token limits well before request limits. Strict JSON schema support does not prove the findings are correct: still verify evidence and evaluate outputs.

Grok (xAI) and Groq are different services. xAI documents usage-priced API access; free chat or a free playground does not establish a free application API. Gemini has a free API tier on selected models and can be an alternative after checking account limits, with synthetic/non-sensitive data appropriate to its published free-tier data-use policy. No account was created, key requested, API call made, or paid service enabled.

Sources checked:

- [Groq free-plan rate limits](https://console.groq.com/docs/rate-limits)
- [Groq structured outputs](https://console.groq.com/docs/structured-outputs)
- [xAI API pricing](https://x.ai/api)
- [Gemini API pricing and free-tier data use](https://ai.google.dev/gemini-api/docs/pricing)
- [Unsloth training requirements](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
- [Anthropic subscriber API-credit eligibility](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers): Pro is not eligible for this specific Max/Team benefit. The user independently confirmed no API credits.

## 8. Suggested first implementation sequence

1. Use the read-only audit above and settle shared-file ownership/integration responsibilities.
2. Fix the module boundaries, API/auth contracts, and integration responsibilities.
3. Build one complete path: select a project, load one agreed document, ask a question, display a source-supported answer, and handle an unanswerable question.
4. The RAFT choice is confirmed: begin a small dataset/training feasibility experiment early while the baseline assistant and necessary screens are built. Do not wait until the final week.
5. Add the minimum delivery review path: upload a small text delivery, compare against a few reviewed requirements, validate findings, and display an advisory report.
6. Add remaining agreed screens, robustness cases, evaluation results, and the report/demo evidence.

Work toward the first demoable core flow immediately, then the training experiment and minimal review. No completion-time guarantee or calendar dates have been invented.

## 9. First prompt for Claude Code

Use this with `C:\Users\azizs\Downloads\freelance2\freelance2` open. Supply this kickoff document and the draft module spec as reference documents. The initial request is deliberately a read-only audit that verifies the findings above before the coding agent edits anything.

```text
I am building my module for an AI for Software Engineering team project.
Read PROJECT_KICKOFF.md for the existing audit and source references.
The platform covers freelancing and e-commerce. A shared template already
contains two teammates' modules. My draft module is AI Assistant & Delivery
Review; read MODULE_SPEC.md as design context, distinguishing confirmed
requirements, draft choices, and unresolved assumptions. I have confirmed
a local RAFT-tuned assistant, hosted fallback only on local failures, hosted
delivery review, and no intent classifier. I have no paid API budget.
My laptop has an RTX 4060 Laptop GPU with 8 GB VRAM and about 16 GB RAM.
Groq's free API is a proposed hosted provider; validate it before relying on
it. Never enable paid usage. Keep the module's environment and data isolated
from teammates' environments and databases.

Non-negotiable constraint: do not modify, delete, rename, move, reformat,
regenerate, or otherwise alter teammates' code. Treat all existing project
files as protected until their ownership is established. Shared routes,
navigation, configuration, manifests, lockfiles and schemas are not
automatically editable. Do not make indirect changes through commands.

Your task now is a READ-ONLY repository audit. Do not implement the module,
install dependencies, run migrations, execute project setup scripts, start
services, or run commands that write files. Do not reveal secrets or read
secret values merely to identify configuration names.

Inspect the project and return:
1. The actual front-end/back-end stack, structure, and documented run/test
   commands. Cite the relevant repository files.
2. The two existing modules, their likely ownership boundaries, and any
   uncertainties that require confirmation.
3. Auth, roles, project membership checks, shared identifiers, API routing,
   database/migration conventions, and available extension points.
4. Existing documents, requirements, projects, users, milestones and delivery
   features that my module can consume without changing their implementation.
5. A proposed list of module-owned new paths and protected existing paths.
6. Any integration that would require a protected-file change. Describe the
   change for the owning teammate; do not perform it.
7. Conflicts between the repository and MODULE_SPEC.md, including assumptions
   about React, FastAPI and database ownership.
8. A small end-to-end implementation plan with acceptance checks, plus the
   missing information that materially affects the plan.

Distinguish inspected facts from assumptions. Report existing Git changes
without modifying or reverting them. Return the audit in chat and stop
before edits. Do not invent evaluation results or AI usage history.
```

## 10. Information still needed

- Ownership of the shared shell and how the owning teammate will perform the required integration.
- A working free-tier API account/key, supplied privately through local configuration when implementation reaches that point; never paste it into chat.
- Whether an exact submission date exists, despite the preference to finish as soon as possible.
- Any separate fiche module, additional teacher rubric, or oral instruction about AI usage evidence.
- Whether the supplied source archive has an original Git remote/history available. Do not initialize or overwrite source-control metadata as part of this audit.
