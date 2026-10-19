"""Source-coverage evaluation, computed from the evidence ledger and the tool history.

This deliberately does NOT ask the LLM whether the research went well. Each of the eight areas is
judged from what the tools actually returned. The checks for architecture, environment setup and
development steps are keyword matches over retrieved titles, snippets and README excerpts: simple,
transparent proxies. They say which sources matched so the result can be audited.

Technologies, architecture, setup and steps can be researched with web search or, when that is not
available, by reading the README and dependency file of the best repository found.
"""

import re

from app.agent.context import find_redundant_call
from app.schemas.research import CoverageItem, Evaluation, ResearchPlan, Source, ToolExecution
from app.tools import DATASET_SEARCH, GITHUB_INSPECT, GITHUB_SEARCH, WEB_SEARCH

MAX_ATTEMPTS_PER_AREA = 3  # after this many fruitless searches the agent stops being asked to retry
MAX_REPOSITORY_INSPECTIONS = 2  # each one costs about 4 GitHub API requests (60/hour without a token)
# Order in which open gaps are closed when the model cannot decide: the core assets first.
FALLBACK_PRIORITY = ("datasets", "github_examples", "technologies", "environment_setup", "architecture", "development_steps")

ARCHITECTURE = re.compile(r"architect|pipeline|design|structure|workflow|components?|overview|layers?|endpoints?|api reference", re.I)
ENVIRONMENT = re.compile(
    r"install|set ?up|getting started|quick ?start|requirements|dependenc|prerequisite|\bpip\b|conda|virtual ?env|"
    r"\bnpm\b|\byarn\b|\bpnpm\b|gradle|maven|composer|cargo|\bflutter pub\b|docker",
    re.I,
)
STEPS = re.compile(r"tutorial|step[- ]by[- ]step|how to|guide|walk-?through|usage|example|train|deploy|getting started", re.I)

ACTIONS = {
    "datasets": "call search_huggingface_datasets with short keywords such as '{query}'.",
    "datasets_retry": "the last dataset search found nothing useful; call search_huggingface_datasets again with different, shorter keywords such as '{query}'.",
    "github_examples": "call search_github_repositories with short keywords such as '{query}'.",
    "github_retry": "the last repository search found nothing useful; call search_github_repositories again with different keywords such as '{query}'.",
    "technologies": "call search_web for the official documentation of ONE library you would recommend, naming it, for example 'scikit-learn text classification documentation' or 'FastAPI CORS documentation' (use the library that fits THIS project).",
    "architecture": "call search_web for an architecture or design guide, for example '{query}'.",
    "environment_setup": "call search_web for installation and setup instructions, for example '{query}'.",
    "development_steps": "call search_web for a step-by-step tutorial, for example '{query}'.",
}

_STOPWORDS = frozenset(
    "a an the for of in on to and or with using use build create make system application app project that this "
    "which i need want develop implement research find how guide complete relevant suitable useful "
    "do does did can could should would will shall may might must is are was were be been you your it its my me we our "
    "they their these those at by as from into over under about than then there here what when where who why".split()
)


def _words(text: str, count: int) -> str:
    words = [w for w in re.findall(r"[a-z0-9+#.-]+", text.lower()) if w not in _STOPWORDS and len(w) > 1]
    return " ".join(words[:count])


# Words that name a language, a framework or a kind of software, not the SUBJECT of the project: a dataset search for
# "python sentiment" finds nothing, one for "sentiment analysis" does.
_TECH_NOISE = frozenset(
    "python java javascript typescript rest api web app application software system tool tools using model models "
    "machine learning deep ai framework library flask fastapi django react node".split()
)


def _project_words(request: str, plan: ResearchPlan | None, count: int, *, subject_only: bool = False) -> str:
    """The project's own words: from the first sentence of the request, else from the plan's objective.

    The plan's first key topic is NOT used: it is often a sub-step ("text preprocessing"), and the agent copied
    it into its searches, which then returned generic blog posts instead of material about the project.
    """
    first_sentence = re.split(r"(?<=[.!?])\s+", request.strip())[0] if request.strip() else ""
    words = _words(first_sentence or (plan.objective if plan else ""), 12).split()
    if subject_only:
        words = [word for word in words if word not in _TECH_NOISE] or words
    return " ".join(words[:count])


def suggested_query(area: str, plan: ResearchPlan | None, request: str = "") -> str:
    """A reasonable starting query for an area, taken from the project's own words. Used as the example in hints."""
    project = _project_words(request, plan, 4) or "project"
    subject = _project_words(request, plan, 2, subject_only=True) or project
    return {
        "datasets": subject,
        "github_examples": project,
        "technologies": f"{project} documentation",
        "architecture": f"{project} architecture guide",
        "environment_setup": f"{project} installation setup",
        "development_steps": f"{project} tutorial step by step",
    }[area]


def _attempts(history: list[ToolExecution], tool: str) -> int:
    return sum(1 for e in history if e.tool == tool and e.status in ("ok", "error"))


def _text(source: Source) -> str:
    return f"{source.title} {source.summary} {source.detail}"


def _ids(sources: list[Source]) -> list[str]:
    return [s.id for s in sources]


def _item(area, label, status, detail, *, source_ids=None, action="", tool="", arguments=None) -> CoverageItem:
    return CoverageItem(area=area, label=label, status=status, detail=detail, source_ids=source_ids or [],
                        action=action, tool=tool, arguments=arguments or {})


def _search_item(
    area: str,
    label: str,
    *,
    plan: ResearchPlan | None,
    request: str,
    matches: list[Source],
    tool: str,
    action_key: str,
    history: list[ToolExecution],
    unavailable: dict[str, str],
    found_detail: str,
    weak: list[Source] | None = None,
    weak_detail: str = "",
) -> CoverageItem:
    """An area researched with one search tool: covered / weak / missing / unavailable."""
    if matches:
        return _item(area, label, "covered", f"{found_detail} ({', '.join(_ids(matches[:4]))}).", source_ids=_ids(matches[:4]))
    attempts, tool_down = _attempts(history, tool), tool in unavailable
    query = suggested_query(area, plan, request)
    can_act = not tool_down and attempts < MAX_ATTEMPTS_PER_AREA
    act = {"action": ACTIONS[action_key].format(query=query), "tool": tool, "arguments": {"query": query}} if can_act else {}
    if weak:
        return _item(area, label, "weak", weak_detail, source_ids=_ids(weak[:4]), **act)
    if tool_down:
        return _item(area, label, "unavailable", f"{tool} cannot be used in this run ({unavailable[tool]}).")
    if not can_act:
        return _item(area, label, "weak", f"Nothing relevant found after {attempts} searches.")
    return _item(area, label, "missing", "Nothing retrieved yet.", **act)


def _guide_item(
    area: str,
    label: str,
    *,
    plan: ResearchPlan | None,
    request: str,
    matches: list[Source],
    repositories: list[Source],
    history: list[ToolExecution],
    unavailable: dict[str, str],
    found_detail: str,
    weak: list[Source] | None = None,
    weak_detail: str = "",
) -> CoverageItem:
    """Technologies, architecture, setup and steps: web search first, else read the best repository."""
    if matches:
        return _item(area, label, "covered", f"{found_detail} ({', '.join(_ids(matches[:4]))}).", source_ids=_ids(matches[:4]))

    web_attempts = _attempts(history, WEB_SEARCH)
    web_usable = WEB_SEARCH not in unavailable and web_attempts < MAX_ATTEMPTS_PER_AREA
    candidates = sorted((s for s in repositories if s.kind == "repository"), key=lambda s: -(s.metadata.get("stars") or 0))
    inspect_usable = (
        GITHUB_INSPECT not in unavailable
        and _attempts(history, GITHUB_INSPECT) < MAX_REPOSITORY_INSPECTIONS
        and bool(candidates)
    )
    act: dict = {}
    # One web search first; if it did not cover the area, reading the best repository (README, dependency file)
    # is more productive than more web searches (a live run spent three of them on generic blog posts).
    if web_usable and (web_attempts == 0 or not inspect_usable):
        query = suggested_query(area, plan, request)
        act = {"action": ACTIONS[area].format(query=query), "tool": WEB_SEARCH, "arguments": {"query": query}}
    elif inspect_usable:
        owner, _, name = candidates[0].title.partition("/")
        act = {
            "action": (
                f"call inspect_github_repository with owner='{owner}' and repo='{name}' (the most popular repository "
                f"found, {candidates[0].id}) to read its README, setup instructions and dependency file."
            ),
            "tool": GITHUB_INSPECT,
            "arguments": {"owner": owner, "repo": name},
        }
    if weak:
        return _item(area, label, "weak", weak_detail, source_ids=_ids(weak[:4]), **act)
    if act:
        return _item(area, label, "missing", "Nothing retrieved yet.", **act)
    if WEB_SEARCH in unavailable and not (candidates and GITHUB_INSPECT not in unavailable):
        return _item(area, label, "unavailable", f"web search cannot be used in this run ({unavailable[WEB_SEARCH]}) and no repository can be read instead.")
    if WEB_SEARCH in unavailable:
        read = _attempts(history, GITHUB_INSPECT)
        return _item(area, label, "weak", f"No match in the README of the {read} repository(ies) read; web search is unavailable ({unavailable[WEB_SEARCH]}).")
    return _item(area, label, "weak", f"Nothing relevant found after {web_attempts} web searches.")


def evaluate_coverage(
    plan: ResearchPlan | None,
    sources: dict[str, Source],
    history: list[ToolExecution],
    unavailable: dict[str, str],
    request: str = "",
) -> Evaluation:
    ledger = list(sources.values())
    web = [s for s in ledger if s.kind == "web_page"]
    docs = [s for s in web if s.metadata.get("looks_like_documentation")]
    repos = [s for s in ledger if s.kind in ("repository", "repository_detail")]
    datasets = [s for s in ledger if s.kind == "dataset"]
    inspected = [s for s in ledger if s.kind == "repository_detail"]
    guides = web + inspected  # sources that can describe an approach, a setup or steps

    items: list[CoverageItem] = []

    # 1. requirements: the model's reading of the request, never externally verified
    if plan and plan.functional_requirements:
        items.append(_item("requirements", "Project requirements", "covered",
                           f"{len(plan.functional_requirements)} requirement(s) derived from the request by the model; not externally verified."))
    else:
        items.append(_item("requirements", "Project requirements", "weak",
                           "The request could not be broken down into requirements by the model."))

    # 2. technologies: official-looking documentation, or a repository whose dependency file was read
    with_dependencies = [s for s in inspected if s.metadata.get("dependency_file")]
    items.append(_guide_item(
        "technologies", "Recommended technologies", plan=plan, request=request, matches=docs + with_dependencies, repositories=repos,
        history=history, unavailable=unavailable, found_detail="Documentation or dependency files retrieved",
        weak=web + repos, weak_detail="Only general web pages or repositories were found, no official-looking documentation or dependency file.",
    ))

    # 3. datasets
    if plan is not None and not plan.needs_datasets:
        items.append(_item("datasets", "Relevant datasets", "not_applicable", "The project does not need a dataset."))
    else:
        well_described = [s for s in datasets if s.metadata.get("license") not in (None, "not stated", "unknown")]
        good = datasets if (len(datasets) >= 2 or well_described) else []
        items.append(_search_item(
            "datasets", "Relevant datasets", plan=plan, request=request, matches=good, tool=DATASET_SEARCH,
            action_key="datasets" if not datasets and not _attempts(history, DATASET_SEARCH) else "datasets_retry",
            history=history, unavailable=unavailable, found_detail=f"{len(datasets)} dataset(s) found",
            weak=datasets, weak_detail="A single dataset was found and its license is not stated.",
        ))

    # 4. GitHub examples
    if plan is not None and not plan.needs_github_examples:
        items.append(_item("github_examples", "Relevant GitHub examples", "not_applicable", "Open-source examples are not needed for this project."))
    else:
        items.append(_search_item(
            "github_examples", "Relevant GitHub examples", plan=plan, request=request, matches=repos, tool=GITHUB_SEARCH,
            action_key="github_examples" if not _attempts(history, GITHUB_SEARCH) else "github_retry",
            history=history, unavailable=unavailable, found_detail=f"{len(repos)} repository(ies) found",
        ))

    # 5-7. approach, setup and steps: keyword proxies over web pages and inspected repositories
    for area, label, pattern in (
        ("architecture", "Architecture or implementation approach", ARCHITECTURE),
        ("environment_setup", "Environment setup", ENVIRONMENT),
        ("development_steps", "Development steps", STEPS),
    ):
        matched = [s for s in guides if pattern.search(_text(s))]
        items.append(_guide_item(
            area, label, plan=plan, request=request, matches=matched, repositories=repos, history=history, unavailable=unavailable,
            found_detail="Keyword match in retrieved titles, snippets or README excerpts",
        ))

    # 8. source references
    total = len(ledger)
    status = "covered" if total >= 3 else "weak" if total else "missing"
    items.append(_item("source_references", "Source references", status, f"{total} distinct source(s) retrieved.",
                       source_ids=list(sources)[:6]))

    gaps = [f"{i.area}: {i.action}" for i in items if i.status in ("missing", "weak") and i.action]
    return Evaluation(items=items, sufficient=not gaps, gaps=gaps)


def render_coverage(evaluation: Evaluation) -> str:
    """Compact text for the agent prompt: what is covered and exactly what to do about each gap."""
    lines = []
    for item in evaluation.items:
        if item.status == "covered":
            lines.append(f"- {item.area}: covered")
        elif item.status == "not_applicable":
            lines.append(f"- {item.area}: not needed")
        elif item.status == "unavailable":
            lines.append(f"- {item.area}: cannot be researched (tool unavailable)")
        elif item.action:
            lines.append(f"- {item.area}: {item.status.upper()}. Next: {item.action}")
        else:
            lines.append(f"- {item.area}: {item.status} (nothing more to try)")
    return "\n".join(lines)


def next_suggested_call(
    evaluation: Evaluation, available: set[str], history: list[ToolExecution]
) -> tuple[str, dict[str, str]] | None:
    """The most important open gap whose tool is usable and whose call has not been made yet."""
    rank = {area: position for position, area in enumerate(FALLBACK_PRIORITY)}
    for item in sorted(evaluation.items, key=lambda i: rank.get(i.area, len(rank))):
        if item.action and item.tool in available and find_redundant_call(item.tool, item.arguments, history) is None:
            return item.tool, dict(item.arguments)
    return None
