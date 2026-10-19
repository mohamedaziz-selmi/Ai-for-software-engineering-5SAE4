"""Run the research agent from the command line and watch every decision as it happens.

Run from the project root (uses the REAL local model and the REAL research APIs):

    uv run python -m scripts.run_agent "Build a fake news detection system using Python and machine learning."
    uv run python -m scripts.run_agent --max-iterations 4 --save run.json "Research how to build a Python sentiment analysis REST API."
    uv run python -m scripts.run_agent --report-file guide.md "How do I enable CORS in FastAPI?"

Replace the example text with YOUR project. A description that does not say what to build (for example the
placeholder "your project") is refused instead of being researched.

A full run takes several minutes on a laptop GPU: the model thinks before every decision and writes the
report section by section. Shows: the request, the plan, each tool the LLM chose with its arguments, the
results returned by the APIs, the evaluator's coverage verdict after every round, and the final report.
"""

import argparse
import sys
import time
from typing import Any

from app.agent.context import source_line
from app.agent.evaluation import render_coverage
from app.agent.graph import build_graph, graph_config
from app.agent.llm import LLMError, build_llm
from app.agent.report import build_response
from app.agent.state import AgentDeps, initial_state
from app.config import get_settings
from app.schemas.research import check_project_description
from app.tools import build_tools, tool_status, unconfigured_tools

DEFAULT_REQUEST = (
    "Research how to build a Python sentiment analysis REST API. Find suitable datasets, useful GitHub "
    "examples, relevant documentation, and generate a complete implementation guide."
)


def print_llm_calls(update: dict[str, Any]) -> None:
    for stat in update.get("llm_calls", []):
        print(
            f"  [LLM '{stat['node']}'] {stat['seconds']}s, {stat['output_tokens']} tokens "
            f"({stat['tokens_per_second']} tok/s), prompt ~{stat['estimated_prompt_tokens']} tokens (estimated), "
            f"thinking {stat['thinking_chars']} chars, done_reason={stat['done_reason']}"
        )


def print_update(node: str, update: dict[str, Any], sources: dict[str, Any], stop_reason: str | None = None) -> None:
    if node == "plan":
        plan = update["plan"]
        print("\n[plan] the model's reading of the request")
        print_llm_calls(update)
        print(f"  objective: {plan.objective}")
        print(f"  needs datasets: {plan.needs_datasets} | needs GitHub examples: {plan.needs_github_examples}")
        print(f"  requirements: {plan.functional_requirements}")
        print(f"  assumptions: {plan.assumptions} | topics: {plan.key_topics}")
        for note in update.get("notes", []):
            print(f"  NOTE: {note}")
    elif node == "agent":
        print("\n[agent] the LLM decides the next step")
        print_llm_calls(update)
        for stat in update.get("llm_calls", [])[:1]:
            if stat["thinking_tail"]:
                print(f"  end of its reasoning: ...{stat['thinking_tail'][-240:]!r}")
        message = update["messages"][0] if update.get("messages") else None
        if message is not None and message.tool_calls:
            who = "EVALUATOR FALLBACK (the model gave no decision)" if message.additional_kwargs.get("decided_by") == "fallback" else "LLM"
            for tool_call in message.tool_calls:
                print(f"  -> {who} CHOSE TOOL: {tool_call['name']}({tool_call['args']})")
        elif message is not None:
            print(f"  -> LLM chose no tool; it said: {message.content[:80]!r}")
        for note in update.get("notes", []):
            print(f"  NOTE: {note}")
    elif node == "tools":
        for execution in update.get("history", []):
            label = {"ok": "EXECUTED", "error": "FAILED", "skipped": "SKIPPED"}[execution.status]
            print(f"\n[tools] step {execution.step} {label}: {execution.tool}({execution.arguments}) in {execution.duration_seconds}s")
            if execution.error:
                print(f"        {execution.error.code}: {execution.error.message}")
            for source_id in execution.source_ids:
                print(f"        {source_line(sources[source_id], 200)}")
            for note in execution.notes:
                print(f"        note: {note}")
    elif node == "evaluate":
        print("\n[evaluate] coverage judged from the retrieved evidence (no LLM involved)")
        for line in render_coverage(update["evaluation"]).splitlines():
            print(f"  {line}")
        # the stop reason may have been set earlier in the same round (tools node) or by the evaluator itself
        reason = update["stop_reason"] if "stop_reason" in update else stop_reason
        if reason is None:
            print("  -> decision: continue researching" + (" (the agent was sent back)" if "stop_reason" in update else ""))
        else:
            print(f"  -> decision: stop research ({reason}), write the report")
    elif node == "report":
        print("\n[report] writing the technical guide")
        print_llm_calls(update)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("request", nargs="?", default=DEFAULT_REQUEST)
    parser.add_argument("--max-iterations", type=int)
    parser.add_argument("--max-tool-calls", type=int)
    parser.add_argument("--save", help="write the full API-style response (report, sources, history, stats) to this JSON file")
    parser.add_argument("--report-file", help="write the Markdown report to this file")
    args = parser.parse_args()

    problem = check_project_description(args.request)
    if problem:  # e.g. the placeholder "your project": do not let the agent invent a topic
        print(f"Not started. {problem}")
        return 2

    settings = get_settings()
    overrides = {k: v for k, v in {"max_iterations": args.max_iterations, "max_tool_calls": args.max_tool_calls}.items() if v}
    settings = settings.model_copy(update=overrides)
    deps = AgentDeps(
        settings=settings,
        llm_factory=lambda num_predict: build_llm(settings, num_predict=num_predict),
        tools=build_tools(settings),
        unavailable_at_start=unconfigured_tools(settings),
        progress=lambda message: print(message, flush=True),
    )

    print(f"USER REQUEST:\n  {args.request}\n")
    print(f"Model {settings.ollama_model} (num_ctx={settings.ollama_num_ctx}, num_gpu={settings.ollama_num_gpu}) | limits: "
          f"{settings.max_iterations} turns, {settings.max_tool_calls} tool calls, {settings.max_calls_per_round} per turn")
    for tool in tool_status(settings):
        print(f"  tool {tool['name']:<30} {'ready' if tool['configured'] else 'NOT CONFIGURED'} - {tool['note']}")

    graph = build_graph(deps)
    started = time.perf_counter()
    final: dict[str, Any] = {}
    try:
        for mode, chunk in graph.stream(initial_state(args.request, deps), graph_config(deps), stream_mode=["updates", "values"]):
            if mode == "values":
                final = chunk
                continue
            for node, update in chunk.items():
                print_update(node, update, {**final.get("sources", {}), **update.get("sources", {})}, final.get("stop_reason"))
                sys.stdout.flush()
    except LLMError as error:
        print(f"\nERROR: {error}\nIs Ollama running? Try: uv run python -m scripts.smoke_ollama")
        return 2

    response = build_response(final, deps)
    print(f"\n{'=' * 78}\nSTOP REASON: {response.stop_reason} | turns: {response.stats.agent_turns} | tool calls: "
          f"{response.stats.tool_calls_executed} | sources: {len(response.sources)} | {time.perf_counter() - started:.0f}s total")
    print(f"{'=' * 78}\nFINAL REPORT\n{'=' * 78}\n")
    print(response.report.markdown)
    if args.report_file:
        with open(args.report_file, "w", encoding="utf-8") as handle:
            handle.write(response.report.markdown)
        print(f"report written to {args.report_file}")
    if args.save:
        with open(args.save, "w", encoding="utf-8") as handle:
            handle.write(response.model_dump_json(indent=2))
        print(f"full response written to {args.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
