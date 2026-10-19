"""Graph nodes of the research agent: the LLM decision node and the tool execution node."""

import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import ValidationError

from app.agent.context import (
    count_enriched,
    estimate_tokens,
    find_redundant_call,
    register_items,
    render_digest,
    render_observation,
    render_plan,
)
from app.agent.evaluation import evaluate_coverage, next_suggested_call, render_coverage
from app.agent.llm import LLMTimeout, llm_stat, message_text, safe_invoke, structured_invoke
from app.agent.prompts import (
    AGENT_SYSTEM,
    BROADEN_HINT,
    NO_RESEARCH_YET_HINT,
    PLAN_SYSTEM,
    SHORT_REASONING_HINT,
    agent_user_message,
    plan_user_message,
)
from app.agent.report import generate_report
from app.agent.state import AgentDeps, AgentState
from app.schemas.research import ResearchPlan, ToolError, ToolExecution, ToolResult
from app.tools.common import failure, truncate

# Research ends at this share of the run timeout so the report always has time to be written.
RESEARCH_TIME_FRACTION = 0.5
TOOL_TIMEOUT_GRACE_SECONDS = 2.0  # on top of the tool's own per-request timeouts
PROMPT_SAFETY_TOKENS = 150
TOKENS_PER_TOOL_SCHEMA = 120
# Errors after which retrying the same tool during this run would be pointless.
DISABLING_ERRORS = frozenset({"not_configured", "auth_failed", "quota_exceeded", "rate_limited"})
GITHUB_TOOLS = ("search_github_repositories", "inspect_github_repository")


def research_deadline(deps: AgentDeps) -> float:
    return deps.settings.run_timeout_seconds * RESEARCH_TIME_FRACTION


def limit_reason(state: AgentState, deps: AgentDeps) -> str | None:
    """Why research must stop now, or None to continue."""
    settings = deps.settings
    if state["tool_calls_made"] >= settings.max_tool_calls:
        return "max_tool_calls"
    if state["iteration"] >= settings.max_iterations:
        return "max_iterations"
    if deps.elapsed(state) >= research_deadline(deps):
        return "run_timeout"
    if state["idle_rounds"] >= idle_round_limit(state):
        return "no_progress"
    return None


def idle_round_limit(state: AgentState) -> int:
    """Empty tool rounds in a row that end the research.

    Two empty rounds after something was found mean the topic is exhausted. While nothing at all has been found the
    queries were most likely too narrow (a live run searched GitHub for "Laravel cake shop ecommerce admin dashboard",
    got 0 results twice and stopped without ever trying web search), so the agent gets more tries to broaden them or
    to switch tools. The turn and tool-call limits still bound the run.
    """
    return 2 if state["sources"] else 4


# ----------------------------------------------------------------------------- agent node


def build_agent_messages(
    state: AgentState, deps: AgentDeps, tool_count: int, extra: str = ""
) -> tuple[list[BaseMessage], int]:
    """The prompt of one agent turn, rebuilt from the ledger so it always fits the context window."""
    settings = deps.settings
    budget = settings.ollama_num_ctx - settings.agent_max_tokens - PROMPT_SAFETY_TOKENS
    fixed = estimate_tokens(AGENT_SYSTEM) + TOKENS_PER_TOOL_SCHEMA * tool_count
    request = truncate(state["request"], 1200)
    digest_chars = 2400
    while True:
        user = agent_user_message(
            request,
            render_digest(state["history"], state["sources"], digest_chars),
            turn=state["iteration"] + 1,
            max_turns=settings.max_iterations,
            calls_used=state["tool_calls_made"],
            max_calls=settings.max_tool_calls,
            unavailable=state["unavailable"],
            plan=render_plan(state["plan"]) if state.get("plan") else "",
            coverage=render_coverage(state["evaluation"]) if state.get("evaluation") else "",
            extra=extra,
            thinking=bool(settings.ollama_reasoning),
        )
        total = fixed + estimate_tokens(user)
        if total <= budget or digest_chars <= 400:
            return [SystemMessage(content=AGENT_SYSTEM), HumanMessage(content=user)], total
        digest_chars = int(digest_chars * 0.75)


def _retry_hint(reply: AIMessage, state: AgentState) -> str | None:
    if reply.tool_calls:
        return None
    truncated = (reply.response_metadata or {}).get("done_reason") == "length"
    if truncated and not message_text(reply):
        return SHORT_REASONING_HINT  # cut off while thinking, nothing usable came out
    if state["tool_calls_made"] == 0:
        return NO_RESEARCH_YET_HINT  # said DONE before researching anything
    return None


def _fallback_decision(state: AgentState, available: set[str]) -> tuple[str, dict[str, str]] | None:
    evaluation = state.get("evaluation") or evaluate_coverage(
        state.get("plan"), state["sources"], state["history"], state["unavailable"], state["request"]
    )
    return next_suggested_call(evaluation, available, state["history"])


def make_agent_node(deps: AgentDeps):
    def agent_node(state: AgentState) -> dict[str, Any]:
        if deps.elapsed(state) >= research_deadline(deps):
            return {"stop_reason": "run_timeout"}
        available = [tool for name, tool in deps.tools.items() if name not in state["unavailable"]]
        if not available:
            return {"stop_reason": "no_tools_available"}

        nothing_found = BROADEN_HINT if state["idle_rounds"] and not state["sources"] else ""
        messages, estimated_prompt_tokens = build_agent_messages(state, deps, len(available), extra=nothing_found)
        model = deps.llm_factory(deps.settings.agent_max_tokens).bind_tools(available)

        limit = deps.settings.ollama_request_timeout
        stats: list[dict[str, Any]] = []
        timed_out = False
        deps.say(f"[agent] turn {state['iteration'] + 1}: the model is choosing the next step (about 20-120 s) ...")
        started = time.perf_counter()
        try:
            reply = safe_invoke(model, messages, limit)
        except LLMTimeout:
            timed_out, reply = True, AIMessage(content="", response_metadata={"done_reason": "timeout"})
        stats.append(llm_stat("agent", reply, started, estimated_prompt_tokens))
        hint = None if timed_out else _retry_hint(reply, state)
        if hint:
            deps.say("[agent] no usable answer (cut off or declined): asking again with a firmer hint ...")
            retry_messages, estimated = build_agent_messages(state, deps, len(available), extra=hint)
            started = time.perf_counter()
            try:
                reply = safe_invoke(model, retry_messages, limit)
            except LLMTimeout:
                timed_out, reply = True, AIMessage(content="", response_metadata={"done_reason": "timeout"})
            stats.append(llm_stat("agent (retry)", reply, started, estimated))

        text = message_text(reply)
        record = AIMessage(content=text, tool_calls=reply.tool_calls)
        update: dict[str, Any] = {"messages": [record], "iteration": state["iteration"] + 1, "llm_calls": stats}
        if not reply.tool_calls:
            truncated = (reply.response_metadata or {}).get("done_reason") == "length" and not text
            no_decision = timed_out or truncated
            suggestion = None
            refused_to_research = state["tool_calls_made"] == 0  # still no tool call after being pushed back
            if no_decision or refused_to_research:
                suggestion = _fallback_decision(state, {tool.name for tool in available})
            if suggestion:
                # Degraded mode: the model produced no usable decision (twice in a row, or it stalled).
                # Execute the evaluator's next step instead, and say so in the trace and the report.
                tool_name, arguments = suggestion
                why = "timed out" if timed_out else "cut off while thinking" if truncated else "declined to research"
                update["messages"] = [
                    AIMessage(
                        content="",
                        tool_calls=[{"name": tool_name, "args": arguments, "id": f"fallback-{state['iteration'] + 1}", "type": "tool_call"}],
                        additional_kwargs={"decided_by": "fallback"},
                    )
                ]
                update["notes"] = [
                    f"Turn {state['iteration'] + 1}: the model gave no decision ({why}), so the "
                    f"evaluator's suggested step was executed instead: {tool_name}({arguments})."
                ]
            else:
                update["stop_reason"] = "agent_no_output" if no_decision else "agent_finished"
        return update

    return agent_node


# ----------------------------------------------------------------------------- tools node


def run_tool_with_timeout(tool: Any, arguments: dict[str, Any], timeout: float) -> ToolResult:
    """Run one tool in a worker thread so a hung call cannot block the whole run."""
    name = tool.name
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(tool.invoke, arguments)
    try:
        result = future.result(timeout=timeout)
    except FutureTimeout:
        return failure(name, arguments, "timeout", f"{name} did not finish within {timeout:.0f}s.")
    except ValidationError as error:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())
        return failure(name, arguments, "invalid_input", f"Invalid arguments: {truncate(problems, 160)}")
    except Exception as error:  # noqa: BLE001 - a tool must never crash the run
        return failure(name, arguments, "unexpected", f"{type(error).__name__}: {truncate(str(error), 160)}")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    if not isinstance(result, ToolResult):
        return failure(name, arguments, "unexpected", "The tool returned an unexpected result type.")
    return result


def _skipped(step: int, name: str, arguments: dict, code: str, message: str) -> ToolExecution:
    return ToolExecution(
        step=step,
        tool=name,
        arguments=arguments,
        status="skipped",
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        duration_seconds=0.0,
        error=ToolError(code=code, message=message),
    )


def _argument_label(arguments: dict[str, Any]) -> str:
    """The first text argument (the query or the repository name), short enough for a status line."""
    for value in arguments.values():
        if isinstance(value, str) and value.strip():
            return truncate(value.strip(), 70)
    return "no arguments"


def make_tools_node(deps: AgentDeps):
    settings = deps.settings

    def tools_node(state: AgentState) -> dict[str, Any]:
        last_message = state["messages"][-1]
        calls = last_message.tool_calls
        decided_by = last_message.additional_kwargs.get("decided_by", "llm")
        sources = state["sources"]
        history = list(state["history"])
        unavailable = dict(state["unavailable"])
        made = state["tool_calls_made"]
        tool_messages: list[ToolMessage] = []
        new_executions: list[ToolExecution] = []
        round_progress = 0  # new sources, or known sources that gained detail
        executed_this_round = 0

        for call in calls:
            name, arguments, call_id = call["name"], call.get("args") or {}, call["id"]
            step = len(history) + 1
            execution: ToolExecution | None = None
            result: ToolResult | None = None

            if name not in deps.tools:
                execution = _skipped(step, name, arguments, "invalid_input", f"Unknown tool '{name}'.")
            elif name in unavailable:
                execution = _skipped(step, name, arguments, "unavailable", f"{name} is unavailable: {unavailable[name]}.")
            elif made >= settings.max_tool_calls:
                execution = _skipped(step, name, arguments, "budget_exhausted", "The tool-call limit was reached.")
            elif executed_this_round >= settings.max_calls_per_round:
                execution = _skipped(step, name, arguments, "budget_exhausted", "Too many tool calls in one turn.")
            elif deps.elapsed(state) >= research_deadline(deps):
                execution = _skipped(step, name, arguments, "budget_exhausted", "The research time budget is used up.")
            elif (previous := find_redundant_call(name, arguments, history)) is not None:
                execution = _skipped(
                    step, name, arguments, "duplicate",
                    f"Same or near-identical to step {previous.step}. Use different keywords or another tool.",
                )

            if execution is None:  # the call is allowed: execute it
                started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                started = time.perf_counter()
                timeout = (
                    settings.tool_timeout_seconds * (2 if name == "inspect_github_repository" else 1)
                    + TOOL_TIMEOUT_GRACE_SECONDS
                )
                deps.say(f"[tools] running {name} ({_argument_label(arguments)}) ...")
                result = run_tool_with_timeout(deps.tools[name], arguments, timeout)
                made += 1
                executed_this_round += 1
                previous_ledger = sources
                sources, source_ids, new_ids = register_items(sources, result.items, step)
                round_progress += len(new_ids) + count_enriched(previous_ledger, sources, source_ids)
                execution = ToolExecution(
                    step=step,
                    tool=name,
                    arguments=arguments,
                    status="ok" if result.ok else "error",
                    started_at=started_at,
                    duration_seconds=round(time.perf_counter() - started, 2),
                    result_count=len(result.items),
                    source_ids=source_ids,
                    error=result.error,
                    notes=result.notes,
                    decided_by=decided_by,
                )
                deps.say(
                    f"[tools] {name} finished in {execution.duration_seconds:.0f} s: "
                    + (f"error {result.error.code}" if result.error else f"{len(result.items)} result(s)")
                )
                if result.error and result.error.code in DISABLING_ERRORS:
                    group = GITHUB_TOOLS if name in GITHUB_TOOLS and result.error.code == "auth_failed" else (name,)
                    for member in group:
                        unavailable[member] = result.error.code

            history.append(execution)
            new_executions.append(execution)
            tool_messages.append(
                ToolMessage(content=render_observation(execution, result, sources), tool_call_id=call_id, name=name)
            )

        idle_rounds = 0 if round_progress else state["idle_rounds"] + 1
        update: dict[str, Any] = {
            "messages": tool_messages,
            "sources": sources,
            "history": new_executions,
            "unavailable": unavailable,
            "tool_calls_made": made,
            "idle_rounds": idle_rounds,
        }
        projected = {**state, **update}
        reason = limit_reason(projected, deps)  # type: ignore[arg-type]
        if reason:
            update["stop_reason"] = reason
        return update

    return tools_node


# ----------------------------------------------------------------------------- plan node

_NEEDS_DATA = re.compile(
    r"machine learning|\bml\b|\bmodel\b|classif|detect|predict|\bnlp\b|dataset|train|neural|deep learning|\bai\b|"
    r"sentiment|recommend|vision|\bimage|speech|\bllm\b",
    re.IGNORECASE,
)


def heuristic_plan(request: str) -> ResearchPlan:
    """Fallback when the model cannot produce a plan. Understanding is minimal and says so.

    The freelancer's own sentences are used as they are: the first is the objective, the next ones the
    requirements. No wording is invented.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", request.strip()) if s.strip()]
    return ResearchPlan(
        objective=truncate(sentences[0] if sentences else request, 200),
        functional_requirements=[truncate(s, 160) for s in sentences[1:5]],
        technical_constraints=[],
        assumptions=["The plan could not be produced by the model, so it was derived from the request text only."],
        needs_datasets=bool(_NEEDS_DATA.search(request)),
        needs_github_examples=True,
        key_topics=[],
    )


_ASKS_FOR_DATASETS = re.compile(r"\bdata[- ]?sets?\b|\bcorpus\b|\bcorpora\b|training data", re.IGNORECASE)
_ASKS_FOR_EXAMPLES = re.compile(r"github|repositor|open[- ]source|code examples?|example projects?|sample projects?", re.IGNORECASE)
_IS_QUESTION = re.compile(
    r"\?\s*$|^\s*(?:how|what|why|can|could|does|do|is|are|which|where|when|should|explain|compare|tell)\b", re.IGNORECASE
)
_NO_CONSTRAINT = re.compile(r"^\W*(?:none|n/?a|nothing|no constraints?|not (?:specified|stated|applicable)|none stated.*)\W*$", re.IGNORECASE)
_WEAK_WORDS = frozenset("must should need needs required require using with that this from have been into only also than then they them their".split())


def _stems(text: str) -> set[str]:
    return {word.rstrip("s") for word in re.findall(r"[a-z]{4,}", text.lower()) if word not in _WEAK_WORDS}


def refine_plan(plan: ResearchPlan, request: str) -> tuple[ResearchPlan, list[str]]:
    """Correct the model's plan where the request itself contradicts it. Deterministic, and every change is reported.

    A 4B model sometimes (1) marks datasets or GitHub examples "not needed" although the freelancer asks for
    them, and (2) invents "technical constraints" the request never states. Both are checked against the text.
    """
    notes: list[str] = []
    updates: dict[str, Any] = {}
    if not plan.needs_datasets and _ASKS_FOR_DATASETS.search(request):
        updates["needs_datasets"] = True
        notes.append("The request asks for datasets, so the model's 'no dataset needed' was overridden.")
    if not plan.needs_github_examples:
        if _ASKS_FOR_EXAMPLES.search(request):
            updates["needs_github_examples"] = True
            notes.append("The request asks for GitHub examples, so the model's 'no examples needed' was overridden.")
        elif not _IS_QUESTION.search(request.strip()):
            # A request to BUILD something always benefits from open-source examples; a plain question does not.
            updates["needs_github_examples"] = True
            notes.append("This is a request to build a project, so open-source examples are researched although the model said they were not needed.")

    request_stems = _stems(request)
    kept, dropped = [], []
    for constraint in plan.technical_constraints:
        if _NO_CONSTRAINT.match(constraint.strip()):  # the model wrote "None" as a constraint: that means there is none
            continue
        stems = _stems(constraint)
        supported = not stems or len(stems & request_stems) / len(stems) >= 0.5
        (kept if supported else dropped).append(constraint)
    if len(kept) != len(plan.technical_constraints):
        updates["technical_constraints"] = kept
    if dropped:
        notes.append(
            f"{len(dropped)} technical constraint(s) proposed by the model were removed because the request does not "
            f"state them: {'; '.join(dropped)}."
        )
    return (plan.model_copy(update=updates) if updates else plan), notes


def normalize_plan(plan: ResearchPlan) -> ResearchPlan:
    """Bound the size of every field; the plan is re-used in every later prompt."""

    def short(items: list[str], limit: int, width: int) -> list[str]:
        return [truncate(item, width) for item in items if item and item.strip()][:limit]

    return ResearchPlan(
        objective=truncate(plan.objective, 220),
        functional_requirements=short(plan.functional_requirements, 5, 160),
        technical_constraints=short(plan.technical_constraints, 3, 160),
        assumptions=short(plan.assumptions, 3, 160),
        needs_datasets=plan.needs_datasets,
        needs_github_examples=plan.needs_github_examples,
        key_topics=short(plan.key_topics, 5, 60),
    )


def make_plan_node(deps: AgentDeps):
    def plan_node(state: AgentState) -> dict[str, Any]:
        question = plan_user_message(truncate(state["request"], 1200), bool(deps.settings.ollama_reasoning))
        llm = deps.llm_factory(deps.settings.plan_max_tokens)
        stats: list[dict[str, Any]] = []
        plan: ResearchPlan | None = None
        refinements: list[str] = []
        timed_out = False
        deps.say("[plan] the model is reading the request (about 20-100 s) ...")
        for attempt in range(2):
            # the retry asks for less thinking: the first attempt most likely ran out of tokens while thinking
            content = question if attempt == 0 else f"{question}\n\n{SHORT_REASONING_HINT}"
            messages = [SystemMessage(content=PLAN_SYSTEM), HumanMessage(content=content)]
            started = time.perf_counter()
            try:
                parsed, raw, _error = structured_invoke(llm, ResearchPlan, messages, deps.settings.ollama_request_timeout)
            except LLMTimeout:
                timed_out = True  # a stalled model will not do better on a second try: use the fallback plan
                break
            if raw is not None:
                stats.append(llm_stat("plan" if attempt == 0 else "plan (retry)", raw, started, estimate_tokens(PLAN_SYSTEM + state["request"])))
            if isinstance(parsed, ResearchPlan):
                plan, refinements = refine_plan(normalize_plan(parsed), state["request"])
                break
        update: dict[str, Any] = {"llm_calls": stats}
        if plan is not None and refinements:
            update["notes"] = refinements
        if plan is None:
            plan = heuristic_plan(state["request"])
            why = "the model timed out" if timed_out else "the model could not produce a structured plan"
            update["notes"] = [f"The plan came from the request text, not from the model ({why})."]
        update["plan"] = plan
        return update

    return plan_node


# ----------------------------------------------------------------------------- evaluate node


def make_evaluate_node(deps: AgentDeps):
    def evaluate_node(state: AgentState) -> dict[str, Any]:
        """Judge source coverage from the real evidence, then decide whether research continues.

        No LLM is involved: the agent saying "DONE" is not accepted as proof of sufficient research.
        """
        evaluation = evaluate_coverage(state.get("plan"), state["sources"], state["history"], state["unavailable"], state["request"])
        deps.say(
            f"[evaluate] {len(state['sources'])} source(s) collected, "
            + ("coverage is sufficient" if evaluation.sufficient else f"{len(evaluation.gaps)} gap(s) still open")
        )
        update: dict[str, Any] = {"evaluation": evaluation}
        reason = state.get("stop_reason")
        if reason == "agent_finished":
            can_continue = limit_reason(state, deps) is None and state["nudges"] < deps.settings.max_gap_nudges
            if evaluation.gaps and can_continue:  # the agent stopped but essential areas are still open
                update.update(stop_reason=None, nudges=state["nudges"] + 1)
        elif reason is None and evaluation.sufficient:
            # "Covered" only because the tools that would cover it are disabled, and nothing was found: that is not
            # sufficient evidence, there is simply nothing left to try.
            nothing_to_try = not state["sources"] and bool(state["unavailable"])
            update["stop_reason"] = "no_tools_available" if nothing_to_try else "sufficient_evidence"
        return update

    return evaluate_node


# ----------------------------------------------------------------------------- report node


def make_report_node(deps: AgentDeps):
    def report_node(state: AgentState) -> dict[str, Any]:
        report, stats = generate_report(state, deps)
        return {"report": report, "llm_calls": stats}

    return report_node
