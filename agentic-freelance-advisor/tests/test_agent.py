"""Tests of the research agent graph: routing, loop, limits and safeguards.

The LLM is replaced by a scripted fake and the tools by in-memory fakes, so no model or network is used.
"""

import time
from itertools import chain, count, repeat

import httpx
import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import StructuredTool

from app.agent import nodes
from app.agent.context import (
    estimate_tokens,
    find_redundant_call,
    register_items,
    render_digest,
)
from app.agent.graph import build_graph, graph_config, run_research
from app.agent.llm import LLMError, LLMTimeout, safe_invoke
from app.agent.nodes import build_agent_messages
from app.agent.prompts import BREVITY, BROADEN_HINT, NO_RESEARCH_YET_HINT, SHORT_REASONING_HINT
from app.agent.state import AgentDeps, initial_state
from app.schemas.research import EvidenceItem, ResearchPlan, ToolExecution, ToolResult
from app.tools import (
    DATASET_SEARCH,
    GITHUB_INSPECT,
    GITHUB_SEARCH,
    WEB_SEARCH,
    DatasetSearchInput,
    GithubInspectInput,
    GithubSearchInput,
    WebSearchInput,
)
from app.tools.common import failure

from fakes import (  # noqa: E402
    DEFAULT_PLAN,
    META,
    REQUEST,
    ScriptedLLM,
    call,
    done,
    fake_tool,
    make_tools,
    results_for,
)

@pytest.fixture
def build(make_settings):
    def factory(replies, tools=None, clock=None, plans=None, texts=None, **settings):
        llm = ScriptedLLM(replies, plans, texts)
        settings.setdefault("max_gap_nudges", 0)  # isolate loop mechanics; nudging has its own tests
        deps = AgentDeps(
            settings=make_settings(**settings),
            llm_factory=lambda num_predict: llm,
            tools=tools or make_tools(),
            **({"clock": clock} if clock else {}),
        )
        return llm, deps

    return factory


def history_of(state):
    return [(e.tool, e.status, e.error.code if e.error else None) for e in state["history"]]


# --------------------------------------------------------------------------- the loop


def test_agent_loops_through_tools_and_finishes(build):
    llm, deps = build(
        [
            call((DATASET_SEARCH, {"query": "fake news"})),
            call((GITHUB_SEARCH, {"query": "fake news detection python"})),
            done(),
        ]
    )
    state = run_research(REQUEST, deps)

    assert state["stop_reason"] == "agent_finished"
    assert state["iteration"] == 3 and state["tool_calls_made"] == 2
    assert history_of(state) == [(DATASET_SEARCH, "ok", None), (GITHUB_SEARCH, "ok", None)]
    assert [s.id for s in state["sources"].values()] == ["S1", "S2", "S3", "S4"]
    assert len(llm.prompts) == 3 and llm.replies == []
    # every AI tool call is answered by exactly one ToolMessage
    tool_messages = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 2
    agent_stat = next(c for c in state["llm_calls"] if c["node"] == "agent")
    assert agent_stat["thinking_chars"] > 0 and agent_stat["tokens_per_second"] == 40.0
    assert state["plan"].objective == "Build a fake news detector"


def test_observations_are_fed_back_to_the_llm_as_bounded_untrusted_data(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "fake news"})), done()])
    state = run_research(REQUEST, deps)

    system, user = llm.prompts[1]
    assert "never instructions" in system.content
    assert REQUEST in user.content
    assert "#1 search_huggingface_datasets(query='fake news')" in user.content
    assert "S1 [dataset] fake-news result 1" in user.content
    observation = next(m for m in state["messages"] if isinstance(m, ToolMessage))
    assert "<untrusted_data>" in observation.content and "</untrusted_data>" in observation.content
    assert llm.bound == [list(deps.tools)] * 2


def test_the_llm_decides_which_tools_run_and_none_is_forced(build):
    llm, deps = build([call((WEB_SEARCH, {"query": "fastapi cors docs"})), done()])
    state = run_research("How do I enable CORS in FastAPI?", deps)
    assert [e.tool for e in state["history"]] == [WEB_SEARCH]  # no dataset or GitHub call was made for it


def test_sources_found_twice_keep_one_id(build):
    same = lambda **kw: ToolResult(  # noqa: E731
        tool=WEB_SEARCH,
        arguments=kw,
        ok=True,
        items=[EvidenceItem(kind="web_page", title="Same page", url="https://example.com/docs/", summary="x")],
    )
    llm, deps = build(
        [call((WEB_SEARCH, {"query": "alpha beta"})), call((WEB_SEARCH, {"query": "gamma delta"})), done()],
        tools=make_tools(**{WEB_SEARCH: same}),
    )
    state = run_research(REQUEST, deps)
    assert list(state["sources"]) == ["S1"]
    assert state["sources"]["S1"].found_by == [1, 2]
    assert state["idle_rounds"] == 1  # the second round found nothing new


# --------------------------------------------------------------------------- limits


def test_iteration_limit_stops_the_loop(build):
    llm, deps = build(
        [call((WEB_SEARCH, {"query": f"topic number {i}"})) for i in range(10)], max_iterations=3, max_tool_calls=20
    )
    state = run_research(REQUEST, deps)
    assert state["stop_reason"] == "max_iterations"
    assert state["iteration"] == 3 and len(llm.prompts) == 3
    assert state["tool_calls_made"] == 3  # the last turn's tool call is still executed


def test_tool_call_limit_skips_extra_calls(build):
    llm, deps = build(
        [
            call(
                (WEB_SEARCH, {"query": "first"}),
                (DATASET_SEARCH, {"query": "second"}),
                (GITHUB_SEARCH, {"query": "third"}),
            )
        ],
        max_tool_calls=2,
        max_calls_per_round=5,
    )
    state = run_research(REQUEST, deps)
    assert state["stop_reason"] == "max_tool_calls"
    assert state["tool_calls_made"] == 2
    assert history_of(state)[2] == (GITHUB_SEARCH, "skipped", "budget_exhausted")


def test_per_round_cap(build):
    llm, deps = build(
        [call((WEB_SEARCH, {"query": "one"}), (DATASET_SEARCH, {"query": "two"})), done()], max_calls_per_round=1
    )
    state = run_research(REQUEST, deps)
    assert history_of(state) == [(WEB_SEARCH, "ok", None), (DATASET_SEARCH, "skipped", "budget_exhausted")]


def test_run_stops_when_research_time_is_used_up(build):
    ticks = chain([0.0], repeat(5000.0))
    llm, deps = build([done()], clock=lambda: next(ticks), run_timeout_seconds=100)
    state = run_research(REQUEST, deps)
    assert state["stop_reason"] == "run_timeout"
    assert llm.prompts == []  # the agent was never asked
    # past the total time limit the report is not written by the model either; it says so
    assert llm.report_prompts == []
    assert state["report"].validation.sections_not_generated == ["B", "D", "E", "F"]


def test_no_progress_stops_after_two_idle_rounds_once_something_was_found(build):
    runs = count()

    def one_result_then_nothing(**kw):
        if next(runs) == 0:
            return results_for(WEB_SEARCH, kw["query"], n=1)
        return ToolResult(tool=WEB_SEARCH, arguments=kw, ok=True, notes=["No web results."])

    llm, deps = build(
        [call((WEB_SEARCH, {"query": f"unlucky query {i}"})) for i in range(5)],
        tools=make_tools(**{WEB_SEARCH: one_result_then_nothing}),
        max_iterations=6,
    )
    state = run_research(REQUEST, deps)
    assert len(state["sources"]) == 1
    assert state["stop_reason"] == "no_progress" and state["iteration"] == 3  # one good round, then two empty ones


def test_nothing_found_yet_allows_four_empty_rounds_and_asks_to_broaden(build):
    empty = lambda **kw: ToolResult(tool=WEB_SEARCH, arguments=kw, ok=True, notes=["No web results."])  # noqa: E731
    llm, deps = build(
        [call((WEB_SEARCH, {"query": f"unlucky query {i}"})) for i in range(6)],
        tools=make_tools(**{WEB_SEARCH: empty}),
        max_iterations=6,
    )
    state = run_research(REQUEST, deps)
    assert state["sources"] == {}
    assert state["stop_reason"] == "no_progress" and state["iteration"] == 4
    user_messages = [prompt[1].content for prompt in llm.prompts]
    assert BROADEN_HINT not in user_messages[0]  # nothing has failed yet on the first turn
    assert all(BROADEN_HINT in message for message in user_messages[1:])


def test_a_late_first_result_keeps_the_research_going(build):
    runs = count()

    def finds_something_on_the_third_try(**kw):
        if next(runs) < 2:
            return ToolResult(tool=GITHUB_SEARCH, arguments=kw, ok=True, notes=["No repositories."])
        return results_for(GITHUB_SEARCH, kw["query"])

    llm, deps = build(
        [call((GITHUB_SEARCH, {"query": "very narrow cake shop laravel query"})),
         call((GITHUB_SEARCH, {"query": "laravel bakery shop admin"})),
         call((GITHUB_SEARCH, {"query": "laravel ecommerce"})),
         done()],
        tools=make_tools(**{GITHUB_SEARCH: finds_something_on_the_third_try}),
        max_iterations=6,
    )
    state = run_research(REQUEST, deps)
    assert state["sources"] and state["stop_reason"] != "no_progress"
    assert state["iteration"] >= 4  # the old limit of two empty rounds would have stopped after turn 2


def test_recursion_limit_is_a_backstop_above_the_explicit_limits(build):
    _, deps = build([], max_iterations=6)
    assert graph_config(deps)["recursion_limit"] >= 6 * 3 + 2  # plan + (agent, tools, evaluate) per turn + report


# --------------------------------------------------------------------------- redundancy


def test_repeated_and_near_identical_queries_are_not_executed_again(build):
    llm, deps = build(
        [
            call((DATASET_SEARCH, {"query": "fake news"})),
            call((DATASET_SEARCH, {"query": "Fake  News"}), (DATASET_SEARCH, {"query": "the fake news"})),
            call((GITHUB_SEARCH, {"query": "fake news"})),  # same words, different tool: allowed
            done(),
        ]
    )
    state = run_research(REQUEST, deps)
    assert history_of(state) == [
        (DATASET_SEARCH, "ok", None),
        (DATASET_SEARCH, "skipped", "duplicate"),
        (DATASET_SEARCH, "skipped", "duplicate"),
        (GITHUB_SEARCH, "ok", None),
    ]
    assert state["tool_calls_made"] == 2
    skipped_message = [m for m in state["messages"] if isinstance(m, ToolMessage)][1]
    assert "near-identical to step 1" in skipped_message.content


def test_find_redundant_call_rules():
    def executed(tool, **args):
        return ToolExecution(step=1, tool=tool, arguments=args, status="ok", started_at="t", duration_seconds=0)

    history = [executed(WEB_SEARCH, query="scikit-learn text classification"), executed(GITHUB_INSPECT, owner="A", repo="B")]
    assert find_redundant_call(WEB_SEARCH, {"query": "text classification scikit-learn"}, history)
    assert not find_redundant_call(WEB_SEARCH, {"query": "pytorch image classification"}, history)
    assert find_redundant_call(GITHUB_INSPECT, {"owner": "a", "repo": "b"}, history)
    assert not find_redundant_call(GITHUB_INSPECT, {"owner": "a", "repo": "other"}, history)
    failed = executed(WEB_SEARCH, query="x y z")
    failed.status = "error"
    assert not find_redundant_call(WEB_SEARCH, {"query": "x y z"}, [failed])  # a failed call may be retried


# --------------------------------------------------------------------------- tool failures


def test_missing_configuration_disables_the_tool_and_nothing_is_invented(build):
    broken = lambda **kw: failure(WEB_SEARCH, kw, "not_configured", "TAVILY_API_KEY is not set.")  # noqa: E731
    llm, deps = build(
        [
            call((WEB_SEARCH, {"query": "fastapi docs"})),
            call((WEB_SEARCH, {"query": "uvicorn docs"}), (DATASET_SEARCH, {"query": "news"})),
            done(),
        ],
        tools=make_tools(**{WEB_SEARCH: broken}),
    )
    state = run_research(REQUEST, deps)

    assert history_of(state) == [
        (WEB_SEARCH, "error", "not_configured"),
        (WEB_SEARCH, "skipped", "unavailable"),
        (DATASET_SEARCH, "ok", None),
    ]
    assert state["unavailable"] == {WEB_SEARCH: "not_configured"}
    assert all("fastapi" not in s.title for s in state["sources"].values())  # only real results are kept
    # from the second turn on the model neither sees nor is told it may call the broken tool
    assert WEB_SEARCH not in llm.bound[1]
    assert "UNAVAILABLE TOOLS" in llm.prompts[1][1].content and "not_configured" in llm.prompts[1][1].content


def test_tools_known_to_be_unusable_are_never_offered_to_the_model(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "news"})), done()])
    deps.unavailable_at_start = {WEB_SEARCH: "not_configured"}
    state = run_research(REQUEST, deps)
    assert WEB_SEARCH not in llm.bound[0]
    assert "UNAVAILABLE TOOLS (do not call): search_web (not_configured)" in llm.prompts[0][1].content
    assert [e.tool for e in state["history"]] == [DATASET_SEARCH]


def test_rate_limit_disables_only_that_tool(build):
    limited = lambda **kw: failure(GITHUB_SEARCH, kw, "rate_limited", "GitHub rate limit.", 30)  # noqa: E731
    llm, deps = build(
        [call((GITHUB_SEARCH, {"query": "fake news"})), call((DATASET_SEARCH, {"query": "news"})), done()],
        tools=make_tools(**{GITHUB_SEARCH: limited}),
    )
    state = run_research(REQUEST, deps)
    assert state["unavailable"] == {GITHUB_SEARCH: "rate_limited"}
    assert state["history"][0].error.retry_after_seconds == 30
    assert GITHUB_INSPECT in llm.bound[1] and GITHUB_SEARCH not in llm.bound[1]


def test_github_auth_failure_disables_both_github_tools(build):
    rejected = lambda **kw: failure(GITHUB_SEARCH, kw, "auth_failed", "token rejected")  # noqa: E731
    _, deps = build(
        [call((GITHUB_SEARCH, {"query": "fake news"})), done()], tools=make_tools(**{GITHUB_SEARCH: rejected})
    )
    state = run_research(REQUEST, deps)
    assert set(state["unavailable"]) == {GITHUB_SEARCH, GITHUB_INSPECT}


def test_all_tools_unavailable_ends_the_run(build):
    deny = lambda name: (lambda **kw: failure(name, kw, "not_configured", "no key"))  # noqa: E731
    tools = make_tools(**{name: deny(name) for name in (WEB_SEARCH, GITHUB_SEARCH, GITHUB_INSPECT, DATASET_SEARCH)})
    _, deps = build(
        [call((WEB_SEARCH, {"query": "a b"}), (GITHUB_SEARCH, {"query": "c d"})), call((DATASET_SEARCH, {"query": "e f"}))],
        tools=tools,
        max_calls_per_round=5,
    )
    state = run_research(REQUEST, deps)
    assert state["stop_reason"] == "no_tools_available"  # not "sufficient_evidence": nothing was found, nothing is left to try
    assert state["sources"] == {}


def test_tool_exception_is_contained_and_the_run_continues(build):
    def explode(**kw):
        raise RuntimeError("boom")

    llm, deps = build(
        [call((WEB_SEARCH, {"query": "a b"})), call((DATASET_SEARCH, {"query": "news"})), done()],
        tools=make_tools(**{WEB_SEARCH: explode}),
    )
    state = run_research(REQUEST, deps)
    assert history_of(state)[0] == (WEB_SEARCH, "error", "unexpected")
    assert "boom" in state["history"][0].error.message
    assert history_of(state)[1] == (DATASET_SEARCH, "ok", None)


def test_slow_tool_hits_its_timeout(build, monkeypatch):
    monkeypatch.setattr(nodes, "TOOL_TIMEOUT_GRACE_SECONDS", 0.0)

    def slow(**kw):
        time.sleep(0.6)
        return results_for(WEB_SEARCH, "x y")

    llm, deps = build(
        [call((WEB_SEARCH, {"query": "a b"})), done()], tools=make_tools(**{WEB_SEARCH: slow}), tool_timeout_seconds=0.05
    )
    started = time.perf_counter()
    state = run_research(REQUEST, deps)
    assert time.perf_counter() - started < 0.5  # the run did not wait for the hung call
    assert history_of(state)[0] == (WEB_SEARCH, "error", "timeout")


def test_unknown_tool_and_invalid_arguments_are_rejected_not_executed(build):
    llm, deps = build(
        [call(("delete_everything", {"path": "/"}), (WEB_SEARCH, {"wrong": "argument"}), (DATASET_SEARCH, {"query": "news"})), done()],
        max_calls_per_round=5,
    )
    state = run_research(REQUEST, deps)
    assert history_of(state) == [
        ("delete_everything", "skipped", "invalid_input"),
        (WEB_SEARCH, "error", "invalid_input"),
        (DATASET_SEARCH, "ok", None),
    ]


def test_unreachable_model_raises_one_clear_error(build):
    from app.agent.llm import safe_invoke

    class Down:
        def invoke(self, messages):
            raise httpx.ConnectError("refused")

    with pytest.raises(LLMError, match="Ollama request failed"):
        safe_invoke(Down(), [])
    _, deps = build([httpx.ConnectError("refused")])
    with pytest.raises(LLMError, match="Ollama request failed: ConnectError"):
        run_research(REQUEST, deps)  # the agent node reports it instead of swallowing it


# --------------------------------------------------------------------------- LLM output problems


def test_cut_off_thinking_is_retried_with_a_shorter_hint(build):
    cut_off = AIMessage(content="", response_metadata={**META, "done_reason": "length"})
    llm, deps = build([cut_off, call((DATASET_SEARCH, {"query": "news"})), done()])
    state = run_research(REQUEST, deps)
    assert state["tool_calls_made"] == 1
    assert SHORT_REASONING_HINT in llm.prompts[1][1].content
    assert [c["node"] for c in state["llm_calls"] if c["node"].startswith("agent")][:2] == ["agent", "agent (retry)"]


def test_finishing_before_any_research_is_pushed_back_once(build):
    llm, deps = build([done(), call((DATASET_SEARCH, {"query": "news"})), done()])
    state = run_research(REQUEST, deps)
    assert NO_RESEARCH_YET_HINT in llm.prompts[1][1].content
    assert state["tool_calls_made"] == 1


cut_off = lambda: AIMessage(content="", response_metadata={**META, "done_reason": "length"})  # noqa: E731


def test_two_cut_off_turns_fall_back_to_the_evaluators_next_step_and_say_so(build):
    llm, deps = build([cut_off(), cut_off(), done()])
    state = run_research(REQUEST, deps)

    first = state["history"][0]
    assert first.decided_by == "fallback" and first.tool == DATASET_SEARCH and first.status == "ok"
    assert first.arguments == {"query": "fake news"}  # a starting query taken from the plan's key topics
    assert any("evaluator's suggested step" in note for note in state["notes"])
    assert any("evaluator's suggested step" in item for item in state["report"].limitations)
    # the model is asked again on the next turn and can take over
    assert state["iteration"] == 2 and state["stop_reason"] == "agent_finished"


def test_a_model_that_declines_to_research_is_replaced_by_the_evaluators_step(build):
    llm, deps = build([done(), done(), done()])  # DONE, pushed back, DONE again, then asked once more
    state = run_research(REQUEST, deps)
    assert state["history"][0].decided_by == "fallback" and state["history"][0].tool == DATASET_SEARCH
    assert any("declined to research" in note for note in state["notes"])
    assert NO_RESEARCH_YET_HINT in llm.prompts[1][1].content


def test_without_a_possible_fallback_a_silent_model_ends_the_run_cleanly(build):
    plan = ResearchPlan(objective="Explain CORS", functional_requirements=["x"], technical_constraints=[], assumptions=[],
                        needs_datasets=False, needs_github_examples=False, key_topics=["cors"])
    _, deps = build([cut_off(), cut_off()], plans=[plan])
    deps.unavailable_at_start = {WEB_SEARCH: "not_configured"}
    state = run_research("Explain CORS", deps)
    assert state["stop_reason"] == "agent_no_output" and state["tool_calls_made"] == 0
    assert state["history"] == []


# --------------------------------------------------------------------------- bounded context


def test_prompt_always_fits_the_context_window(build):
    _, deps = build([])
    state = initial_state("x" * 5000, deps)
    sources, history = {}, []
    for step in range(1, 9):
        items = [
            EvidenceItem(kind="repository", title=f"repo-{step}-{i}" * 5, url=f"https://github.com/o/r{step}{i}",
                         summary="a long description " * 30, metadata={"stars": 100, "language": "Python"})
            for i in range(5)
        ]
        sources, ids, _ = register_items(sources, items, step)
        history.append(ToolExecution(step=step, tool=GITHUB_SEARCH, arguments={"query": "q" * 150}, status="ok",
                                     started_at="t", duration_seconds=1, result_count=5, source_ids=ids))
    state.update(sources=sources, history=history, tool_calls_made=8, iteration=7)
    settings = deps.settings

    messages, estimate = build_agent_messages(state, deps, tool_count=4)
    allowed = settings.ollama_num_ctx - settings.agent_max_tokens
    assert estimate <= allowed - nodes.PROMPT_SAFETY_TOKENS
    assert estimate_tokens(messages[0].content + messages[1].content) + 4 * nodes.TOKENS_PER_TOOL_SCHEMA <= allowed


def test_digest_is_bounded_and_prefers_recent_detail():
    sources, history = {}, []
    for step in range(1, 7):
        item = EvidenceItem(kind="dataset", title=f"data-{step}", url=f"https://hf.co/d/{step}", summary="s" * 300,
                            metadata={"downloads": 1, "license": "mit"})
        sources, ids, _ = register_items(sources, [item], step)
        history.append(ToolExecution(step=step, tool=DATASET_SEARCH, arguments={"query": f"q{step}"}, status="ok",
                                     started_at="t", duration_seconds=1, result_count=1, source_ids=ids))
    digest = render_digest(history, sources, max_chars=900)
    assert len(digest) <= 900
    assert "S6 [dataset] data-6" in digest  # the newest result is still detailed
    assert "#1 search_huggingface_datasets(query='q1')" in digest  # older steps are kept as one-liners


# --------------------------------------------------------------------------- plan


def test_plan_is_created_first_and_shown_to_the_agent(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "fake news"})), done()])
    state = run_research(REQUEST, deps)
    assert REQUEST in llm.plan_prompts[0][1].content
    first_prompt = llm.prompts[0][1].content
    assert "PLAN\nObjective: Build a fake news detector" in first_prompt
    assert "Needs datasets: yes. Needs GitHub examples: yes." in first_prompt
    assert state["llm_calls"][0]["node"] == "plan"


def test_plan_falls_back_to_a_minimal_one_when_the_model_output_is_unparsable(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "news"})), done()], plans=[None, None])
    state = run_research(REQUEST, deps)
    plan = state["plan"]
    assert plan.objective.startswith("Build a fake news") and plan.needs_datasets is True  # "machine learning"
    assert plan.functional_requirements == []
    assert len(llm.plan_prompts) == 2  # it asked twice before giving up
    assert any("structured plan" in note for note in state["notes"])
    assert any("structured plan" in item for item in state["report"].limitations)


def test_plan_fields_are_bounded(build):
    huge = ResearchPlan(objective="o" * 900, functional_requirements=["r" * 500] * 9, technical_constraints=["c"] * 9,
                        assumptions=["a"] * 9, needs_datasets=False, needs_github_examples=False, key_topics=["t"] * 12)
    _, deps = build([done(), done(), done()], plans=[huge])  # DONE before research: pushed back, then a fallback step
    plan = run_research(REQUEST, deps)["plan"]
    assert len(plan.objective) <= 220 and len(plan.functional_requirements) == 5
    assert all(len(r) <= 160 for r in plan.functional_requirements)
    assert len(plan.technical_constraints) == 3 and len(plan.assumptions) == 3 and len(plan.key_topics) == 5


# --------------------------------------------------------------------------- evaluation drives the loop


def test_agent_claiming_done_is_not_accepted_while_essential_areas_are_open(build):
    llm, deps = build(
        [call((DATASET_SEARCH, {"query": "fake news"})), done(), call((GITHUB_SEARCH, {"query": "fake news detection"})), done(), done()],
        max_gap_nudges=2,
        max_iterations=8,
    )
    state = run_research(REQUEST, deps)

    assert state["nudges"] == 2 and state["iteration"] == 5
    assert state["stop_reason"] == "agent_finished"  # accepted only after the nudges were used up
    # the agent was told exactly what was still open, before its third turn
    third = llm.prompts[2][1].content
    assert "COVERAGE (computed from the evidence" in third
    assert "- datasets: covered" in third
    assert "- github_examples: MISSING. Next: call search_github_repositories with short keywords such as" in third
    # and the final evaluation still records the gaps that remain (no search_web results exist)
    statuses = {item.area: item.status for item in state["evaluation"].items}
    assert statuses["datasets"] == "covered" and statuses["github_examples"] == "covered"
    assert statuses["technologies"] == "weak" and statuses["environment_setup"] == "missing"
    assert any("Environment setup" in limitation for limitation in state["report"].limitations)


def test_no_nudge_when_the_budget_is_already_spent(build):
    _, deps = build([call((DATASET_SEARCH, {"query": "fake news"})), done()], max_gap_nudges=2, max_iterations=2)
    state = run_research(REQUEST, deps)
    assert state["nudges"] == 0 and state["stop_reason"] == "agent_finished"


def test_research_stops_by_itself_once_the_evidence_is_sufficient(build):
    def web(**kw):
        return ToolResult(tool=WEB_SEARCH, arguments=kw, ok=True, items=[
            EvidenceItem(kind="web_page", title="Docs", url="https://docs.example.com/guide", metadata={"looks_like_documentation": True},
                         summary="Installation guide, tutorial and architecture overview"),
        ])

    llm, deps = build(
        [call((WEB_SEARCH, {"query": "classification docs"}), (DATASET_SEARCH, {"query": "fake news"})),
         call((GITHUB_SEARCH, {"query": "fake news detection"}))],
        tools=make_tools(**{WEB_SEARCH: web}),
        max_gap_nudges=0,
    )
    state = run_research(REQUEST, deps)
    assert state["stop_reason"] == "sufficient_evidence"
    assert state["iteration"] == 2 and llm.replies == []  # the model was not asked a third time
    assert state["evaluation"].sufficient and state["evaluation"].gaps == []


def test_without_web_search_the_agent_is_pointed_at_a_repository_and_stops_once_it_is_read(build):
    def github(**kw):
        return ToolResult(tool=GITHUB_SEARCH, arguments=kw, ok=True, items=[EvidenceItem(
            kind="repository", title="acme/fakenews", url="https://github.com/acme/fakenews", summary="detector",
            metadata={"stars": 50, "license": "MIT"})])

    def inspect(owner, repo):
        return ToolResult(tool=GITHUB_INSPECT, arguments={"owner": owner, "repo": repo}, ok=True, items=[EvidenceItem(
            kind="repository_detail", title="acme/fakenews", url="https://github.com/acme/fakenews", summary="detector",
            detail="README -> Headings: Installation; Usage; Architecture | requirements.txt -> torch, fastapi",
            metadata={"dependency_file": "requirements.txt", "readme_available": True})])

    llm, deps = build(
        [call((DATASET_SEARCH, {"query": "fake news"}), (GITHUB_SEARCH, {"query": "fake news detection"})),
         call((GITHUB_INSPECT, {"owner": "acme", "repo": "fakenews"}))],
        tools=make_tools(**{GITHUB_SEARCH: github, GITHUB_INSPECT: inspect}),
    )
    deps.unavailable_at_start = {WEB_SEARCH: "not_configured"}
    state = run_research(REQUEST, deps)

    assert "inspect_github_repository with owner='acme' and repo='fakenews'" in llm.prompts[1][1].content
    assert state["stop_reason"] == "sufficient_evidence" and state["iteration"] == 2 and llm.replies == []
    assert state["sources"]["S3"].kind == "repository_detail"  # the inspection enriched the existing repository source
    areas = {item.area: item.status for item in state["evaluation"].items}
    assert areas["technologies"] == areas["environment_setup"] == areas["development_steps"] == areas["architecture"] == "covered"
    assert any("TAVILY_API_KEY" in item for item in state["report"].limitations)


def test_plan_retry_asks_for_less_thinking(build):
    plan = DEFAULT_PLAN.model_copy(update={"objective": "Retry worked"})
    llm, deps = build([call((DATASET_SEARCH, {"query": "news"})), done()], plans=[None, plan])
    state = run_research(REQUEST, deps)
    assert state["plan"].objective == "Retry worked" and state["notes"] == []
    assert llm.plan_prompts[0][1].content.endswith(BREVITY)  # every prompt already asks for brief thinking
    assert SHORT_REASONING_HINT not in llm.plan_prompts[0][1].content
    assert SHORT_REASONING_HINT in llm.plan_prompts[1][1].content  # the retry is firmer about it


# --------------------------------------------------------------------------- progress and prompts


def test_every_prompt_ends_with_the_request_for_brief_thinking(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "fake news"})), done()])
    run_research(REQUEST, deps)
    assert llm.plan_prompts[0][1].content.endswith(BREVITY)
    assert all(prompt[1].content.endswith(f"Decide the next step. {BREVITY}") for prompt in llm.prompts)
    assert all(prompt[1].content.endswith(BREVITY) for prompt in llm.report_prompts)


def test_inspecting_known_repositories_counts_as_progress_not_as_an_idle_round(build):
    def github(**kw):
        return ToolResult(tool=GITHUB_SEARCH, arguments=kw, ok=True, items=[
            EvidenceItem(kind="repository", title=f"acme/{name}", url=f"https://github.com/acme/{name}", summary="x", metadata={"stars": 5})
            for name in ("one", "two")])

    def inspect(owner, repo):
        return ToolResult(tool=GITHUB_INSPECT, arguments={"owner": owner, "repo": repo}, ok=True, items=[EvidenceItem(
            kind="repository_detail", title=f"{owner}/{repo}", url=f"https://github.com/{owner}/{repo}", summary="x",
            detail="README -> Intro: a small demo project", metadata={"readme_available": True})])

    llm, deps = build(
        [call((GITHUB_SEARCH, {"query": "fake news detection"})),
         call((GITHUB_INSPECT, {"owner": "acme", "repo": "one"})),
         call((GITHUB_INSPECT, {"owner": "acme", "repo": "two"})),
         done()],
        tools=make_tools(**{GITHUB_SEARCH: github, GITHUB_INSPECT: inspect}),
    )
    state = run_research(REQUEST, deps)
    # no new source id appeared in rounds 2 and 3, but both inspections added README detail: not "no_progress"
    assert state["stop_reason"] == "agent_finished" and state["iteration"] == 4 and llm.replies == []
    assert [e.tool for e in state["history"]] == [GITHUB_SEARCH, GITHUB_INSPECT, GITHUB_INSPECT]
    assert all(s.kind == "repository_detail" for s in state["sources"].values())


# --------------------------------------------------------------------------- a stalled or very slow model


def test_safe_invoke_enforces_a_wall_clock_limit_even_if_the_call_keeps_running():
    class Slow:
        def invoke(self, messages):
            time.sleep(0.6)
            return "late"

    class Fast:
        def invoke(self, messages):
            return "quick"

    class Down:
        def invoke(self, messages):
            raise httpx.ConnectError("refused")

    started = time.perf_counter()
    with pytest.raises(LLMTimeout, match="did not finish within 0s"):
        safe_invoke(Slow(), [], timeout=0.1)
    assert time.perf_counter() - started < 0.5  # it did not wait for the call
    assert safe_invoke(Fast(), [], timeout=5) == "quick"
    assert safe_invoke(Slow(), []) == "late"  # no limit given: plain call
    with pytest.raises(LLMError, match="Ollama request failed: ConnectError"):
        safe_invoke(Down(), [], timeout=5)  # errors inside the worker are re-raised in the caller


def test_a_stalled_agent_call_falls_back_to_the_evaluators_step_without_a_retry(build):
    llm, deps = build([LLMTimeout("stalled"), done()])
    state = run_research(REQUEST, deps)
    first = state["history"][0]
    assert first.decided_by == "fallback" and first.tool == DATASET_SEARCH
    assert any("timed out" in note for note in state["notes"])
    assert len(llm.prompts) == 2  # the stalled call was not retried; the next turn asked the model again


def test_a_stalled_plan_call_uses_the_request_text_without_a_second_attempt(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "news"})), done()], plans=[LLMTimeout("stalled")])
    state = run_research(REQUEST, deps)
    assert len(llm.plan_prompts) == 1
    assert state["plan"].objective.startswith("Build a fake news")
    assert any("the model timed out" in note for note in state["notes"])


def test_a_stalled_report_section_is_reported_not_hidden(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "news"})), done()], texts=[LLMTimeout("stalled"), "D", "E", "F"])
    report = run_research(REQUEST, deps)["report"]
    assert report.validation.sections_not_generated == ["B"]
    assert any("Section B" in item and "stalled" in item for item in report.limitations)


def test_the_fallback_plan_reuses_the_freelancers_own_sentences():
    from app.agent.nodes import heuristic_plan

    plan = heuristic_plan("Build a tool that sorts invoices. It must read PDFs! Give me the steps? Also add tests.")
    assert plan.objective == "Build a tool that sorts invoices."
    assert plan.functional_requirements == ["It must read PDFs!", "Give me the steps?", "Also add tests."]
    assert plan.assumptions == ["The plan could not be produced by the model, so it was derived from the request text only."]
    assert heuristic_plan("single sentence request").functional_requirements == []


# --------------------------------------------------------------------------- the plan is checked against the request


def make_plan(**overrides):
    return DEFAULT_PLAN.model_copy(update=overrides)


def test_the_models_no_datasets_no_examples_is_overridden_when_the_request_asks_for_them():
    from app.agent.nodes import refine_plan

    request = "Research a sentiment API. Find suitable datasets and useful GitHub examples."
    plan, notes = refine_plan(make_plan(needs_datasets=False, needs_github_examples=False), request)
    assert plan.needs_datasets is True and plan.needs_github_examples is True
    assert len(notes) == 2 and "asks for datasets" in notes[0] and "asks for GitHub examples" in notes[1]
    # nothing is forced when the request does not ask: the model's judgement stands
    plan, notes = refine_plan(make_plan(needs_datasets=False, needs_github_examples=False), "How do I enable CORS in FastAPI?")
    assert plan.needs_datasets is False and plan.needs_github_examples is False and notes == []


def test_technical_constraints_the_request_never_states_are_removed_and_reported():
    from app.agent.nodes import refine_plan

    request = "Build a Python REST API. It must run on Windows."
    plan, notes = refine_plan(
        make_plan(technical_constraints=["No model training required", "Use Python framework (e.g., Flask)", "API must be self-contained", "Must run on Windows"]),
        request,
    )
    assert plan.technical_constraints == ["Must run on Windows"]
    assert len(notes) == 1 and "3 technical constraint(s) proposed by the model were removed" in notes[0]
    assert "No model training required" in notes[0] and "Flask" in notes[0]
    untouched, notes = refine_plan(make_plan(technical_constraints=["Python only", "REST API"]), request)
    assert untouched.technical_constraints == ["Python only", "REST API"] and notes == []


def test_the_run_applies_the_corrections_and_shows_them_in_the_report(build):
    wrong = make_plan(needs_datasets=False, needs_github_examples=False, technical_constraints=["No model training required"])
    llm, deps = build([call((DATASET_SEARCH, {"query": "news"})), done()], plans=[wrong])
    state = run_research("Research a news classifier. Find suitable datasets and GitHub examples.", deps)
    assert state["plan"].needs_datasets is True and state["plan"].needs_github_examples is True
    assert state["plan"].technical_constraints == []
    assert any("asks for datasets" in note for note in state["notes"])
    assert any("technical constraint(s) proposed by the model were removed" in item for item in state["report"].limitations)
    areas = {item.area: item.status for item in state["evaluation"].items}
    assert areas["github_examples"] == "missing"  # it is researched now, as the freelancer asked


# --------------------------------------------------------------------------- the run must not look frozen


def test_every_slow_model_call_is_announced_while_the_run_is_in_progress(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "fake news"})), done()])
    messages: list[str] = []
    deps.progress = messages.append
    run_research(REQUEST, deps)

    assert messages[0].startswith("[plan] the model is reading the request")
    assert any(m.startswith("[agent] turn 1: the model is choosing the next step") for m in messages)
    assert any(m.startswith("[agent] turn 2: the model is choosing the next step") for m in messages)
    writing = [m for m in messages if m.startswith("[report] writing section")]
    assert [m.split(" (")[0] for m in writing] == [f"[report] writing section {letter}" for letter in "BDEF"]
    assert [m.split("), ")[1].split(" (")[0] for m in writing] == ["1 of 4", "2 of 4", "3 of 4", "4 of 4"]
    finished = [m for m in messages if m.startswith("[report] section ")]
    assert len(finished) == 4 and all(" written in " in m for m in finished)
    # the order of the announcements follows the order of the work
    assert messages.index(writing[0]) > max(i for i, m in enumerate(messages) if m.startswith("[agent]"))


def test_a_failed_report_section_is_announced_as_not_written(build):
    llm, deps = build([call((DATASET_SEARCH, {"query": "fake news"})), done()], texts=[LLMTimeout("stalled"), "D", "E", "F"])
    messages: list[str] = []
    deps.progress = messages.append
    run_research(REQUEST, deps)
    assert any(m.startswith("[report] section B NOT written") for m in messages)


# --------------------------------------------------------------------------- more plan corrections seen in a real report


def test_a_request_to_build_something_always_researches_open_source_examples():
    from app.agent.nodes import refine_plan

    plan, notes = refine_plan(make_plan(needs_github_examples=False), "Build a fake news detection system using Python and machine learning.")
    assert plan.needs_github_examples is True
    assert notes == ["This is a request to build a project, so open-source examples are researched although the model said they were not needed."]
    for question in ("How do I enable CORS in FastAPI?", "Explain CORS", "What is the best Python web framework"):
        assert refine_plan(make_plan(needs_github_examples=False), question)[0].needs_github_examples is False


def test_none_written_as_a_constraint_means_there_is_none_and_is_not_reported():
    from app.agent.nodes import refine_plan

    plan, notes = refine_plan(make_plan(technical_constraints=["None", "none stated in the request.", "N/A"]), "Build a fake news detector")
    assert plan.technical_constraints == []  # "None" means there is no constraint
    assert not any("technical constraint" in note for note in notes)  # and it is not reported as an invented one


def test_a_model_that_does_not_think_is_told_to_act_instead_of_to_think_briefly(build):
    """qwen3:4b-instruct wrote 'The next step is to find GitHub examples' instead of calling the tool when the
    prompt ended with the thinking model's 'think in at most three sentences, then respond'."""
    from app.agent.prompts import ACT_NOW

    llm, deps = build([call((DATASET_SEARCH, {"query": "fake news"})), done()], ollama_reasoning=False)
    run_research(REQUEST, deps)
    assert BREVITY not in llm.plan_prompts[0][1].content
    assert llm.prompts and all(p[1].content.endswith(f"Decide the next step. {ACT_NOW}") for p in llm.prompts)
    assert all(BREVITY not in p[1].content for p in llm.prompts + llm.report_prompts)
    assert "Do not describe the step in words" in ACT_NOW
