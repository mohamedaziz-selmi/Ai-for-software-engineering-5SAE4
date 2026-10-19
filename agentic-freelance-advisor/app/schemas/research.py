"""Data models shared by the tools, the agent and the API."""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ErrorCode = Literal[
    "not_configured",  # a required API key is missing
    "auth_failed",  # the key was rejected
    "rate_limited",
    "quota_exceeded",
    "timeout",
    "network_error",
    "http_error",
    "not_found",
    "invalid_input",
    "unavailable",  # skipped: the tool already failed earlier in this run
    "duplicate",  # skipped: same or near-identical call already made
    "budget_exhausted",  # skipped: tool-call limit reached
    "unexpected",
]

EvidenceKind = Literal["web_page", "repository", "repository_detail", "dataset"]


class ToolError(BaseModel):
    code: ErrorCode
    message: str
    retry_after_seconds: int | None = None


class EvidenceItem(BaseModel):
    """One normalised, bounded piece of retrieved information. Text is already sanitised."""

    kind: EvidenceKind
    title: str
    url: str
    summary: str = ""
    detail: str = ""  # longer text, e.g. README excerpt and dependency file of an inspected repo
    metadata: dict[str, Any] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)  # e.g. "possible_prompt_injection"


class ToolResult(BaseModel):
    """What every research tool returns. Tools never raise: failures are reported here."""

    tool: str
    arguments: dict[str, Any]
    ok: bool
    items: list[EvidenceItem] = Field(default_factory=list)
    error: ToolError | None = None
    notes: list[str] = Field(default_factory=list)


class Source(EvidenceItem):
    """An evidence item registered in the run's evidence ledger under a stable id (S1, S2, ...)."""

    id: str
    found_by: list[int] = Field(default_factory=list)  # step numbers of the tool executions


class ResearchPlan(BaseModel):
    """The model's reading of the request. This is understanding, not researched fact."""

    objective: str = Field(description="One sentence naming the software the freelancer must build, not the task of analysing the request.")
    functional_requirements: list[str] = Field(description="At most 5 short requirements taken from the request.")
    technical_constraints: list[str] = Field(description="At most 3 constraints stated in the request; empty if none.")
    assumptions: list[str] = Field(description="At most 3 assumptions needed because the request is silent.")
    needs_datasets: bool = Field(description="True only if the project must train or evaluate a model on data.")
    needs_github_examples: bool = Field(description="True if open-source implementations would help the freelancer.")
    key_topics: list[str] = Field(description="3 to 5 short topics that must be researched.")


CoverageStatus = Literal["covered", "weak", "missing", "not_applicable", "unavailable"]


class CoverageItem(BaseModel):
    area: str
    label: str
    status: CoverageStatus
    detail: str  # evidence-based explanation, e.g. which sources matched
    source_ids: list[str] = Field(default_factory=list)
    action: str = ""  # what the agent could do to close the gap; empty if nothing useful remains
    tool: str = ""  # the tool that would close it, and the arguments to start with
    arguments: dict[str, str] = Field(default_factory=dict)


class Evaluation(BaseModel):
    """Source coverage, computed from the evidence ledger and the tool history."""

    items: list[CoverageItem]
    sufficient: bool
    gaps: list[str] = Field(default_factory=list)


class ToolExecution(BaseModel):
    """One row of the tool execution history returned to the API caller."""

    step: int
    tool: str
    arguments: dict[str, Any]
    status: Literal["ok", "error", "skipped"]
    started_at: str
    duration_seconds: float
    result_count: int = 0
    source_ids: list[str] = Field(default_factory=list)
    error: ToolError | None = None
    notes: list[str] = Field(default_factory=list)
    # "fallback" marks a call chosen by the evaluator because the model produced no decision (see agent node)
    decided_by: Literal["llm", "fallback"] = "llm"


# ----------------------------------------------------------------------------- report


class ReportSection(BaseModel):
    id: Literal["A", "B", "C", "D", "E", "F", "G"]
    title: str
    content: str  # Markdown
    # Where the content comes from, so a reader knows what is verified:
    #   tool_evidence        built directly from tool results
    #   derived_from_request the model's reading of the request
    #   model_recommendation model-written advice; cites sources where it can, otherwise general knowledge
    origin: Literal["tool_evidence", "derived_from_request", "model_recommendation"]


class ReportValidation(BaseModel):
    """What the post-generation checks changed. Every URL or citation that is not in the ledger is removed."""

    removed_urls: list[str] = Field(default_factory=list)
    removed_citations: list[str] = Field(default_factory=list)
    # Statements that cite a source but contradict its retrieved metadata (license, downloads, stars) or name
    # a different source; they stay in the text, marked [CHECK: ...].
    unverified_claims: list[str] = Field(default_factory=list)
    sections_not_generated: list[str] = Field(default_factory=list)


class TechnicalReport(BaseModel):
    title: str
    sections: list[ReportSection]
    markdown: str
    limitations: list[str] = Field(default_factory=list)
    validation: ReportValidation = Field(default_factory=ReportValidation)


# ----------------------------------------------------------------------------- API


# Words that say nothing about WHAT is to be built. A description needs at least two other words.
_VAGUE_WORDS = frozenset(
    """the and for with that this from have has had are was were been can could should would will shall may might must
    need needs want wants like also just into onto over under about what when where which who how why not but you your
    yours our ours his her its their them they she him mine any all some one two out off too very then than there here
    please help hello hey okay yes sure thanks thank build make create develop write implement do does did get got
    project projects thing things something anything stuff test tests testing example examples sample idea ideas
    is in on an to of it my me we or if as at by no so up us be""".split()
)
_WORD = re.compile(r"[a-z][a-z0-9+#]+")

NOT_A_PROJECT = (
    "The description does not say what to build. Describe the project in a sentence or two: what it should do and, "
    "if you have one, the technology to use. Example: 'Build a fake news detection system using Python and machine "
    "learning.'"
)


def check_project_description(text: str) -> str | None:
    """None if the text describes a project, otherwise the reason it does not.

    A placeholder such as "your project" used to reach the agent, which then researched topics nobody had asked
    about (full-stack architecture, React) instead of saying that the description was missing. Deterministic and
    cheap on purpose: an LLM would be slow and, as seen, is pushed towards inventing a task.
    """
    meaningful = {word for word in _WORD.findall(text.lower()) if word not in _VAGUE_WORDS}
    return None if len(meaningful) >= 2 else NOT_A_PROJECT


class ResearchRequest(BaseModel):
    project_description: str = Field(
        min_length=10,
        max_length=2000,
        description="What the freelancer has to build, in plain language.",
        examples=["Build a fake news detection system using Python and machine learning."],
    )

    @field_validator("project_description")
    @classmethod
    def must_describe_a_project(cls, value: str) -> str:
        problem = check_project_description(value)
        if problem:
            raise ValueError(problem)
        return value


class RunStats(BaseModel):
    model: str
    elapsed_seconds: float
    agent_turns: int
    tool_calls_executed: int
    llm_calls: list[dict[str, Any]]


class ResearchResponse(BaseModel):
    project_description: str
    stop_reason: str
    plan: ResearchPlan | None
    report: TechnicalReport
    sources: list[Source]
    tool_history: list[ToolExecution]
    evaluation: Evaluation | None
    stats: RunStats


class ToolInfo(BaseModel):
    name: str
    description: str
    provider: str
    requires_key: bool
    configured: bool
    note: str


class OllamaHealth(BaseModel):
    base_url: str
    model: str
    reachable: bool
    model_installed: bool
    installed_models: list[str]
    error: str | None = None


class HealthResponse(BaseModel):
    status: str  # "ok" when research can run, "degraded" when it cannot (see `problems`)
    ollama: OllamaHealth
    research_running: bool
    web_search_configured: bool
    problems: list[str] = Field(default_factory=list)
