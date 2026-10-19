"""Agent state and the dependencies the graph nodes need."""

import operator
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages

from app.config import Settings
from app.schemas.research import Evaluation, ResearchPlan, Source, TechnicalReport, ToolExecution


class AgentState(TypedDict):
    """Everything the agent knows during one research run.

    `messages` is the full conversation record (AI tool calls and tool observations). The prompt of
    each agent turn is NOT built from it: it is rebuilt from `sources` and `history`, so the context
    stays bounded no matter how long the run is.
    """

    request: str
    messages: Annotated[list[AnyMessage], add_messages]
    sources: dict[str, Source]  # the evidence ledger, keyed by source id (S1, S2, ...)
    history: Annotated[list[ToolExecution], operator.add]  # every tool execution, including skipped ones
    unavailable: dict[str, str]  # tool name -> why it cannot be used for the rest of the run
    iteration: int  # agent turns taken
    tool_calls_made: int  # tool calls actually executed (skipped calls do not count)
    idle_rounds: int  # consecutive tool rounds that produced no new source
    started_at: float
    stop_reason: str | None
    llm_calls: Annotated[list[dict[str, Any]], operator.add]  # per-LLM-call timing and token stats
    plan: ResearchPlan | None
    evaluation: Evaluation | None  # source coverage after the latest tool round
    nudges: int  # times the evaluator sent the agent back after it said DONE with gaps open
    notes: Annotated[list[str], operator.add]  # run-level remarks that end up in the report limitations
    report: TechnicalReport | None


@dataclass
class AgentDeps:
    """Collaborators injected into the graph so tests can replace the LLM, the tools and the clock."""

    settings: Settings
    llm_factory: Callable[[int | None], BaseChatModel]  # num_predict -> chat model
    tools: dict[str, BaseTool]
    clock: Callable[[], float] = field(default=time.monotonic)
    # Tools known to be unusable before the run starts (e.g. a missing API key). They are never
    # offered to the model, which saves an LLM turn that could only end in a failed call.
    unavailable_at_start: dict[str, str] = field(default_factory=dict)
    # Receives short status lines such as "[agent] turn 2: the model is deciding...". A model call takes one to
    # two minutes, and a graph step only reports when it is finished, so without this a run looks frozen.
    progress: Callable[[str], None] = field(default=lambda message: None)

    def elapsed(self, state: AgentState) -> float:
        return self.clock() - state["started_at"]

    def say(self, message: str) -> None:
        self.progress(message)


def initial_state(request: str, deps: AgentDeps) -> AgentState:
    return AgentState(
        request=request,
        messages=[],
        sources={},
        history=[],
        unavailable=dict(deps.unavailable_at_start),
        iteration=0,
        tool_calls_made=0,
        idle_rounds=0,
        started_at=deps.clock(),
        stop_reason=None,
        llm_calls=[],
        plan=None,
        evaluation=None,
        nudges=0,
        notes=[],
        report=None,
    )
