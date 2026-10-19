# Project report: Agentic Freelance Research & Technical Advisor (Cerebro, Module 7)

This report explains **what was built, in what order, how each part of the code works, what was measured
and tested, which problems were found and fixed, and what is still limited.** It is meant to be read by the
project owner and by anyone evaluating the module. Setup and usage instructions are in [README.md](README.md).

## 1. What was built

A single local AI agent that, given a freelance project description, **researches** how to implement it and
returns a sourced implementation guide. It does not build anything for the freelancer.

- **LLM:** `qwen3:4b` through Ollama (the only model provider; nothing hosted).
- **Orchestration:** LangGraph (`StateGraph` written by hand), LangChain for tool schemas and the Ollama client.
- **Research tools (all real):** web search (Tavily), GitHub repository search, GitHub repository inspection,
  Hugging Face dataset search.
- **API:** FastAPI with `GET /health`, `GET /tools`, `POST /research`.
- **Result of a run:** a seven-section report (A-G), the evidence ledger (every source), the tool execution
  history, the plan, the coverage evaluation and run statistics.
- **Size:** about 3,200 lines of application code, 258 automated tests (about 2,500 lines), four command-line scripts.

## 2. What I did, step by step

### Step 1: Inspect the environment (before writing any application code)

| Check | Result |
|---|---|
| Python | 3.12.12 (uv-managed), project pinned to 3.12 |
| Ollama | 0.31.1, reachable on `http://localhost:11434`, model `qwen3:4b` installed (2.5 GB) |
| Hardware | RTX 2050 with 4096 MiB VRAM (3719 MiB free), i7-12700H, 23.7 GB RAM |
| API keys | none set at the start. The project owner added Tavily, GitHub and Hugging Face keys later; all three were then verified live |

### Step 2: Measure the model before designing around it

I ran throwaway experiments against the real model instead of assuming how it behaves. Findings that shaped
the design:

| Finding | Measurement | Consequence |
|---|---|---|
| `qwen3:4b` is a **thinking-only** build (same Ollama digest as `qwen3:4b-thinking-2507`) | every answer starts with 150-1,500+ thinking tokens | token caps must include thinking; replies can be cut off with no answer |
| `reasoning=False` does **not** disable thinking | thinking text leaked into the answer | use `reasoning=True`; thinking lands in a separate field |
| Tool calling works | correct tool and arguments in all three reasoning modes | no need for a different model |
| Default context split | 4096 ctx: 67% GPU / 33% CPU, 17 tok/s | slow |
| 8192 context | 58% GPU, 13-14 tok/s (~25% slower) | keep 4096 as requested |
| **Forcing all layers on the GPU** (`num_gpu=99`) | **100% GPU, 3.18 GB, 31.8 tok/s** (vs 17.3) | default `OLLAMA_NUM_GPU=99`, about 1.8x faster |
| Structured output | `json_schema` method worked; `function_calling` method ran out of tokens while thinking | use `json_schema` only |

### Step 3: Prepare the project

`uv` project on Python 3.12; dependencies installed and locked (`langgraph`, `langchain`, `langchain-ollama`,
`fastapi`, `uvicorn`, `pydantic-settings`, `python-dotenv`, `huggingface-hub`, `httpx`; dev: `pytest`, `respx`).
`.env.example`, `.gitignore`, `requirements.txt` (exported from the lock file). A Tavily SDK was installed at
first and then **removed** because the Tavily call goes through `httpx`, as the task specified.

### Step 4: Research tools, verified against the real APIs first

Before writing the tool code I checked each API's real behaviour (Tavily from its documentation; GitHub and
Hugging Face by live probes). That revealed details that the code depends on:

- GitHub without a token: search 10 requests/min, other endpoints 60/hour. Missing repo gives 404, empty query 422.
- Hugging Face anonymous access works; the license can be a string, a list or `None`; descriptions are full of
  whitespace noise; `search` matches substrings of dataset names.
- Tavily: `POST /search`, `Authorization: Bearer`, error codes 401, 429 (with `Retry-After`), 432/433 (plan limits).

### Step 5: The agent loop, evaluation and report

Built in layers, each one tested before the next: state and tool node, then the LLM node, then plan, evaluation
and report nodes, then the API. Several **live runs against the real model and APIs** then exposed weaknesses that
I fixed one by one (section 7); each fix got a regression test.

### Step 6: Tests, scripts, documentation

160 automated tests (section 8), four scripts to try each layer for real, README, this report and `CLAUDE.md`.

## 3. Architecture

```
START -> plan -> agent --tool calls--> tools --> evaluate --gaps and budget left--> agent
                   |                                |
                   +--no tool call (wants to stop)--+--sufficient evidence or a limit hit--> report -> END
```

Why this shape:

- **The LLM decides the research** (which tool, which query, whether to continue). Only `plan` (once, first) and
  `report` (once, last) are fixed steps. There is no hard-coded "web, then GitHub, then Hugging Face" sequence;
  a CORS question and a machine-learning project produce different tool calls.
- **`evaluate` runs after every tool round and whenever the agent tries to stop.** It is deterministic (no LLM),
  so the agent's claim "I'm done" is never accepted as proof.
- **Everything the agent learns lives in the evidence ledger** (`state["sources"]`, ids `S1`, `S2`, ...). The
  report is built from it.

## 4. Code explanation, file by file

### `app/config.py`: settings

A `pydantic-settings` class reading environment variables and the project-root `.env`. Notable details:

```python
model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_ignore_empty=True, extra="ignore")
tavily_api_key: SecretStr | None = None
ollama_num_ctx: int = Field(4096, ge=2048)
ollama_num_gpu: int = Field(99, ge=-1)
```

`env_ignore_empty=True` makes `KEY=` mean "not set". Keys are `SecretStr`, so they never appear in logs or in
`repr()`. `configured_keys()` returns booleans only. Every limit has a validated range.

### `app/schemas/research.py`: the data contract

All models in one file: `EvidenceItem` (one normalised result), `ToolResult` (what every tool returns),
`Source` (an evidence item with an id in the ledger), `ToolExecution` (one row of the history, including
`decided_by: "llm" | "fallback"`), `ResearchPlan`, `CoverageItem` / `Evaluation`, `ReportSection` /
`TechnicalReport`, and the API models. A tool **never raises**: failures are a `ToolResult` with
`ok=False` and an `error.code` from a fixed list (`not_configured`, `rate_limited`, `timeout`, ...).

### `app/tools/common.py`: the safety layer shared by all tools

`sanitize_untrusted(text, max_chars)` is applied to every piece of external text:

```python
text, blocks = _ROLE_BLOCK.subn(f" {REMOVED_MARKER} ", text)   # <system>...</system> blocks, whole
text = _MD_LINK.sub(r"\1", text)                                # keep link text, drop the target
text = _BARE_URL.sub("[link]", text)                            # raw URLs are not sources
...
if _INJECTION.search(segment):                                  # "ignore previous instructions", ...
    kept.append(REMOVED_MARKER)                                 # replace the sentence, flag the item
```

It strips markup, control characters and raw URLs, removes sentences that look like instructions to an AI
assistant, bounds the length, and reports whether anything was removed (`flags=["possible_prompt_injection"]`).
`failure(...)` builds error results; `error_from_exception` maps `httpx` timeouts and network errors to codes;
`retry_after_from_headers` reads `Retry-After` or GitHub's reset time.

### `app/tools/web_search.py`: Tavily over `httpx`

`search_web(query)` validates the query, returns `not_configured` (with the URL where a free key is obtained)
if there is no key, otherwise POSTs to Tavily and maps status codes (401, 429 + `Retry-After`, 432/433, 4xx,
5xx) to error codes. Results are de-duplicated, sanitised and flagged `looks_like_documentation` from the
host/path (`docs.`, `readthedocs`, `/docs`).

### `app/tools/github_search.py`: two tools

- `search_github_repositories(query)`: best-match search, drops forks and archived repositories, keeps stars,
  language, license (`"not stated"` if `null`), topics, last push date, and a `possibly_stale` flag (> 2 years).
- `inspect_github_repository(owner, repo)`: validates names (blocks `../` and slashes), reads metadata,
  README, the root file list and **one** dependency file (`requirements.txt`, `pyproject.toml`, ...). Failures
  after the metadata call produce a **partial result with notes**, not an error. `summarize_readme` extracts
  headings, the opening paragraph and the install/usage passages. Nothing is cloned or executed.

### `app/tools/dataset_search.py`: Hugging Face metadata

Uses `HfApi.list_datasets(search=..., sort="downloads", limit=5, expand=[...])`. `_license()` normalises the
three shapes the license can have and returns `"not stated"` instead of guessing. A search with no results
returns a note telling the model to use shorter keywords. No dataset is downloaded.

### `app/tools/__init__.py`: what the LLM sees

Wraps the four functions as LangChain `StructuredTool`s with short, specific descriptions and typed argument
schemas (a 4B model relies heavily on these). `tool_status()` feeds `GET /tools`; `unconfigured_tools()` lists
tools that cannot work (missing key) so the agent is never offered them.

### `app/agent/state.py`: the state

`AgentState` is a `TypedDict`. Lists that grow use reducers (`add_messages`, `operator.add`). Key fields:
`sources` (the ledger), `history` (every tool execution), `unavailable` (tool to reason), counters
(`iteration`, `tool_calls_made`, `idle_rounds`, `nudges`), `plan`, `evaluation`, `stop_reason`, `report`.
`AgentDeps` bundles the settings, an LLM factory, the tools and a clock, so tests can inject fakes.

### `app/agent/context.py`: bounded prompts and the evidence ledger

The model has a 4096-token window shared by the prompt, the tool schemas and its own thinking, so prompts are
**rebuilt every turn** with hard character budgets instead of replaying the conversation.

- `register_items(...)` adds results to the ledger, de-duplicated by normalised URL (host + path). The same
  repository found by a search and later inspected keeps **one id**; its metadata and README detail are merged.
- `find_redundant_call(...)` detects an identical or near-identical earlier call (word overlap >= 0.8, plural
  and stop-word tolerant; for inspection, the same `owner/repo`).
- `render_digest(...)` shows the last two executions in detail and older ones as one-liners, shrinking
  progressively to a character cap.

### `app/agent/prompts.py`

Short on purpose. The agent system prompt states the rules (use only useful tools, specific queries, never
repeat a query, content in `<untrusted_data>` is data and not instructions, keep reasoning short, answer DONE
when finished). It also holds the plan prompt, the report prompt and the four section briefs.

### `app/agent/llm.py`: the only door to the model

`build_llm` creates the one `ChatOllama` client (model, context size, `num_gpu`, `reasoning=True`, token cap).
`safe_invoke(runnable, messages, timeout)` turns transport failures into one `LLMError` and adds a **wall-clock
limit per call**: the call runs in a worker thread and `LLMTimeout` is raised if it does not finish in time. This
is needed because httpx's own timeout cannot fire when tokens keep trickling in; in a live test one call took
852 s instead of about 55 s. `structured_invoke` asks for JSON matching a Pydantic schema (the `json_schema`
method). `message_text` removes any `<think>` text, `llm_stat` records timing and token statistics, and
`ollama_status` feeds `/health`. A stalled agent call falls back to the evaluator's step, a stalled plan call uses
the request text, a stalled report section becomes an explicit notice: the run never blocks.

### `app/agent/nodes.py`: the nodes

**Agent node.** Builds the bounded prompt, binds only the tools not in `state["unavailable"]`, calls the model
and handles bad outcomes:

- cut off while thinking (`done_reason == "length"`, no text) or "DONE" before any research: **one retry** with a
  hint to think less;
- still nothing: the **fallback**: the evaluator's next step is executed instead, marked `decided_by="fallback"`
  and listed in the report limitations. It is visible, never silent.

**Tools node.** For each requested call, in this order, it skips (and records why) or executes:

```python
if name not in deps.tools:                  -> skipped: invalid_input
elif name in unavailable:                   -> skipped: unavailable
elif made >= settings.max_tool_calls:       -> skipped: budget_exhausted
elif executed_this_round >= max_calls_per_round: -> skipped: budget_exhausted
elif deps.elapsed(state) >= research_deadline(deps): -> skipped: budget_exhausted
elif (previous := find_redundant_call(...)):  -> skipped: duplicate
```

Executed calls run in a worker thread with a timeout (`run_tool_with_timeout`), results are registered in the
ledger, and an error in `{not_configured, auth_failed, quota_exceeded, rate_limited}` disables that tool for the
rest of the run. Every call, executed or skipped, gets a `ToolMessage` so the conversation stays consistent.
The observation text is fenced in `<untrusted_data>`. After the round it computes `stop_reason` from the
limits (`max_tool_calls`, `max_iterations`, `run_timeout`, `no_progress` after two rounds with no new source).

**Plan node.** `with_structured_output(ResearchPlan, method="json_schema")`; two attempts (the second asks for
less thinking); if both fail, a minimal heuristic plan is used and that fact is recorded.

**Evaluate node.**

```python
evaluation = evaluate_coverage(state.get("plan"), state["sources"], state["history"], state["unavailable"])
if reason == "agent_finished":
    can_continue = limit_reason(state, deps) is None and state["nudges"] < deps.settings.max_gap_nudges
    if evaluation.gaps and can_continue:      # the agent stopped but essential areas are still open
        update.update(stop_reason=None, nudges=state["nudges"] + 1)
elif reason is None and evaluation.sufficient:
    update["stop_reason"] = "sufficient_evidence"
```

### `app/agent/evaluation.py`: coverage judged from evidence

Eight areas, each `covered`, `weak`, `missing`, `not_applicable` or `unavailable`:

| Area | Covered when |
|---|---|
| requirements | the plan has requirements (labelled "derived by the model, not externally verified") |
| technologies | an official-looking documentation page, or an inspected repo whose dependency file was read |
| datasets | >= 2 datasets, or one with a known license (skipped if the plan says none is needed) |
| github_examples | >= 1 repository (skipped if not needed) |
| architecture, environment_setup, development_steps | a retrieved web page or inspected README whose text matches keywords (install, tutorial, architecture, ...). **A keyword proxy; it names the matching sources.** |
| source_references | >= 3 distinct sources |

Every open gap carries a concrete next action with an example query taken from the plan, for instance
`call search_huggingface_datasets with short keywords such as 'sentiment analysis'`. For the four guidance
areas, when web search is unavailable the action becomes `inspect_github_repository` on the most popular
repository found. A search that keeps failing stops being requested after three attempts, so the loop cannot
chase an impossible gap. `next_suggested_call` (used by the fallback) prefers datasets and repositories over
documentation.

### `app/agent/graph.py`: the wiring

```python
graph.add_edge(START, "plan")
graph.add_edge("plan", "agent")
graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "evaluate": "evaluate"})
graph.add_edge("tools", "evaluate")
graph.add_conditional_edges("evaluate", route_after_evaluate, {"agent": "agent", "report": "report"})
graph.add_edge("report", END)
```

`route_after_agent` sends tool calls to `tools` and anything else (a stop or a limit) to `evaluate`;
`route_after_evaluate` goes to `report` when a `stop_reason` exists, else back to `agent`. That back-edge is the
research loop. `recursion_limit` is set above the explicit limits as a last safety net. A hand-written graph
was used on purpose: LangGraph's `create_react_agent` is deprecated in v1 and hides the loop, and we need our
own budgets, duplicate guard, evidence ids and error handling.

### `app/agent/report.py`: a report that cannot invent sources

- **Sections C and G are built by code** from the ledger (links, stars, downloads, licenses, dates, derived
  advantages and limitations such as "license not stated: check before commercial use" or "possibly stale").
  Nothing in them is written by the model.
- **Section A** is the plan. **Sections B, D, E, F** are four separate, bounded model calls.
- **`clean_generated`** checks the model's text afterwards:

```python
allowed = {normalize_url(source.url) for source in ledger.values()}
...
if host in LOOPBACK_HOSTS or normalize_url(url) in allowed:  return match.group(0)
removed_urls.append(url);  return REMOVED_LINK                # any other URL is removed
kept = [i for i in ids if i in ledger]                        # citations to unknown [S#] are removed
```

  Removals are counted in `report.validation` and listed in the limitations.
- **`check_claims`** goes one step further, because a small model can attach a *real* id to a *wrong fact*. In a
  live run a sentence named the dataset `sayalaruano/FakeNewsCorpusSpanish` next to `[S4]`, and S4 was a different
  dataset. For every sentence that cites sources it checks that (1) a license it mentions is the license of a cited
  source (spelling variants such as "Apache License 2.0" / "apache-2.0" are accepted, and a source whose license
  is "not stated" or "unknown" cannot be credited with a specific one), (2) a download or star count equals the
  retrieved count, and (3) a source it names is among the cited ones. A failing sentence is **kept but marked**
  `[CHECK: ...]`, counted in `validation.unverified_claims`, and listed in the limitations.
- Each section carries an `origin` label (`tool_evidence`, `derived_from_request`, `model_recommendation`) and
  the Markdown prints a note saying what that means. Commands in E and F are followed by "not run or tested".
- Time is checked before each model call; a section that cannot be written becomes an explicit notice, so a
  report is always returned. `build_limitations` lists unavailable tools, failed steps, why research stopped,
  uncovered areas, removed injection text and removed links.

### `app/main.py`: the API

`GET /health` (Ollama reachability, model installed, run in progress), `GET /tools`, a synchronous
`POST /research` and its streaming twin `POST /research/stream`. It checks Ollama and the model first (503 with
instructions), allows **one run at a time** through a non-blocking lock (429 otherwise, because one local GPU cannot
serve two runs), validates input (10 to 2,000 characters), maps a model failure to 503 and any other failure to 500,
and always releases the lock. CORS allows the front end's dev server (`http://localhost:8766`) only.

`/research/stream` runs the same checks before it starts streaming, so 422, 503 and 429 stay plain HTTP errors. The
run itself happens in a worker thread that feeds a queue; the response is a Server-Sent Events generator reading that
queue (`progress` events built from the agent's own status lines, then one `result` or `error` event, and a comment
line every 15 s so a quiet model call does not look like a dead connection). The lock is released by the worker, not by
the connection, so it stays held while the GPU is busy even if the browser disconnects.

### `scripts/`

| Script | Purpose |
|---|---|
| `check_setup` | dependencies, config, keys (booleans), Ollama, installed model |
| `smoke_ollama` | real model: connection, plain answer, tool call, GPU placement |
| `try_tools` | each research tool against the real APIs, no LLM |
| `run_agent` | full live run printing every decision, result and the final report |

## 5. Safeguards, mapped to the requirements

| Requirement | Where |
|---|---|
| Maximum iterations and tool calls | `limit_reason`, `Settings.max_iterations / max_tool_calls / max_calls_per_round` |
| Per-tool timeouts | httpx timeouts plus `run_tool_with_timeout` (worker thread) |
| Rate limits, unavailable tools | error codes + `DISABLING_ERRORS`; tool is removed from the model's tool list |
| Repeated or redundant queries | `find_redundant_call`; the model is told "same or near-identical to step N" |
| Bounded context | per-turn prompt rebuild, character budgets, token estimates (tested) |
| Prompt injection | `sanitize_untrusted`, `<untrusted_data>` fencing, system rule, no tool has side effects |
| Failures never faked | errors become observations and report limitations; no result is ever invented |
| A stalled or very slow model | wall-clock limit per model call (`safe_invoke`), then fallback step / request-text plan / explicit notice |
| Wrong facts attached to real sources | `check_claims` compares licenses, download and star counts and source names with the retrieved metadata |
| Verified vs assumed | section origins, `validation`, section G, limitations |

## 6. Live demonstrations (real model, real APIs)

Environment: RTX 2050 4 GB, `qwen3:4b`, `num_ctx=4096`, no Tavily key (web search honestly reported as not
configured), no GitHub token. Request: *"Research how to build a Python sentiment analysis REST API. Find
suitable datasets, useful GitHub examples, relevant documentation, and generate a complete implementation guide."*

**Run 1 (full pipeline, before the fixes below)**: 664 s. The LLM chose `search_huggingface_datasets("sentiment")`,
then, after the evaluator reported GitHub examples as missing, `search_github_repositories("python sentiment
analysis rest api")`. 10 real sources (5 datasets, 5 repositories). The evaluator ended research with
`sufficient_evidence`. The report was complete, every URL came from the ledger, and the limitations said web
search was not configured. It also showed the weaknesses fixed in section 7.

**Run 2 (after adding repository reading to the evaluator)**: 1,298 s. Chain chosen by the LLM:
`search_huggingface_datasets("sentiment analysis")` -> `search_github_repositories("sentiment analysis flask api")`
-> `inspect_github_repository(...)` twice. Section C then contained real README outlines and dependency files.
Two defects appeared and were fixed: research stopped with a **false `no_progress`** (inspecting a known repository
adds detail but no new source id), and the old 1,200 s limit cut section F, which the report then declared
honestly as "could not be generated" (a real test of the time-limit path).

**Run 3 (final code, same request)**: **773 s**, every area covered, complete report. The decisions, as printed
by `scripts.run_agent`:

| Step | Who | What | Evaluator verdict afterwards |
|---|---|---|---|
| plan | LLM (2 attempts) | objective "Python sentiment analysis REST API", needs datasets: yes, GitHub examples: yes | |
| 1 | LLM | `search_huggingface_datasets("sentiment analysis")` -> 5 datasets (S1-S5) | datasets covered; GitHub examples **missing** |
| 2 | LLM | `search_github_repositories("python sentiment analysis rest")` -> 5 repositories (S6-S10) | technologies weak; architecture, setup, steps **missing**: "inspect the most popular repository (S6)" |
| 3 | LLM | `inspect_github_repository("curiousily", "Deploy-BERT-for-Sentiment-Analysis-with-FastAPI")` | technologies, setup, steps covered; architecture **missing**: "inspect S9" |
| 4 | LLM | `inspect_github_repository("arupdas0825", "sentiment-analysis-project")` | all eight areas covered -> `sufficient_evidence` |

So the LLM chose each tool and its arguments, each later choice was made after observing the previous result and the
evaluator's verdict, and research stopped because the **evidence** was sufficient, not because the model said so.
Web search was not available in this run (no key at the time), and the report says so.

Where the time went (from the saved statistics of run 3):

| Part | LLM calls | Time | Output tokens |
|---|---|---|---|
| plan | 2 | 104 s | 2,114 |
| agent (4 turns) | 4 | 167 s | 2,067 |
| report (4 sections, 2 retried) | 6 | 498 s | 6,791 |
| tools (4 real API calls) | none | **3.6 s** | none |

**99% of the run is model time**; the research tools are negligible. At about 14 tok/s (the power-capped GPU) the
report is the largest cost. Excerpts of the resulting report (full text in `scripts.run_agent` output):

- Section C lists S6 with `224 stars; license: MIT; README and setup files were read; dependency file: Pipfile` and
  `possibly stale: last push 2022-12-08`, and dataset S5 with `license: mit` but `757 downloads (little community usage)`.
- Section E: *"Install dependencies via `pip install fastapi uvicorn transformers torch pandas scikit-learn` based on the
  repository examples [S6, S9]"*, a citation to two repositories whose READMEs and dependency files were actually read.
- Section F, phase 1: *"Use Sp1786/multiclass-sentiment-analysis-dataset [S2] as it provides English text-classification
  tasks with Apache-2.0 license and 1350 downloads"*, which matches the metadata returned by Hugging Face.
- Section G lists only URLs returned by tools, and its "not verified" list says web search was not configured.

**Run 4 (the real HTTP API with live web search, fake-news request)**: after the project owner added a Tavily
key, a `POST /research` was sent with `curl` to the owner's own `uvicorn app.main:app --reload` server.
`HTTP 200 in 1,185 s`. The LLM chose: Hugging Face `"fake news"`, GitHub `"fake news detection python"`, web search
(tutorial), web search (architecture and design guide), `inspect_github_repository` of the top repository, and on
turn 6, after the model was cut off twice, the evaluator's fallback step (web search for documentation, labelled
`decided_by: "fallback"` and listed in the limitations). 20 sources: 5 datasets, 5 repositories and **10 real web
pages from Tavily** (newscatcherapi.com, geeksforgeeks.org, medium.com, coursera.org, aws.amazon.com, ...). A
script check confirmed that **all 20 URLs in the report are in the evidence ledger; none is outside it.** Web search
is therefore verified live, not only against mocks.

This run was also the least successful one, and the reasons are instructive:

- The plan failed on both attempts (they hit the 1,200-token cap I had lowered the day before), so the plan fell
  back to the request text. Section E could not be generated and sections D and F were cut off. Lowering the caps
  had made things worse (1,185 s and failures against 773 s and a complete report with the higher caps), so they
  were reverted.
- Reading the report, I found *"Dataset path with verified license (e.g., CC-BY-4.0 for S4)"* next to the name of a
  different dataset: a real id with the wrong dataset name, which the URL and citation checks could not catch. This
  led to `check_claims` (section 4).

**Experiment: can wording stop the runaway thinking?** The model thinks until its token cap on some calls even
though every prompt asks for brief thinking. I tested three closing sentences on the plan prompt that had just
failed, two trials each, cap 1,600 tokens: the current sentence, a firmer one, and the "your previous attempt ran
out of space" retry hint. **All six trials failed** (about 7,500 characters of thinking each). Wording is therefore
not the lever; the model's own behaviour is. One of the six calls also took **852 s instead of about 55 s**, which
the httpx timeout did not stop; this led to the per-call wall-clock limit (`safe_invoke`).

The remaining remedy is a non-thinking model such as `qwen3:4b-instruct` (same family, 2.5 GB), which was **not
pulled** because the task said to use the installed model.

**Run 5 (final code, the real HTTP API again, sentiment-analysis request)**: a first attempt was lost because the
laptop went to sleep during the run (curl reported `HTTP 000 in 11,339 s`); the repeat finished with
**`HTTP 200 in 1,218 s`**. With all three keys active (web search, GitHub token, Hugging Face token):

| Step | Who | What | Result |
|---|---|---|---|
| plan | LLM (retry) | "A Python REST API that classifies sentiment of text", 3 requirements | first attempt hit the token cap, the retry took 21 s |
| 1 | LLM | `search_huggingface_datasets("sentiment")` | 5 datasets (S1-S5) |
| 2 | LLM | `search_web("FastAPI sentiment analysis REST API implementation tutorial step by step")` | 4 pages (S6-S9), including the official FastAPI documentation |
| 3 | LLM | `search_web("FastAPI sentiment analysis setup and dependencies tutorial")` | 4 more pages (S10-S13) |
| 4 | LLM | `inspect_github_repository("mahinuralam", "Fast-API-Sentiment-Analysis")` | README and dependency file read |

The run stopped by `sufficient_evidence` (all applicable areas covered). 13 sources: 5 datasets, 7 web pages, 1
inspected repository. **16 URLs in the report, none outside the evidence ledger; 0 removed links, 0 removed
citations, 0 `[CHECK]` markers.** Section B cites `[S8, S9]` for FastAPI, and those are the official FastAPI
documentation pages. Section F's phases cite `[S6]`, `[S8]`, `[S11]` correctly. Section D could not be written (both
attempts ran to the token cap) and the report says so in its limitations; the other six sections were produced.
Again 99.5% of the time (1,210 of 1,216 s) was model time.

Reading this report showed three more weaknesses, fixed afterwards and checked on the real data of this run:

1. The model's plan said datasets and GitHub examples were **not needed** although the request explicitly asks for
   both. `refine_plan` now overrides a "not needed" when the request's own words ask for them.
2. The plan contained **three invented "technical constraints"** ("No model training required", "Use Python
   framework (e.g., Flask)", "API must be self-contained"). Constraints must be supported by words of the request;
   unsupported ones are removed and reported. Applied to this run's real plan, it removed exactly these three.
3. The official FastAPI tutorial pages were not recognised as documentation (their URLs have no `docs`). The
   heuristic now also looks for `/tutorial`, `/user-guide`, `/getting-started`, `/stable/`, `/latest/`; on this run's
   real web results it newly recognises both FastAPI tutorial pages.

These three fixes have unit tests but were **not** part of a further full live run.

**Runs 6 and 7: the non-thinking model `qwen3:4b-instruct`** (installed by the project owner; same family and size,
2.5 GB; `OLLAMA_REASONING=false`). First a model check (`scripts.smoke_ollama`): a plain answer in 2 tokens (the
thinking model used 151) and a correct tool call in 26 tokens and 4 s (it used 600 to 750 tokens and 36 to 46 s);
100% on the GPU. Then the timed full runs on the owner's request, "Build a fake news detection system using Python
and machine learning.":

- **Run 6: 78 s, but a poor result** (1 tool call, 5 sources). The model answered *"The next step is to find
  open-source GitHub implementations of fake news detection"* in words instead of calling the tool, turn after
  turn, so the evaluator's fallback had to take the first step and research ended with most areas missing. The
  cause was my own prompt: every prompt ended with the sentence written for the thinking model ("think in at most
  three sentences, then respond"), and a model that does not think writes those three sentences as its answer.
  The closing instruction now depends on `OLLAMA_REASONING` (`ACT_NOW`: "call a tool now, do not describe the step").
- **Run 7 (after the fix): 173 s.** Six turns, five tool calls, all chosen by the LLM: Hugging Face datasets, GitHub
  repositories, three web searches. 23 sources (5 datasets, 5 repositories, 13 web pages); all 23 URLs in the report
  are in the evidence ledger; no removed links, no `[CHECK]` markers; all four model-written sections produced
  (section D, which the thinking model often failed to write, included); the roadmap recommends an **English** dataset
  with its license from the Hub metadata (`genesisqu/fake-real-news`, BSD).

| Measured on the same request | `qwen3:4b` (thinking) | `qwen3:4b-instruct` |
|---|---|---|
| Full run | 773 to 1,298 s | **173 s** |
| Tokens generated | 11,000 to 18,000 | **1,697** |
| Calls cut off at the token cap | 3 to 5 per run | **0** |
| Model time by stage (run 7) | plan 104 s, agent 167 s, report 498 s (run 3) | plan 20 s, agent 50 s, report 95 s |
| Tool time | 3.6 to 6.1 s | 7.4 s |
| Speed | 14 to 15 tok/s (power-capped) | about 31 tok/s |

**Reviewing the guide the owner generated (`guide.md`, a run like run 7)** showed that speed was not the only issue.
After the fixes listed as problems 40 to 45 the same request gave (93 s, `qwen3:4b-instruct`):

| | Before (the owner's `guide.md`) | After |
|---|---|---|
| GitHub examples (stars) | 3, 0, 0, 0, 0; none inspected | **639, 151, 132, 119, 74**; two inspected (README and dependencies read) |
| Web sources | 6 of 9 generic "text preprocessing" pages | all about fake news detection (a full-code tutorial, a Medium article, research papers) |
| Section B | cited a dataset for "Python is dominant"; listed licenses and GitHub as technologies | cites a source only where it shows the statement, otherwise (general knowledge) |
| Section D / title / Python | repeated its title / cut mid-word / Python 3.8 | clean / cut at a word / Python 3.10+ |

The quality of the two models' reports was not compared systematically; only the structure, grounding and
completeness above were checked. The non-thinking model is recommended for this hardware.

## 7. Problems found and how they were fixed

| # | Found by | Problem | Fix |
|---|---|---|---|
| 1 | unit test | `<system>...</system>` injection: tag stripping ran **before** the injection check, so the payload text survived | detect and remove role-tag blocks and special tokens first |
| 2 | live probe | `reasoning=False` leaks thinking into the answer | `reasoning=True`, thinking read from a separate field |
| 3 | live probe | `function_calling` structured output runs out of tokens | `json_schema` method only |
| 4 | live probe | Ollama's default GPU split: 17 tok/s | `num_gpu=99`: 32 tok/s, still 3.2 GB |
| 5 | live run | agent turn 4 cut off twice (thinking filled the cap) -> run ended with no decision | one retry with "think less", then the visible evaluator fallback |
| 6 | live run | the plan call hit its token cap twice -> empty plan | larger plan budget (3,000), retry asks for less thinking |
| 7 | live run | with no web key the run stopped after 2 calls: setup/architecture "cannot be researched" | evaluator now directs the agent to read the README and dependency file of the best repository |
| 8 | live run | two of four report sections cut off and re-asked (2.5 min lost) | section cap raised to 2,600 tokens |
| 9 | live run | raw (even truncated) URLs from dataset descriptions appeared in section C | the sanitiser replaces raw URLs |
| 10 | review | model says DONE before any research even after being pushed back | the fallback also covers this case |
| 11 | live server test | `/health` too impatient while Ollama is busy | health timeout raised to 8 s |
| 12 | my own tests | two tests had wrong expectations; one scripted patch wrote bad code and was caught by the tests | corrected; CLAUDE.md warns about inline-script escaping |
| 13 | live run 2 | false `no_progress` stop: inspecting a known repository adds README detail but no new source id | `count_enriched`: a round that adds detail to a known source counts as progress |
| 14 | live run 2 | the plan's objective echoed my prompt ("Analyze freelance project request...") | prompt and schema now say the objective names the software to **build** |
| 15 | live run 2 | "keep your reasoning short" in a system prompt is ignored: first attempts always thought until the token cap (about 190 s wasted, three times) while the retry's firm sentence finished in 40 s | the sentence "Think in at most three sentences, then respond." now ends **every** prompt. It helped in run 3 (773 s) but a later controlled test showed it is **not reliable** (rows 20 and 22); lowering the caps to make runaway attempts cheaper backfired and was reverted |
| 16 | live run 2 | model text contained a title line ("Section E: ...") and a leaked note ("avoided URLs per rules") | `clean_generated` drops title lines and notes about the rules; the prompt forbids them |
| 17 | live run 2 | misleading CLI line: "decision: continue" although the tools node had already set a stop reason | the CLI reads the merged state |
| 18 | measurement | speed halves after about 2 minutes: GPU at 337 of 2100 MHz, throttle reason "software power cap", on AC power with the Balanced plan | documented with the fix (performance mode); I did not change system power settings |
| 19 | first live Tavily call | `learn.microsoft.com/.../quickstart` was not recognised as documentation; scripts printed `?` for non-ASCII text | wider documentation heuristic (hosts, paths, titles) with tests; scripts force UTF-8 |
| 20 | live API run | lowering the token caps made the plan and a report section fail | caps reverted to 1,600 / 2,000 / 2,000 (agent / plan / report) |
| 21 | reading the live report | a real source id attached to another dataset's name (and "GitHub metadata" for a Hugging Face dataset) | `check_claims`: licenses, counts and source names are compared with the cited source's metadata; mismatches are marked `[CHECK]` |
| 22 | wording experiment | no closing sentence stops the runaway thinking (0 of 6 trials) | documented as a model limitation; the evaluator fallback and the retries stay; a non-thinking model is the remedy |
| 23 | wording experiment | one model call took 852 s (normal: about 55 s) and the httpx timeout never fired | wall-clock limit per call in `safe_invoke` and a graceful reaction in the plan, agent and report nodes |
| 24 | live API run | when the plan failed, the fallback plan had no requirements | the fallback now reuses the freelancer's own sentences (first = objective, next ones = requirements) |
| 25 | final live API run | the plan marked datasets and GitHub examples "not needed" although the request asks for them | `refine_plan` overrides it from the request's own words; the override is reported |
| 26 | final live API run | the plan invented technical constraints the request never states | constraints must be supported by words of the request; unsupported ones are removed and reported |
| 27 | final live API run | official FastAPI tutorial pages not recognised as documentation | wider documentation heuristic (`/tutorial`, `/stable/`, `/latest/`, ...) |
| 28 | the final run itself | the laptop went to sleep mid-run; curl returned `HTTP 000 in 11,339 s` | nothing to fix in the code; the run was repeated and succeeded |
| 29 | the project owner's own run | the command in the instructions used the placeholder `"your project"` as the request; the agent first answered (correctly) that the description was missing, was pushed by the "research before DONE" rule, and researched invented topics (full-stack, React) | a deterministic input check refuses a description that names no project (HTTP 422 in the API, exit code 2 in the CLI) before any work is done; the instructions now use a real example |
| 30 | the project owner's own run | the command looked frozen while writing the report: a graph step reports only when it ends, and the report step contains four model calls of 1-2 minutes (5-10 minutes of silence) | every slow model call is announced when it starts and when it ends (`AgentDeps.progress`): printed by the CLI, logged by the API server |
| 31 | reviewing the owner's real report | for an English request, 3 of 5 datasets were Filipino or Spanish (ranked by downloads only) and the roadmap recommended a **Spanish** dataset | the dataset search leaves out datasets tagged for, or named after, another language (reported in a note) unless the query names a language; `DATASET_LANGUAGE=any` turns it off. Checked live: the most downloaded English dataset stays first |
| 32 | same report | dataset languages were not shown in section C | section C shows each dataset's language and flags a non-English one |
| 33 | same report | irrelevant web pages (a CNBC video, a press release) were listed as sources | Tavily results scoring below 0.3 are dropped (the two best always stay), with a note; `WEB_MIN_RELEVANCE` |
| 34 | same report | "looks like documentation" was shown for a tutorial site | reworded: "the URL pattern suggests documentation or a guide (not verified as official)" |
| 35 | same report | the model cited as `(S4)` and `(S7 shows ...)`, which the claim checker did not read | parenthesised citations are cleaned like `[S4]`, and claims are checked wherever an `S#` id appears in a sentence |
| 36 | same report | the model wrote "None" as a technical constraint and the report said it was removed as invented: "None" | "None"-style constraints mean there is none and are dropped silently (this also exposed that the silent drop did not update the plan) |
| 37 | same report | the plan said no GitHub examples were needed for a request to build a system | a request to build something always researches open-source examples; a plain question does not |
| 38 | same report | unfilled dataset-card templates ("TODO: Add YAML tags here") were shown as descriptions | such descriptions are dropped |
| 39 | run with `qwen3:4b-instruct` | the non-thinking model answered "the next step is to find GitHub examples" in words instead of calling the tool (1 tool call, 5 sources), because every prompt ended with the thinking model's "think in at most three sentences, then respond" | the closing instruction depends on `OLLAMA_REASONING`: `BREVITY` for a thinking model, `ACT_NOW` ("call a tool now, do not describe the step") otherwise. Result: 6 tool calls chosen by the model, 173 s |
| 40 | owner's `guide.md` (3-minute run) | 6 of 9 web sources were generic "text preprocessing" pages, none official documentation, none about fake news | the evaluator's example queries came from the plan's FIRST key topic, a sub-step ("Text preprocessing"), and the agent copied them; queries are now built from the project's own words (first sentence of the request) |
| 41 | same guide | all five GitHub examples had 0-8 stars and no license while a 639-star repository existed | the search takes the 30 best matches and returns the five most starred |
| 42 | same guide | after one fruitless web search the agent kept searching the web | the evaluator now points to reading the best repository (README, dependency file) after one web search |
| 43 | same guide | the evaluator asked for "official documentation of the main libraries" without naming one | the hint asks for ONE named library, for example `scikit-learn text classification documentation` |
| 44 | same guide | section B cited a dataset for "Python is dominant" and listed licenses and GitHub as technologies | the brief forbids both and says to write (general knowledge) instead of citing a dataset or repository for a general claim |
| 45 | same guide | section D repeated its own title ("**D. Recommended Architecture**"); the title was cut mid-word; section E advised Python 3.8 | title echoes with a section letter are removed; the title is cut at a word boundary; the brief asks for Python 3.10 or newer |
| 46 | the owner calling the API | the `curl` command in the instructions was Bash-style: pasted into Windows PowerShell 5.1 it sent a broken body (`JSON decode error`, `Could not resolve host: fake`); the server was also not running (`Failed to connect`) | the README now gives a form per shell, verified in PowerShell 5.1 (a real request returned HTTP 200 in 104 s), and lists the three symptoms |
| 47 | preparing a non-Python example | three Python-only assumptions: section E asked for "the Python dependencies" and a virtual environment; repository inspection only knew Python and `package.json` dependency files; setup detection only knew `pip` and `conda` | section E is generic (the project's runtime and package manager); inspection reads `pubspec.yaml`, `composer.json`, `pom.xml`, `build.gradle(.kts)`, `Cargo.toml`, `go.mod`, `Gemfile`, `Package.swift`; setup detection knows npm, yarn, pnpm, Gradle, Maven, Composer, Cargo, Docker. Verified live on a Flutter app: 89 s, no dataset search, the repository's `pubspec.yaml` read, `docs.flutter.dev` found, 0 mentions of Python in the report |
| 48 | the front-end demo (bakery brief: Laravel + Stripe) | the run stopped as `no_progress` after two GitHub searches that returned 0 results ("Laravel cake shop ecommerce admin dashboard" was too narrow), never tried web search, and wrote a guide with **0 sources**. The same happened to a Flutter brief when one GitHub call also failed with a network error | the empty-round limit is 2 only once something was found; while the evidence ledger is empty the agent gets 4 rounds, and from the second empty round the prompt says to use broader keywords or another tool. Verified live: the same bakery brief then found 5 sources in 3 searches |
| 49 | same demo, stop reasons | with every search tool disabled the evaluator reported `sufficient_evidence` (all areas were "covered" because the tools were unavailable) and the old two-round limit had hidden it | no sources plus disabled tools now ends as `no_tools_available`, which the guide's limitations state |
| 50 | the guide text in the browser | removing an unknown citation left a stray space ("a single codebase ." ) | the space before a removed citation is removed with it (and a double space is not left behind) |

## 8. Tests

258 automated tests, no network and no model needed (APIs mocked with `respx`, Hugging Face by patching the
client, the LLM replaced by a scripted fake with three behaviours: tool-calling agent, structured plan, plain
report text). Run with `uv run pytest`.

| Test file | Tests | What it covers |
|---|---|---|
| `test_tools.py` | 82 | Tavily / GitHub / Hugging Face parsing, every error path (401, 404, 422, 429, 432, timeouts, invalid JSON), license normalisation, prompt-injection and URL stripping, documentation detection, tool registry |
| `test_agent.py` | 53 | graph routing, the loop, iteration / tool-call / time limits, the empty-round limit (2 once something was found, 4 while nothing was), duplicate detection, unavailable tools, tool exceptions and timeouts, a stalled model, bounded prompts, plan and its checks, nudging, early stop, the fallback |
| `test_evaluation.py` | 30 | coverage statuses for all eight areas, keyword proxies, repository-reading suggestions, next-step selection |
| `test_report.py` | 48 | seven sections and origins, every URL grounded in the ledger, citation removal, claim checking, evidence-built sections, limitations, model failures, API payload |
| `test_api.py` | 38 | endpoints, validation, 503 / 429 / 500 handling and lock release, CORS, docs, production wiring, the event stream (progress then result, plain 422 / 503 / 429 before streaming, error events, keep-alive) |
| `test_config.py` | 7 | defaults, overrides, secrets, validation |
| **Total** | **258** | all passing; they run in about 5 to 20 seconds |

## 9. Limitations and what is not verified

- **Run time depends on the model, and the choice matters.** With the thinking-only `qwen3:4b` a full run took 11 to 22
  minutes (664, 773, 1,185, 1,298 s): about 95% of its tokens are thinking, and on some calls it thinks until its token
  cap whatever the prompt says (a controlled test failed 6 of 6 trials). With the non-thinking `qwen3:4b-instruct` a
  full run took **173 s** with no cut-off calls. The research tools take seconds in both cases.
- **The comparison is on one request** (fake news detection), and report quality was checked for structure, grounding
  and completeness only, not rated. The dev laptop's GPU is also power-capped (clock 210-360 of 2100 MHz).
- **Quality of a 4B model.** Tool choices are sensible; recommendations in sections B, D, E, F are plausible but can
  be generic or mis-cite a source. `check_claims` catches wrong licenses, counts and source names, but not every
  wrong statement. They are labelled model-written and never presented as verified.
- **Prompts are model-specific.** A prompt sentence that helps a thinking model can break a non-thinking one (row 39).
  If another model is tried, run `scripts.smoke_ollama` and one `scripts.run_agent` and look at the tool choices.
- **Coverage evaluation** of architecture, setup and steps is a keyword proxy, not a judgement of quality.
- **Hugging Face search** matches dataset names only, and licenses are often missing ("not stated").
- **Verified live:** Hugging Face (anonymous and with a token), GitHub (without and with a token), Tavily web search
  and the real HTTP API. Everything else is verified by the unit tests, which use mocks and a scripted LLM.
- **One run at a time**, synchronous API, in-memory only: by design for this prototype (no database, auth, Docker,
  frontend or RAG).

## 10. What you can do next

1. **Use `qwen3:4b-instruct`** (`OLLAMA_MODEL=qwen3:4b-instruct`, `OLLAMA_REASONING=false` in `.env`): measured 173 s
   against 13 to 22 minutes.
2. **Set the laptop to its performance mode** (and Windows "Best performance"): the GPU is power-capped.
3. Start the API (`uv run uvicorn app.main:app --reload`) and try `POST /research` from `/docs`.
4. When the front end is built, add an `/advisor` proxy to `freelance2/vite.config.js` (CORS already allows port 8766).
