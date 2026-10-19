"""Tests of the HTTP API. The model and the research tools are replaced by fakes."""

import json
import time

import httpx
import pytest
from fakes import REQUEST, ScriptedLLM, call, done, make_tools
from fastapi.testclient import TestClient

from app import main
from app.agent.state import AgentDeps
from app.config import Settings, get_settings
from app.schemas.research import ResearchResponse
from app.tools import DATASET_SEARCH, GITHUB_SEARCH

BODY = {"project_description": REQUEST}
HEALTHY = {"base_url": "http://localhost:11434", "model": "qwen3:4b", "reachable": True, "model_installed": True,
           "installed_models": ["qwen3:4b"], "error": None}


@pytest.fixture
def api(monkeypatch, make_settings):
    """A TestClient wired to a scripted model; yields (client, llm, set_status)."""
    settings = make_settings(max_gap_nudges=0)
    llm = ScriptedLLM([call((DATASET_SEARCH, {"query": "fake news"}), (GITHUB_SEARCH, {"query": "fake news detection"})), done()])
    deps = AgentDeps(settings=settings, llm_factory=lambda n: llm, tools=make_tools())
    status = dict(HEALTHY)
    monkeypatch.setattr(main, "ollama_status", lambda s=None, timeout=3.0: dict(status))
    main.app.dependency_overrides[main.get_agent_deps] = lambda: deps
    main.app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(main.app), llm, status
    main.app.dependency_overrides.clear()


def test_health_reports_ollama_and_configuration(api):
    client, _, status = api
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["ollama"]["model"] == "qwen3:4b" and body["ollama"]["reachable"] is True
    assert body["research_running"] is False and body["web_search_configured"] is False
    assert any("TAVILY_API_KEY" in problem for problem in body["problems"])

    status.update(reachable=False, model_installed=False, error="ConnectError: refused")
    degraded = client.get("/health").json()
    assert degraded["status"] == "degraded" and degraded["ollama"]["error"] == "ConnectError: refused"
    assert any("Ollama is not reachable" in problem for problem in degraded["problems"])

    status.update(reachable=True, model_installed=False, error=None)
    assert any("ollama pull qwen3:4b" in p for p in client.get("/health").json()["problems"])


def test_tools_lists_every_tool_with_its_configuration(api):
    client, *_ = api
    tools = {t["name"]: t for t in client.get("/tools").json()}
    assert set(tools) == {"search_web", "search_github_repositories", "inspect_github_repository", "search_huggingface_datasets"}
    assert tools["search_web"]["configured"] is False and "app.tavily.com" in tools["search_web"]["note"]
    assert tools["search_huggingface_datasets"]["configured"] is True and tools["search_huggingface_datasets"]["description"]


def test_research_returns_report_sources_and_tool_history(api):
    client, llm, _ = api
    response = client.post("/research", json=BODY)
    assert response.status_code == 200
    result = ResearchResponse.model_validate(response.json())

    assert [s.id for s in result.report.sections] == list("ABCDEFG")
    assert [e.tool for e in result.tool_history] == [DATASET_SEARCH, GITHUB_SEARCH]
    assert result.tool_history[0].arguments == {"query": "fake news"} and result.tool_history[0].status == "ok"
    assert len(result.sources) == 4 and all(s.url.startswith("https://") for s in result.sources)
    assert result.stop_reason == "agent_finished" and result.plan is not None and result.evaluation is not None
    assert result.stats.tool_calls_executed == 2 and result.stats.model == "qwen3:4b"
    assert result.report.markdown.startswith("# Technical implementation guide")
    assert llm.replies == []


@pytest.mark.parametrize(
    "body",
    [{}, {"project_description": "short"}, {"project_description": "x" * 2001}, {"project_description": "   \n  \t   "},
     {"project_description": 12345678901}, {"wrong": "field"}],
)
def test_invalid_requests_are_rejected_before_any_work(api, body):
    client, llm, _ = api
    assert client.post("/research", json=body).status_code == 422
    assert llm.prompts == [] and llm.plan_prompts == []


def test_missing_ollama_or_model_gives_503_with_instructions(api):
    client, _, status = api
    status.update(reachable=False)
    down = client.post("/research", json=BODY)
    assert down.status_code == 503 and "Ollama is not reachable" in down.json()["detail"]
    status.update(reachable=True, model_installed=False)
    missing = client.post("/research", json=BODY)
    assert missing.status_code == 503 and "ollama pull qwen3:4b" in missing.json()["detail"]


def test_a_second_run_is_refused_while_one_is_in_progress(api):
    client, llm, _ = api
    assert main._run_lock.acquire(blocking=False)
    try:
        assert client.get("/health").json()["research_running"] is True
        busy = client.post("/research", json=BODY)
        assert busy.status_code == 429 and "in progress" in busy.json()["detail"] and busy.headers["retry-after"]
        assert llm.plan_prompts == []
    finally:
        main._run_lock.release()
    assert client.post("/research", json=BODY).status_code == 200


def test_model_failure_during_a_run_gives_503_and_releases_the_lock(monkeypatch, api):
    client, llm, _ = api
    llm.replies = [httpx.ConnectError("Ollama died")]
    failed = client.post("/research", json=BODY)
    assert failed.status_code == 503 and "local model failed" in failed.json()["detail"]
    assert main._run_lock.locked() is False


def test_unexpected_errors_give_500_and_release_the_lock(monkeypatch, api):
    client, *_ = api

    def explode(request, deps):
        raise RuntimeError("bug")

    monkeypatch.setattr(main, "run_research", explode)
    failed = client.post("/research", json=BODY)
    assert failed.status_code == 500 and "RuntimeError: bug" in failed.json()["detail"]
    assert main._run_lock.locked() is False


def read_events(response) -> list[tuple[str, dict]]:
    """Parse a text/event-stream body into (event name, data) pairs; comment lines (keep-alives) are skipped."""
    events = []
    for frame in response.text.split("\n\n"):
        lines = [line for line in frame.splitlines() if line and not line.startswith(":")]
        if not lines:
            continue
        name = next(line[len("event: "):] for line in lines if line.startswith("event: "))
        data = next(line[len("data: "):] for line in lines if line.startswith("data: "))
        events.append((name, json.loads(data)))
    return events


def test_stream_sends_live_progress_then_the_same_result_as_research(api):
    client, llm, _ = api
    response = client.post("/research/stream", json=BODY)
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"

    events = read_events(response)
    names = [name for name, _ in events]
    assert names[-1] == "result" and set(names[:-1]) == {"progress"} and names.count("result") == 1

    progress = [data for name, data in events if name == "progress"]
    stages = {entry["stage"] for entry in progress}
    assert {"plan", "agent", "tools", "evaluate", "report"} <= stages
    assert all(entry["message"] and not entry["message"].startswith("[") for entry in progress)
    assert [e["elapsed_seconds"] for e in progress] == sorted(e["elapsed_seconds"] for e in progress)
    assert any(e["stage"] == "tools" and "search_huggingface_datasets" in e["message"] for e in progress)
    assert any(e["stage"] == "report" and "written" in e["message"] for e in progress)

    result = ResearchResponse.model_validate(events[-1][1])
    assert [s.id for s in result.report.sections] == list("ABCDEFG")
    assert [e.tool for e in result.tool_history] == [DATASET_SEARCH, GITHUB_SEARCH]
    assert llm.replies == [] and main._run_lock.locked() is False


@pytest.mark.parametrize("body", [{}, {"project_description": "short"}, {"project_description": "x" * 2001}])
def test_stream_rejects_invalid_requests_with_a_plain_422(api, body):
    client, llm, _ = api
    response = client.post("/research/stream", json=body)
    assert response.status_code == 422 and not response.headers["content-type"].startswith("text/event-stream")
    assert llm.prompts == [] and llm.plan_prompts == []


def test_stream_refuses_before_streaming_when_ollama_is_down_or_busy(api):
    client, llm, status = api
    status.update(reachable=False)
    down = client.post("/research/stream", json=BODY)
    assert down.status_code == 503 and "Ollama is not reachable" in down.json()["detail"]
    status.update(reachable=True)

    assert main._run_lock.acquire(blocking=False)
    try:
        busy = client.post("/research/stream", json=BODY)
        assert busy.status_code == 429 and busy.headers["retry-after"]
        assert llm.plan_prompts == []
    finally:
        main._run_lock.release()


def test_stream_reports_a_model_failure_as_an_error_event_and_releases_the_lock(api):
    client, llm, _ = api
    llm.replies = [httpx.ConnectError("Ollama died")]
    events = read_events(client.post("/research/stream", json=BODY))
    assert events[-1][0] == "error" and "result" not in [name for name, _ in events]
    assert events[-1][1]["status"] == 503 and "local model failed" in events[-1][1]["detail"]
    assert main._run_lock.locked() is False


def test_stream_reports_an_unexpected_error_as_a_500_event(monkeypatch, api):
    client, *_ = api

    def explode(request, deps):
        raise RuntimeError("bug")

    monkeypatch.setattr(main, "run_research", explode)
    events = read_events(client.post("/research/stream", json=BODY))
    assert events[-1][0] == "error" and events[-1][1]["status"] == 500 and "RuntimeError: bug" in events[-1][1]["detail"]
    assert main._run_lock.locked() is False


def test_stream_keeps_the_connection_alive_while_the_model_is_quiet(monkeypatch, api):
    client, *_ = api
    monkeypatch.setattr(main, "KEEP_ALIVE_SECONDS", 0.01)

    def slow(request, deps):
        time.sleep(0.2)
        raise RuntimeError("done waiting")

    monkeypatch.setattr(main, "run_research", slow)
    body = client.post("/research/stream", json=BODY).text
    assert ": keep-alive" in body and "event: error" in body


def test_progress_lines_become_structured_events():
    event = main._progress_event("[tools] running search_web (fastapi jwt) ...", started=time.perf_counter())
    assert event["stage"] == "tools" and event["message"] == "running search_web (fastapi jwt) ..."
    plain = main._progress_event("no stage prefix", started=time.perf_counter())
    assert plain["stage"] == "agent" and plain["message"] == "no stage prefix"


def test_cors_allows_the_front_end_dev_server_only(api):
    client, *_ = api
    allowed = client.get("/health", headers={"Origin": "http://localhost:8766"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:8766"
    other = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_interactive_docs_are_available(api):
    client, *_ = api
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/tools", "/research", "/research/stream"} <= set(paths)
    assert "post" in paths["/research"] and "post" in paths["/research/stream"] and "get" in paths["/health"]


def test_default_dependencies_build_the_real_wiring(make_settings):
    """The production dependency wires the four tools, only the Ollama model, and pre-marks unconfigured tools."""
    deps = main.get_agent_deps(make_settings())
    assert set(deps.tools) == {"search_web", "search_github_repositories", "inspect_github_repository", "search_huggingface_datasets"}
    assert deps.unavailable_at_start == {"search_web": "not_configured"}
    assert deps.progress == main.logger.info  # progress lines go to the server log
    model = deps.llm_factory(123)
    assert model.__class__.__name__ == "ChatOllama" and model.num_predict == 123 and model.num_ctx == 4096
    assert model.reasoning is True and model.num_gpu == 99
    configured = main.get_agent_deps(make_settings(tavily_api_key="k"))
    assert configured.unavailable_at_start == {}


# --------------------------------------------------------------------------- a request must describe a project


@pytest.mark.parametrize(
    "text",
    ["your project", "my project please help", "Hello, can you help me please?", "asdf", "a test project idea", "?????? !!!!!! ......"],
)
def test_a_description_that_says_nothing_about_what_to_build_is_refused_before_any_work(api, text):
    client, llm, _ = api
    response = client.post("/research", json={"project_description": text + " " * max(0, 12 - len(text))})
    assert response.status_code == 422
    assert "does not say what to build" in response.json()["detail"][0]["msg"]
    assert llm.plan_prompts == [] and llm.prompts == []  # the model was never called, nothing was researched


@pytest.mark.parametrize(
    "text",
    [
        "Build a fake news detection system using Python and machine learning.",
        "How do I enable CORS in FastAPI?",
        "AI chatbot for customer support",
        "Build a website for my bakery",
        "Convert PDFs to Excel with C++",
    ],
)
def test_real_project_descriptions_are_accepted(api, text):
    from app.schemas.research import check_project_description

    assert check_project_description(text) is None
    client, *_ = api
    assert client.post("/research", json={"project_description": text}).status_code == 200


def test_the_command_line_runner_refuses_a_placeholder_without_touching_the_model(monkeypatch, capsys):
    import sys

    from scripts import run_agent

    monkeypatch.setattr(sys, "argv", ["run_agent", "your project"])
    assert run_agent.main() == 2
    assert "does not say what to build" in capsys.readouterr().out


def test_the_bare_address_sends_a_browser_to_the_documentation(api):
    client, *_ = api
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307) and response.headers["location"] == "/docs"
    assert client.get("/").status_code == 200  # followed: the interactive documentation page
    assert "/" not in client.get("/openapi.json").json()["paths"]  # it is not listed as an API endpoint
