"""FastAPI application: health, tool status and the research endpoint.

Run:  uv run uvicorn app.main:app --reload      then open http://127.0.0.1:8000/docs

POST /research is synchronous. A run takes several minutes on a laptop GPU because the local model
thinks before every decision, so clients must allow a long timeout (the run is capped by RUN_TIMEOUT_SECONDS).
"""

import dataclasses
import json
import logging
import queue
import re
import threading
import time
from collections.abc import Iterator
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from app.agent.graph import graph_config, run_research
from app.agent.llm import LLMError, build_llm, ollama_status
from app.agent.report import build_response
from app.agent.state import AgentDeps
from app.config import Settings, get_settings
from app.schemas.research import HealthResponse, OllamaHealth, ResearchRequest, ResearchResponse, ToolInfo
from app.tools import build_tools, tool_status, unconfigured_tools

logger = logging.getLogger("advisor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Agentic Freelance Research & Technical Advisor",
    version="0.1.0",
    description=(
        "A single local AI agent (Ollama + LangGraph) that researches how to implement a freelance technical "
        "project with Hugging Face, GitHub and web search, then returns a sourced implementation guide. "
        "It only researches and advises: it never downloads, clones, installs or runs anything."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# One local GPU cannot serve two research runs at once, so a second request is refused instead of queued.
_run_lock = threading.Lock()


def get_agent_deps(settings: Settings = Depends(get_settings)) -> AgentDeps:
    """The collaborators of one run. Tests replace this dependency with fakes."""
    return AgentDeps(
        settings=settings,
        llm_factory=lambda num_predict: build_llm(settings, num_predict=num_predict),
        tools=build_tools(settings),
        unavailable_at_start=unconfigured_tools(settings),
        progress=logger.info,
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Opening the bare address in a browser used to show {"detail":"Not Found"}; send people to the documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse, summary="API status and Ollama connectivity")
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    # Ollama answers slowly (about 2.5 s) while it is generating, so allow more than the default 3 s.
    status = ollama_status(settings, timeout=8.0)
    problems: list[str] = []
    if not status["reachable"]:
        problems.append(f"Ollama is not reachable at {status['base_url']}. Start it (the tray app, or `ollama serve`).")
    elif not status["model_installed"]:
        problems.append(f"Model '{status['model']}' is not installed. Run: ollama pull {status['model']}")
    web_configured = settings.tavily_api_key is not None
    if not web_configured:
        problems.append("Web search is not configured (TAVILY_API_KEY); reports will lack documentation sources.")
    ready = status["reachable"] and status["model_installed"]
    return HealthResponse(
        status="ok" if ready else "degraded",
        ollama=OllamaHealth(**status),
        research_running=_run_lock.locked(),
        web_search_configured=web_configured,
        problems=problems,
    )


@app.get("/tools", response_model=list[ToolInfo], summary="Research tools and their configuration status")
def tools(settings: Settings = Depends(get_settings)) -> list[ToolInfo]:
    return [ToolInfo(**entry) for entry in tool_status(settings)]


def _check_ready(request: ResearchRequest, settings: Settings) -> str:
    """Refuse a run that cannot succeed (bad text, Ollama down, model missing) before any work starts."""
    description = request.project_description.strip()
    if len(description) < 10:
        raise HTTPException(status_code=422, detail="project_description must contain at least 10 characters of text.")

    status = ollama_status(settings)
    if not status["reachable"]:
        raise HTTPException(503, f"Ollama is not reachable at {status['base_url']}. Start it and try again.")
    if not status["model_installed"]:
        raise HTTPException(503, f"Model '{status['model']}' is not installed. Run: ollama pull {status['model']}")
    return description


def _take_run_slot() -> None:
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(429, "Another research run is in progress. Try again when it has finished.", headers={"Retry-After": "120"})


@app.post(
    "/research",
    response_model=ResearchResponse,
    summary="Research a freelance project and return the implementation guide",
    responses={
        429: {"description": "Another research run is already in progress."},
        503: {"description": "Ollama or the model is not available."},
    },
)
def research(
    request: ResearchRequest,
    settings: Settings = Depends(get_settings),
    deps: AgentDeps = Depends(get_agent_deps),
) -> ResearchResponse:
    description = _check_ready(request, settings)
    _take_run_slot()
    started = time.perf_counter()
    try:
        logger.info("research started (%d chars, model %s)", len(description), settings.ollama_model)
        state = run_research(description, deps)
        response = build_response(state, deps)
        logger.info(
            "research finished: stop_reason=%s turns=%d tool_calls=%d sources=%d in %.0fs",
            response.stop_reason, response.stats.agent_turns, response.stats.tool_calls_executed,
            len(response.sources), time.perf_counter() - started,
        )
        return response
    except LLMError as error:
        logger.error("research failed: %s", error)
        raise HTTPException(503, f"The local model failed during the run: {error}") from error
    except HTTPException:
        raise
    except Exception as error:  # noqa: BLE001 - report the failure, never leave the lock held
        logger.exception("research failed unexpectedly")
        raise HTTPException(500, f"The research run failed unexpectedly: {type(error).__name__}: {error}") from error
    finally:
        _run_lock.release()


# ----------------------------------------------------------------------------- live progress (Server-Sent Events)

_STAGE_LINE = re.compile(r"^\[(?P<stage>[a-z]+)\]\s*(?P<text>.*)$")
KEEP_ALIVE_SECONDS = 15.0


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _progress_event(message: str, started: float) -> dict[str, Any]:
    """'[tools] running search_web (...) ...' becomes {stage: 'tools', message: 'running search_web (...) ...'}."""
    match = _STAGE_LINE.match(message)
    stage, text = (match["stage"], match["text"]) if match else ("agent", message)
    return {"stage": stage, "message": text, "elapsed_seconds": round(time.perf_counter() - started, 1)}


@app.post(
    "/research/stream",
    summary="Same research as POST /research, streamed: live progress events, then the result",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": (
                "Server-Sent Events. `progress` events ({stage, message, elapsed_seconds}) while the agent works, then "
                "one `result` event (the same JSON as POST /research) or one `error` event ({status, detail})."
            ),
        },
        429: {"description": "Another research run is already in progress."},
        503: {"description": "Ollama or the model is not available."},
    },
)
def research_stream(
    request: ResearchRequest,
    settings: Settings = Depends(get_settings),
    deps: AgentDeps = Depends(get_agent_deps),
) -> StreamingResponse:
    """A browser cannot show anything useful during a run that takes minutes, so this streams what the agent is doing.

    The refusals (422, 503, 429) are plain HTTP errors sent before the stream starts. The run itself lives in a
    worker thread that outlives the connection, so the lock stays held while the GPU is busy even if the browser closes.
    """
    description = _check_ready(request, settings)
    _take_run_slot()
    started = time.perf_counter()
    events: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()

    def emit(message: str) -> None:
        logger.info(message)
        events.put(("progress", _progress_event(message, started)))

    run_deps = dataclasses.replace(deps, progress=emit)

    def work() -> None:
        try:
            logger.info("research started (%d chars, model %s, streaming)", len(description), settings.ollama_model)
            state = run_research(description, run_deps)
            response = build_response(state, run_deps)
            logger.info(
                "research finished: stop_reason=%s turns=%d tool_calls=%d sources=%d in %.0fs",
                response.stop_reason, response.stats.agent_turns, response.stats.tool_calls_executed,
                len(response.sources), time.perf_counter() - started,
            )
            events.put(("result", response.model_dump(mode="json")))
        except LLMError as error:
            logger.error("research failed: %s", error)
            events.put(("error", {"status": 503, "detail": f"The local model failed during the run: {error}"}))
        except Exception as error:  # noqa: BLE001 - report the failure, never leave the lock held
            logger.exception("research failed unexpectedly")
            events.put(("error", {"status": 500, "detail": f"The research run failed unexpectedly: {type(error).__name__}: {error}"}))
        finally:
            _run_lock.release()
            events.put(None)

    try:
        threading.Thread(target=work, name="research-run", daemon=True).start()
    except BaseException:
        _run_lock.release()
        raise

    def frames() -> Iterator[str]:
        yield _sse("progress", _progress_event("[plan] starting the research ...", started))
        while True:
            try:
                item = events.get(timeout=KEEP_ALIVE_SECONDS)
            except queue.Empty:
                yield ": keep-alive\n\n"  # keeps proxies and the browser from closing a quiet connection
                continue
            if item is None:
                return
            yield _sse(*item)

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
