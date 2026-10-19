# Agentic Freelance Research & Technical Advisor (Cerebro, Module 7)

A single local AI agent that researches how to implement a freelance technical project and returns a
sourced implementation guide. The freelancer describes a project; the agent plans the research, chooses
tools by itself, evaluates what it found, searches again where evidence is missing, and writes the guide.

**It only researches and advises.** It never clones, downloads, installs or runs anything, and it never
writes the freelancer's project. A FastAPI backend, plus a "Freelance Advisor" screen in the sibling front end
(`../freelance2`, see "Use it from the front end"). Independent of Cerebro Modules 1-6.

> **Full project report** (what was built, step by step, with code explanations, measurements, bugs found and
> fixed, limitations): [REPORT.md](REPORT.md). Guidance for AI coding assistants: [CLAUDE.md](CLAUDE.md).

## How it works

```
START -> plan -> agent --tool calls--> tools --> evaluate --gaps and budget left--> agent
                   |                                |
                   +--no tool call (wants to stop)--+--sufficient evidence or a limit hit--> report -> END
```

| Node | What it does |
|---|---|
| plan | The local LLM reads the request once (structured output): objective, requirements, assumptions, whether datasets / GitHub examples are needed. The plan is then checked against the request: a "not needed" the freelancer contradicts is overridden, and technical constraints the request never states are removed (both are reported). |
| agent | The LLM decides: call a tool (which one, with which query) or stop. Its prompt is rebuilt from the evidence ledger every turn, so it always fits the 4096-token window. If the model is cut off twice without a decision, the evaluator's next step is executed instead and **clearly marked** (`decided_by: "fallback"`). |
| tools | Executes the calls with timeouts, a per-turn cap, duplicate detection and unavailable-tool handling. Every result is registered as evidence (S1, S2, ...). |
| evaluate | Judges coverage of eight areas **from the retrieved evidence, not from the LLM's opinion**, and tells the agent exactly what is still open. Sends it back if it says DONE too early. Without web search it directs the agent to read the README and dependency file of the best repository found. |
| report | Writes sections A-G. C and G are built by code from the evidence; B, D, E, F are model-written recommendations that are checked afterwards. |

**Research tools** (all real, none simulated): `search_web` (Tavily), `search_github_repositories` and
`inspect_github_repository` (GitHub REST API), `search_huggingface_datasets` (Hugging Face Hub, metadata only).

**Grounding rules**
- Every URL in the report comes from a tool result. The model is told not to write URLs; any URL or `[S#]`
  citation it writes that is not in the evidence ledger is removed, and the removal is reported.
- Metadata (stars, downloads, licenses, dates) is copied from API responses. Missing metadata is shown as
  "not stated", never guessed. In the model-written sections, a statement that cites a source but gives a different
  license, download/star count or source name is kept and marked `[CHECK: ...]`.
- Retrieved web/repository text is untrusted data: instruction-like sentences and raw URLs are stripped, the
  content is fenced, and no tool has side effects.
- If a tool fails or is not configured, the run continues with the others and the report says what could not be verified.

## Requirements

- Windows/macOS/Linux, [uv](https://docs.astral.sh/uv/), Python 3.12 (uv fetches it)
- [Ollama](https://ollama.com) with the model `qwen3:4b-instruct` (about 2.5 GB). `qwen3:4b` also works but is much slower
- Tuned and measured on an RTX 2050 (4 GB VRAM), i7-12700H, 24 GB RAM. See "Performance" below.

## Setup

```powershell
uv sync                                   # create .venv and install the locked dependencies
ollama pull qwen3:4b-instruct             # recommended model (2.5 GB); see Performance below
copy .env.example .env                    # only if .env does not exist; then add your keys
uv run python -m scripts.check_setup      # verifies dependencies, config, keys, Ollama
```

### API keys (in `.env`)

| Variable | Needed | How to get it |
|---|---|---|
| `TAVILY_API_KEY` | For web search. Without it the agent still works with GitHub + Hugging Face and says documentation could not be verified. | Free at https://app.tavily.com (1,000 credits/month, no credit card) |
| `GITHUB_TOKEN` | Recommended. Without it: 10 search requests/min and 60 other requests/hour. | https://github.com/settings/personal-access-tokens: fine-grained token, public repositories only, no extra permissions |
| `HF_TOKEN` | Optional. Public dataset metadata works anonymously (verified). | https://huggingface.co/settings/tokens |

## Run the API

```powershell
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in a browser: it forwards you to the interactive documentation at
http://127.0.0.1:8000/docs, where you can try every endpoint (before this, the bare address showed
`{"detail":"Not Found"}` because only `/health`, `/tools`, `/research` and `/docs` exist).

A research request takes minutes, and the server console shows its progress line by line (for example
`[agent] turn 2: the model is choosing the next step`, `[report] writing section D ... 2 of 4`). Silence for up to
two minutes between lines is normal: that is one model call.

| Endpoint | Purpose |
|---|---|
| `GET /health` | API status, Ollama reachability, whether the model is installed, whether a run is in progress. |
| `GET /tools` | The four research tools and their configuration status. |
| `POST /research` | Runs the agent and returns the report, sources, tool execution history, plan, evaluation and stats. **Synchronous: it takes several minutes.** One run at a time (a second request gets HTTP 429). 503 if Ollama or the model is missing. 422 if the text does not say what to build (for example the placeholder `your project`): it is refused before any work, because the agent would otherwise invent a topic. |
| `POST /research/stream` | The same run and the same checks (422, 503, 429 are plain HTTP errors sent before anything streams), but answered as Server-Sent Events: `progress` events (`{stage, message, elapsed_seconds}`) while the agent works, then one `result` event (the same JSON as `/research`) or one `error` event (`{status, detail}`). A comment line every 15 s keeps the connection open. This is what the front end uses to show live progress. |

Sample request. **The server must be running first** (the `uvicorn` command above, left open in its own terminal),
otherwise curl says `Failed to connect to 127.0.0.1:8000`. Use the form that matches your shell: quotes are handled
differently, and a Bash-style command pasted into Windows PowerShell sends a broken body.

Windows PowerShell (recommended, verified: HTTP 200 in about 2 minutes with `qwen3:4b-instruct`):
```powershell
$body = @{ project_description = "Build a fake news detection system using Python and machine learning." } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/research -Method Post -ContentType "application/json" -Body $body -TimeoutSec 2400 |
    ConvertTo-Json -Depth 20 | Out-File research.json -Encoding utf8
```

Windows PowerShell with `curl.exe` (single quotes outside, `\"` inside; **not** double quotes outside):
```powershell
curl.exe -X POST http://127.0.0.1:8000/research -H "Content-Type: application/json" --max-time 2400 -d '{\"project_description\": \"Build a fake news detection system using Python and machine learning.\"}'
```

Bash, macOS, Linux or Git Bash:
```bash
curl -X POST http://127.0.0.1:8000/research -H "Content-Type: application/json" --max-time 2400 \
     -d '{"project_description": "Build a fake news detection system using Python and machine learning."}'
```

Symptoms: `Failed to connect` = the server is not running; `JSON decode error` or `Could not resolve host: fake` = a
quoting problem (use the PowerShell forms above); `422` = the text does not say what to build; `429` = a run is
already in progress.

Response fields: `report` (`markdown` and the seven `sections`, each labelled with its `origin`, plus
`limitations` and `validation`), `sources` (the evidence ledger), `tool_history` (every tool call: arguments,
status, duration, source ids, `decided_by`), `plan`, `evaluation`, `stop_reason` and `stats` (per-LLM-call timing).

## Use it from the front end (`freelance2`)

The Cerebro front end (`../freelance2`, Vite + React) has a **Freelance Advisor** triangle in its gallery. It opens a
dialog with a text box, six freelance example briefs to start from (Python ML, Laravel shop, Flutter app, FastAPI
sentiment API, Next.js portal, Spring Boot inventory), an animated loading screen driven by the live `progress` events
(plan, each search, each report section, an elapsed clock, a progress bar), and a result view with the seven sections,
clickable `[S1]` citations, the sources, how the research went, and Copy / Download as Markdown.

Three terminals (the model is served by the Ollama app, which must be running):

```powershell
# 1. the API (this folder)
uv run uvicorn app.main:app --reload

# 2. the front end
cd ..\freelance2
npm.cmd install        # first time only
npm.cmd run dev
```

Then open http://localhost:8766 and click the **Freelance Advisor** triangle (the leftmost one). The front end
reaches the API through the dev server's `/advisor` proxy (`vite.config.js`), so no CORS setup is needed. If the
header badge says **Advisor · Offline**, the API terminal is not running. Closing the dialog while a run is going does
not stop it: a pill at the bottom left of the gallery shows the elapsed time and re-opens the dialog; the finished
guide is kept for the browser tab until you press **New research**.

## Example projects to try

The agent is not limited to Python or machine learning. Replace the text in any command above with one of these:

| Project text | What you should see |
|---|---|
| `Build a cross-platform mobile app with Flutter to track daily habits, with reminders and local notifications.` | No dataset search (nothing to train); GitHub examples, web search (found `docs.flutter.dev`), then a repository's `pubspec.yaml` read. Verified: 89 s, no Python in the report. |
| `Create an online store with Next.js and Stripe payments for a small clothing brand, with a product catalog, cart and checkout.` | GitHub examples and the Next.js / Stripe documentation; no datasets. |
| `Develop a REST API with Node.js and Express, JWT authentication and a PostgreSQL database for a library management system.` | Repositories with a `package.json`, Express and PostgreSQL documentation. |
| `Build an inventory management backend with Java Spring Boot and MySQL with role-based access.` | Repositories with a `pom.xml` or `build.gradle`, Spring documentation. |
| `Build an in-browser handwritten digit classifier with TensorFlow.js.` | Here the agent should also look for **datasets** (a non-Python project that does need data). |
| `How do I enable CORS in FastAPI?` | A plain question: few tool calls, no GitHub examples. |

## Testing

| What | Command | Needs |
|---|---|---|
| All unit tests (mocked APIs and a scripted fake LLM; a few seconds) | `uv run pytest` | nothing |
| One test file / one test | `uv run pytest tests/test_agent.py` / `uv run pytest tests/test_agent.py::test_iteration_limit_stops_the_loop` | nothing |
| Model connectivity, a plain answer, a real tool call (about 15 s) | `uv run python -m scripts.smoke_ollama` | Ollama + model |
| Each research tool against the real APIs (no LLM) | `uv run python -m scripts.try_tools` | internet (Tavily key for the web tool) |
| Full agent, live, with progress lines, every decision and the final report (about 3 minutes with `qwen3:4b-instruct`, 13-22 with `qwen3:4b`) | `uv run python -m scripts.run_agent "Build a fake news detection system using Python and machine learning."` (use **your own** project text) | Ollama + internet |
| The API end to end | start the server, then `POST /research` as above | Ollama + internet |

| Test file | Covers |
|---|---|
| `test_tools.py` | GitHub (popular-first ranking) / Hugging Face (including the English-first filter) / Tavily (including relevance filtering) response parsing, every error path (401, 404, 422, 429, 432, timeouts, invalid JSON), license normalisation, prompt-injection and URL stripping, tool registry |
| `test_agent.py` | graph routing, the loop, iteration / tool-call / time limits, duplicate detection, unavailable tools, tool exceptions and timeouts, a stalled model, bounded prompts, plan, nudging, early stop, the fallback |
| `test_evaluation.py` | coverage statuses for all eight areas, keyword proxies, repository-reading suggestions, next-step selection |
| `test_report.py` | seven sections and origins, every URL grounded in the ledger, citation removal, claim checking (licenses, counts, source names), evidence-built sections, limitations, model failures, API payload |
| `test_api.py` | endpoints, validation (including refusing a description that names no project), 503 / 429 / 500 handling and lock release, CORS, docs, production wiring |
| `test_config.py` | defaults, overrides, secrets, validation |

## Configuration

Every setting is an environment variable (see `.env.example`). The important ones:

| Variable | Default | Meaning |
|---|---|---|
| `OLLAMA_MODEL` | `qwen3:4b` | Local model. Only Ollama is used. |
| `OLLAMA_NUM_CTX` | `4096` | Context window. 8192 was measured ~25% slower on a 4 GB card. |
| `OLLAMA_NUM_GPU` | `99` | GPU layers. 99 puts the whole model on the GPU (measured 32 vs 17 tok/s); `-1` lets Ollama decide. |
| `OLLAMA_REASONING` | `true` | Keep `true` for `qwen3:4b`: it is a thinking-only build, and `false` leaks the thinking into the answer. |
| `AGENT_MAX_TOKENS` / `PLAN_MAX_TOKENS` / `REPORT_MAX_TOKENS` | `1600` / `2000` / `2000` | Generated-token caps per call, **thinking included**. Too low and the model is cut off with no answer. |
| `MAX_ITERATIONS` / `MAX_TOOL_CALLS` / `MAX_CALLS_PER_ROUND` | `6` / `8` / `2` | Research limits. |
| `MAX_GAP_NUDGES` | `2` | Times the evaluator may send the agent back after it said DONE with gaps open. |
| `RUN_TIMEOUT_SECONDS` | `1800` | Whole run. Research stops at 50% of it so the report can still be written. |
| `TOOL_TIMEOUT_SECONDS` | `20` | Per HTTP request and per tool call. |
| `DATASET_LANGUAGE` | `en` | `en` leaves out datasets tagged for, or named after, another language (unless the query names one); `any` turns the filter off. |
| `WEB_MIN_RELEVANCE` | `0.3` | Tavily results scoring below this are dropped (the two best always stay). |
| `OLLAMA_REQUEST_TIMEOUT` | `300` | Wall-clock limit for one model call, seconds. A stalled call falls back instead of blocking the run. |

## Performance and known limitations

**Choose the model with `OLLAMA_MODEL` / `OLLAMA_REASONING` in `.env`.** Both were measured on the same request
(fake news detection) on an RTX 2050 with 4 GB of VRAM:

| | `qwen3:4b` (thinking-only build) | **`qwen3:4b-instruct` (non-thinking)** |
|---|---|---|
| `.env` | `OLLAMA_MODEL=qwen3:4b`, `OLLAMA_REASONING=true` | `OLLAMA_MODEL=qwen3:4b-instruct`, `OLLAMA_REASONING=false` |
| Full run | **773 to 1,298 s** (13 to 22 min) | **173 s** (about 3 min) |
| Tokens generated per run | 11,000 to 18,000 (about 95% thinking) | 1,697 |
| Calls cut off with no answer | 3 to 5 per run (about half of the model time) | 0 |
| Report sections written | one was missing in several runs | all four |
| Where the time goes | the model thinking | plan 20 s, research turns 50 s, report 95 s, tools 7 s |

- **The thinking build is slow because it thinks, not because of the research.** About 95% of the tokens it
  generates are reasoning, and on some calls it thinks until its token cap whatever the prompt says (a test of three
  wordings failed 6 of 6). The tools take seconds in both cases.
- **The GPU is power-capped on the test laptop** (clock 210-360 of 2100 MHz, "software power cap", Windows
  "Balanced" plan): the thinking model starts at about 30 tok/s and falls to about 14. The non-thinking model ran at
  about 31 tok/s. The laptop's performance mode may help both (not tested).
- **A model that does not think must be told to act.** With the thinking model's closing sentence ("think in at
  most three sentences, then respond") the non-thinking model wrote *"The next step is to find GitHub examples"*
  instead of calling the tool (1 tool call instead of 6). The closing instruction now depends on `OLLAMA_REASONING`.
- **Quality of a 4B model.** Tool choices are usually sensible. Sections B, D, E, F are plausible recommendations
  that can be generic or mis-cite a source. `check_claims` marks statements whose license, download or star count,
  or source name does not match the cited source (`[CHECK: ...]`), but it cannot catch every wrong statement. They
  are labelled model-written and never presented as verified.
- **Coverage evaluation** of architecture, setup and steps is a keyword match over retrieved titles, snippets
  and README excerpts. It names the sources that matched, but it is a proxy, not a judgement of quality.
- **Verified live** (real services, not mocks): Hugging Face (anonymous and with a token), GitHub (with and without
  a token), Tavily web search, and the real HTTP API. Everything else is covered by the unit tests.
- **Hugging Face search** matches dataset *names*; datasets in other languages are left out by default. Licenses are
  often "not stated".
- **GitHub without a token** is limited to 10 searches/min and 60 other requests/hour (an inspection uses about 4).
- One run at a time (the local GPU). Closing the browser tab or pressing "Stop waiting" does not stop the model: the
  server finishes its current step, and a new run is refused (429) until it is done. No database, authentication,
  Docker or RAG, by design.

## Project layout

```
app/
  main.py               FastAPI app: /health, /tools, /research
  config.py             settings (environment / .env)
  agent/                graph.py (wiring), nodes.py, state.py, prompts.py, context.py (bounded prompts,
                        evidence ledger), evaluation.py, report.py, llm.py (Ollama)
  tools/                web_search.py, github_search.py, dataset_search.py, common.py (sanitising, errors)
  schemas/research.py   all data models
scripts/                check_setup, smoke_ollama, try_tools, run_agent
tests/                  unit tests with mocked APIs and a scripted LLM (fakes.py, conftest.py shared)
REPORT.md               the full project report
```
