### 11.1 The day before

- Start everything once and ask one question, so you know it works on that day (`demo/README.md`, "Before the
  demo").
- **Run at most one review the day before.** Each review uses about 26,000 of the free tier's 200,000 daily
  tokens, and the hosted fallback shares that budget.
- Charge the laptop and keep it plugged in during the demo (the local model runs on the GPU).

### 11.2 Ten minutes before

Double-click `control_center\START_PLATFORM.cmd`: it starts the control center and the front end and opens
http://127.0.0.1:8080. Then turn on **AI Assistant & Delivery Review** with the round button (bottom right). The model
loads by itself (about a minute; up to 4 minutes on the first start after a reboot).

### 11.3 The demo, in order (about 15 minutes)

| # | Show | Where | Point to make |
|---|---|---|---|
| 1 | The architecture diagram | This report, section 3 | Separate microservice behind the existing gateway; local model on the laptop, hosted model only for reviews and as fallback |
| 2 | The dashboard tile, then the module | http://127.0.0.1:8080 → **AI Assistant & Delivery Review** | Integrated in the template and the gateway |
| 3 | A question with a verified citation | Page Assistant, Freelancer A, "How many orders can a shop accept per pickup slot?" | The quote is checked in code, not trusted from the model |
| 4 | "Not in the documents" | "What is the hosting budget for the second year?" | No invented answers |
| 5 | Scope verdict | "Is online card payment included in this project?" | Answers "out of scope" with the clause |
| 6 | Access control | Switch to Freelancer C | A non-member cannot see the project (HTTP 403) |
| 7 | Upload, then ask | Upload `demo/documents/PRJ-DEMO-001_service_agreement.pdf` (type Contract), ask "Is there a limit on the freelancer's liability?" | A PDF is searchable at once; the citation gives the article and page |
| 7b | Every file type | Appendix C, scenarios 14 to 19: a TXT, a DOCX, a new version of a file, then the refused files | Each accepted type answers with a citation; each refused file gets a clear reason |
| 8 | A delivery review | Page Delivery review: Extract requirements, submit `demo/deliverables/M2_v1_with_defects`, Run review | The progress bar, then blockers with file, lines and exact quotes; the planted prompt injection is ignored |
| 9 | The client decides | Switch to Client B, Open last review, accept or dismiss a finding | The AI only advises |
| 10 | RAFT | This report, section 7 | What RAFT is, the criteria, why Base + RAG stays the default |
| 11 | Switch to RAFT, then the failure drill | Model button in the composer: pick RAFT and ask; then switch **Failure drill** on and ask "What is the fixed price of the project?" | RAFT is one click away; when the chosen model fails, the other one answers and the route says so |
| 12 | Evaluation and tests | Sections 8 and 9; run `cd backend; ..\.venv\Scripts\python.exe -m pytest`, then open http://127.0.0.1:8003/api/ai/docs | 61 tests pass; Swagger documents every refusal |
| 13b | The control center | The round button on any page: the map, the readings, a switch | My own microservice: one switch per module, its model included; GPU temperature watched |
| 13 | How you worked with the AI | Appendix A | Every prompt in order, with the structured tuning prompts where the tuning happened |

Optional: the hosted fallback (close the private Ollama window and ask again: the answer says "Hosted fallback answered").

### 11.4 Where everything is

| Thing | Location |
|---|---|
| This report, one file (Blackboard) | `module_assistant_delivery/docs/AI_Assistant_Delivery_Review_Mohamed_Aziz_Selmi.pdf` |
| The same report in Markdown | `module_assistant_delivery/docs/REPORT.md` |
| Demo script and files | `module_assistant_delivery/demo/` (a file of every type, and files that must be refused) |
| Run-and-test guide | `module_assistant_delivery/docs/RUN_AND_TEST.md` |
| Backend code | `module_assistant_delivery/backend/app/` (assistant: `assistant/`, review: `review/`, models: `llm/`, retrieval: `rag/`) |
| Prompts | `module_assistant_delivery/backend/app/llm/prompts/` |
| Frontend code | `module_assistant_delivery/frontend/src/` |
| Tests | `module_assistant_delivery/backend/tests/` |
| Evaluation scripts and results | `module_assistant_delivery/eval/` (`results/` holds every measured number) |
| RAFT data generators, training, export | `module_assistant_delivery/raft/` (results in `raft/results/`, adapters in `raft/outputs/`) |
| RAFT training data | `raft/data/generated_v2/` (run 2), `raft/data/generated/` (run 1), `raft/data/handwritten_val/` (validation) |
| AI usage log | `module_assistant_delivery/docs/AI_USAGE_LOG.md` (also Appendix A) |
| Gateway | `platform_gateway/` (route `/api/ai`, `/assistant` → :8003) |
| Code on GitHub | https://github.com/mohamedaziz-selmi/freelance-platform (private) |

### 11.5 Questions she may ask

- **"Did you train the model?"** The base model (Qwen2.5-7B-Instruct) is downloaded, not trained from scratch.
  RAFT adds a LoRA adapter trained on generated RAG-shaped examples; section 7 shows what each run measured and
  which model the app serves.
- **"Why didn't you use RAFT?"** I did, and measured it. It won on the validation set (24/28 vs 16/28) but lost the
  final test in the real app (19/24 vs 23/24, one harmful answer), so Base + RAG is the default. RAFT stays one click
  away in the model picker and is the first backup. Section 7 has the criteria and the cause.
- **"How do you stop hallucinations?"** Every claim needs a quote, and code checks each quote against the source
  text; answers or findings without a verified quote are withheld or dropped.
- **"Why a hosted model for the review?"** It judged better than the local models (13/13 vs 9/13 for Qwen3-4B) and
  the free tier costs nothing; the review never silently falls back to the local model.
- **"Is personal data sent to the cloud?"** Only masked text: e-mails, phones, IBANs, cards, IDs and secrets are
  replaced by placeholders before any model call.
- **"How did you test it?"** 61 automated tests with fake models (offline, repeatable), Swagger with every refusal
  documented, the model evaluations of section 8, and the demo kit's 19 scenarios run live. Testing every file type
  found two bugs, both fixed, and one honest limit of the review (section 9).
