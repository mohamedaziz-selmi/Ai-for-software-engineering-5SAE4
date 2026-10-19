# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Cerebro Module 7: a **single local AI agent** that researches how to implement a freelance technical project (datasets, GitHub repositories, documentation) and returns a sourced implementation guide. It only researches and advises. It never builds, clones, downloads or runs anything. A FastAPI backend, with a front-end screen in the sibling `freelance2/` project, and fully independent of Cerebro Modules 1-6 (no calls to their APIs or databases). README.md has the user-facing setup, endpoint and testing instructions.

Hard constraints from the project owner:
- One agent, not multi-agent. Ollama (`qwen3:4b`) is the only LLM provider; do not use a hosted/paid LLM.
- No RAG, vector DB, database, auth, Docker or fine-tuning. Tools read metadata only: no cloning repositories, no downloading datasets.
- Never fabricate URLs, dataset metadata, versions or test results. Missing information is reported as missing.

The sibling folders in `ai for eng/` are separate projects, not part of this repo: `freelance2/` is the Vite/React Cerebro front end and `langchainProject/` is a scratch sandbox. Don't modify them unless asked. `freelance2/` has the "Freelance Advisor" dialog for this API (the owner asked for it): `src/AdvisorDialog.jsx` (UI, loading screen), `src/advisor-run.js` (an outside-React store that POSTs to `/research/stream` and parses the SSE events), `src/markdown.jsx` (renders the guide without raw HTML), `src/advisor-examples.js` (freelance example briefs), `src/advisor.css`, and a `/advisor` proxy in `vite.config.js` pointing at `127.0.0.1:8000`. The loading screen parses the status lines the agent emits (`[plan]`, `[agent]`, `[tools] ... finished in`, `[evaluate] N source(s)`, `[report] section X written`), so changing those messages in `nodes.py` / `report.py` needs the matching change in `summarizeProgress` (AdvisorDialog.jsx) and the `/research/stream` test.

## Commands

Windows, uv-managed Python 3.12. Run everything from this directory.

```powershell
uv sync                                                # create .venv, install locked deps
uv run python -m scripts.check_setup                   # imports, config, key presence, Ollama
uv run pytest                                          # all unit tests (no network, no model)
uv run pytest tests/test_agent.py::test_iteration_limit_stops_the_loop -v   # single test
uv run pytest -k fallback                              # by keyword
uv run uvicorn app.main:app --reload                   # API; docs at http://127.0.0.1:8000/docs
uv run python -m scripts.smoke_ollama                  # REAL model: answer + tool call + GPU placement
uv run python -m scripts.try_tools                     # each tool against the REAL APIs, no LLM
uv run python -m scripts.run_agent "Build a fake news detection system using Python and machine learning."   # full REAL run (10-20 min); a text that names no project is refused
uv add <package>                                       # then keep requirements.txt in sync:
uv export --no-hashes --no-dev --no-emit-project -o requirements.txt
```

No linter or formatter is configured. `app` is not an installed package: run scripts as modules (`python -m scripts.x`); pytest gets the path from `pythonpath = ["."]`. When a script prints model or API text, call `sys.stdout.reconfigure(encoding="utf-8")` first (the Windows console is cp1252 and crashed on a `≤`).

Tests: `tests/fakes.py` holds `ScriptedLLM` (one object with the three behaviours of the real model: `bind_tools(...).invoke` = agent decisions, `with_structured_output` = the plan, `invoke` = report sections) and in-memory fake tools; import them with `from fakes import ...`. `tests/conftest.py` clears every settings env var for each test, and tests build settings with `make_settings(...)` / `Settings(_env_file=None)` so they never depend on the developer's `.env`. HTTP is mocked with `respx`, Hugging Face by patching `dataset_search.HfApi`.

## Architecture

A hand-written LangGraph `StateGraph` in `app/agent/graph.py` (deliberately not `create_react_agent`, deprecated in LangGraph v1, nor `create_agent`: they hide the loop and we need our own budgets, duplicate guard, evidence ids and error handling).

```
START → plan → agent ──tool calls──▶ tools ──▶ evaluate ──gaps and budget left──▶ agent
                 └──no tool call (wants to stop)──▶ evaluate ──sufficient or limit hit──▶ report → END
```

- **progress**: `AgentDeps.progress` (a `Callable[[str], None]`, `deps.say(...)`) announces each slow model call; the CLI prints it, the API logs it. A graph step only reports when it finishes and the report step holds four model calls, so without it a run looks frozen for minutes.
- **input check** (`check_project_description` in `schemas/research.py`, used by `ResearchRequest` and by `scripts/run_agent`): refuses a text with fewer than two meaningful words (e.g. "your project") before any work. Without it the agent researched invented topics (full-stack, React) for the placeholder.
- **plan** (`nodes.py`): structured output (`ResearchPlan`), then `refine_plan` checks it against the request text (overrides a "no datasets / no examples needed" the request contradicts, drops invented technical constraints; each change goes to `notes` and the report limitations); falls back to a minimal heuristic plan if the model's JSON cannot be parsed, and records that in `notes`.
- **agent**: `ChatOllama.bind_tools(...)` over only the tools not in `state["unavailable"]`. Its prompt is **rebuilt every turn** from the evidence ledger and tool history (`context.py`) with hard character budgets, never from the raw message history, so it always fits the 4096-token window shared with tool schemas and the model's thinking. `messages` is only a record. If the model is cut off twice without a decision, `next_suggested_call` executes the evaluator's next step instead, marked `decided_by="fallback"` in the history and listed in the report limitations.
- **tools**: our own node (not `ToolNode`). Tools return `ToolResult` and never raise. It enforces per-turn cap, total budget, run-time budget, per-call timeout (worker thread), duplicate / near-duplicate detection (`find_redundant_call`), and disables a tool for the rest of the run after `not_configured`, `auth_failed`, `quota_exceeded` or `rate_limited`. Tools known to be unconfigured at start (`unavailable_at_start`) are never offered to the model.
- Example queries in the evaluator's hints are built from the project's own words (`_project_words`: the first sentence of the request), never from the plan's first key topic: that is often a sub-step and the agent copies the hint verbatim. `search_github_repositories` takes the 30 best matches and returns the 5 most starred. After one fruitless web search the evaluator points to reading the best repository.
- **evaluate** (`evaluation.py`): **deterministic, no LLM.** Judges eight areas from the ledger and tool history; architecture/setup/steps are keyword matches over retrieved text (a proxy, and it names the matching sources). Each open gap carries a concrete next action. It sends the agent back if it said DONE with gaps open (up to `MAX_GAP_NUDGES`) and ends research early with `sufficient_evidence`. The agent's own claim of success is never accepted as proof.
- **report** (`report.py`): sections C and G are built by code from the ledger; A is the plan; B, D, E, F are four separate bounded LLM calls whose output is checked twice: `clean_generated` removes every URL not in the ledger (loopback excepted), every `[S#]` that does not exist, stray title lines and leaked notes about the rules; `check_claims` compares a cited sentence's license, download/star counts and named sources with the cited source's metadata and marks mismatches `[CHECK: ...]` (a small model attaches real ids to wrong facts, which URL and id checks cannot see). Each section carries an `origin` label. Before each call the run-time budget is checked; sections that cannot be written become explicit notices, so a report is always returned.

Evidence ledger: every tool result gets an id (`S1`, `S2`, ...) in `state["sources"]`, de-duplicated by URL. The LLM never writes URLs; code resolves ids.

Untrusted content: tool text goes through `sanitize_untrusted` in `tools/common.py` (strips markup, removes instruction-like sentences and chat-role blocks, bounds length), is fenced in `<untrusted_data>`, and the agent system prompt says it is data, never instructions.

Every model call goes through `safe_invoke(..., timeout)` in `llm.py`: a wall-clock limit (`OLLAMA_REQUEST_TIMEOUT`) in a worker thread, because the httpx timeout never fires while tokens trickle in (one call took 852 s instead of ~55 s). `LLMTimeout` makes the agent fall back to the evaluator's step, the plan use the request's own sentences, and a report section become a notice.

Limits (all in `Settings`): `MAX_ITERATIONS`, `MAX_TOOL_CALLS`, `MAX_CALLS_PER_ROUND`, `TOOL_TIMEOUT_SECONDS`, `RUN_TIMEOUT_SECONDS` (research stops at 50% of it, `RESEARCH_TIME_FRACTION`), plus LangGraph's `recursion_limit`. Every run records a `stop_reason`.

API (`app/main.py`): synchronous `POST /research` (a run takes minutes), its Server-Sent Events twin `POST /research/stream` (same checks; the run lives in a worker thread that releases the lock, so a disconnect does not free the GPU early), `GET /health`, `GET /tools`. One run at a time via a non-blocking lock (second request gets 429); Ollama/model are checked up front (503). Production wiring is `get_agent_deps`; tests override it with a fake.

## Gotchas (verified)

- Model choice is in `.env`: `qwen3:4b-instruct` + `OLLAMA_REASONING=false` (measured 173 s per run, 0 cut-offs) or `qwen3:4b` + `true` (773-1,298 s). Prompts end differently per model (`BREVITY` for a thinking model, `ACT_NOW` otherwise, see `prompts.py`): with `BREVITY` the non-thinking model describes the next step in words instead of calling the tool. Code defaults in `config.py` are still `qwen3:4b`/`true`; `.env.example` recommends the instruct model.
- `qwen3:4b` on Ollama has the same digest as `qwen3:4b-thinking-2507-q4_K_M`: a **thinking-only** build. `reasoning=False` does not disable thinking (it leaks into `content`); keep `reasoning=True` so thinking lands in `additional_kwargs["reasoning_content"]`.
- Thinking tokens count toward `num_predict`. If the cap is hit mid-thought the reply is empty (`done_reason="length"`), and on some calls the model thinks until the cap **whatever the prompt says**: a controlled test of three closing sentences (including the firm retry hint) failed 6 of 6 trials, so do not spend time on prompt wording for this. Lowering the caps made runs worse (plan and a section failed); keep `AGENT_MAX_TOKENS`/`PLAN_MAX_TOKENS`/`REPORT_MAX_TOKENS` at 1600/2000/2000. Remedies that work: retries, the evaluator fallback, and a non-thinking model (`qwen3:4b-instruct`, not pulled yet, needs the owner's approval).
- Structured output must use `with_structured_output(..., method="json_schema")` (see `structured_invoke`); the `function_calling` method ran out of tokens while thinking.
- RTX 2050 (4 GB): Ollama's default splits the model 67% GPU / 33% CPU (~17 tok/s); `num_gpu=99` runs 100% on GPU (3.2 GB) at ~32 tok/s. `num_ctx=8192` was ~25% slower. Defaults in `config.py` reflect this.
- Ranked by downloads alone, 3 of 5 `fake news` datasets were Filipino/Spanish. `search_huggingface_datasets` therefore asks for 4x the results and drops datasets tagged for or named after another language (`DATASET_LANGUAGE=en`, off when the query names a language). Tavily results below `WEB_MIN_RELEVANCE` are dropped (best two kept).
- Hugging Face `list_datasets(search=...)` matches substrings of dataset *names*; license can be a string, a list or `None` (normalised in `_license`, otherwise "not stated"); descriptions contain whitespace noise. No `direction` parameter in huggingface_hub 2.x.
- GitHub unauthenticated: search 10/min, core API 60/hour; `inspect_github_repository` costs about 4 core requests. Tavily is called through `httpx` (`POST https://api.tavily.com/search`, Bearer key) and has been verified live (Tavily, GitHub and Hugging Face keys are in `.env`).
- The owner may run `uvicorn app.main:app --reload` on port 8000: it restarts on any `.py` edit and kills an in-flight `/research`, so do not edit Python while such a request is running. It re-reads `.env` only when the process restarts.
- The GPU of the dev laptop is power-capped (337 of 2100 MHz, "software power cap", Balanced plan): speed drops from ~30 to ~14 tok/s after ~2 minutes of load. Full runs take 11-22 minutes.
- Backslash escapes get mangled in inline `python -`/heredoc scripts run through the shell: edit source files with the Edit tool, not scripted string replacement.
- `.env` holds real keys (gitignored). Keys are `SecretStr`; `configured_keys()` and `check_setup` expose only booleans. Never print key values.
