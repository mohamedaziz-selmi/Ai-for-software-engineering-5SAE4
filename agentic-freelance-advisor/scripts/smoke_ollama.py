"""Phase 1 check: is the local model reachable, does it answer, and can it make a tool call?

Run from the project root:  uv run python -m scripts.smoke_ollama

Uses the real model, so expect roughly a minute (the first call also loads the model).
Exit code 0 only if all three checks pass.
"""

import sys
import time

from langchain_core.tools import tool

from app.agent.llm import (
    build_llm,
    generation_stats,
    loaded_model_placement,
    message_text,
    ollama_status,
    reasoning_text,
)
from app.config import get_settings

TOOL_PROMPT = (
    "I need to build a fake news detection system with machine learning. "
    "Find suitable datasets for it."
)


@tool
def search_web(query: str) -> str:
    """Search the web for technical documentation, libraries and guides."""
    return "not executed in the smoke test"


@tool
def search_huggingface_datasets(query: str) -> str:
    """Search Hugging Face for datasets. Use short keywords."""
    return "not executed in the smoke test"


def report(name: str, passed: bool, detail: str) -> bool:
    print(f"  {'PASS' if passed else 'FAIL'}  {name}: {detail}")
    return passed


def check_connection() -> bool:
    status = ollama_status()
    if not status["reachable"]:
        return report("connection", False, f"{status['base_url']} unreachable ({status['error']})")
    if not status["model_installed"]:
        return report("connection", False, f"model '{status['model']}' not installed; "
                      f"installed: {status['installed_models']}")
    return report("connection", True, f"{status['base_url']}, model '{status['model']}' installed")


def check_simple_response() -> bool:
    llm = build_llm(num_predict=600)
    start = time.perf_counter()
    message = llm.invoke("Reply with exactly the single word: OK")
    wall = time.perf_counter() - start
    stats = generation_stats(message)
    answer = message_text(message)
    detail = (f"answer={answer!r}, {stats['output_tokens']} tokens at {stats['tokens_per_second']} tok/s, "
              f"thinking={len(reasoning_text(message))} chars, {wall:.0f}s")
    return report("simple response", bool(answer) and "<think>" not in answer, detail)


def check_tool_call() -> bool:
    llm = build_llm(num_predict=1500).bind_tools([search_web, search_huggingface_datasets])
    start = time.perf_counter()
    message = llm.invoke(TOOL_PROMPT)
    wall = time.perf_counter() - start
    stats = generation_stats(message)
    calls = message.tool_calls
    valid = bool(calls) and all(
        call["name"] in {"search_web", "search_huggingface_datasets"}
        and isinstance(call["args"].get("query"), str)
        and call["args"]["query"].strip()
        for call in calls
    )
    shown = ", ".join(f"{call['name']}({call['args']})" for call in calls) or "no tool call"
    detail = (f"{shown} | {stats['output_tokens']} tokens at {stats['tokens_per_second']} tok/s, "
              f"done_reason={stats['done_reason']}, {wall:.0f}s")
    return report("tool call", valid, detail)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the Windows console is cp1252
    settings = get_settings()
    print(f"Model {settings.ollama_model} | num_ctx={settings.ollama_num_ctx} | "
          f"reasoning={settings.ollama_reasoning} | temperature={settings.ollama_temperature}\n")
    if not check_connection():
        return 1
    results = [check_simple_response(), check_tool_call()]
    placement = loaded_model_placement()
    if placement:
        print(f"\nModel placement: {placement}")
    print("\nResult:", "all checks passed" if all(results) else "FAILED")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
