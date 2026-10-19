"""Report generation.

Two kinds of sections, kept apart on purpose:
  * C (research results) and G (sources and verification) are built by code straight from the evidence
    ledger. Nothing in them is written by the model, so every URL and every number comes from a tool result.
  * B, D, E and F are recommendations written by the local model. They are checked afterwards: any URL or
    citation that is not in the ledger is removed, and the section is labelled as model-written.
Section A is the model's reading of the request. Time is checked before every model call, so a slow run
still returns a report: sections that could not be written are replaced by an explicit notice.
"""

import re
import time
from typing import Any
from urllib.parse import urlsplit

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.context import estimate_tokens, normalize_url, render_plan, source_line
from app.agent.llm import LLMError, llm_stat, message_text, safe_invoke
from app.agent.prompts import REPORT_SYSTEM, SHORT_REASONING_HINT, report_user_message
from app.agent.state import AgentDeps, AgentState
from app.schemas.research import (
    ReportSection,
    ReportValidation,
    ResearchPlan,
    ResearchResponse,
    RunStats,
    Source,
    TechnicalReport,
    ToolExecution,
)
from app.tools.common import days_since, truncate

TITLES = {
    "A": "Project Understanding",
    "B": "Recommended Technology Stack",
    "C": "Research Results",
    "D": "Recommended Architecture",
    "E": "Environment Configuration",
    "F": "Step-by-Step Implementation Roadmap",
    "G": "Sources and Verification",
}
MODEL_SECTIONS = ("B", "D", "E", "F")
ORIGIN_NOTES = {
    "tool_evidence": "_Built directly from tool results. Nothing in this section was written by the model._",
    "derived_from_request": "_The model's reading of your request. Not externally verified._",
    "model_recommendation": (
        "_Written by the local model. [S#] citations point to the retrieved sources listed in section G; "
        "text marked (general knowledge) is not backed by a retrieved source._"
    ),
}
COMMANDS_NOTE = "_The commands above are suggestions. This agent did not run or test them._"
BANNER = (
    "> Produced by a research agent that only researches and advises. Nothing was downloaded, cloned, "
    "installed or executed, and nothing here has been tested."
)
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
REMOVED_LINK = "[link removed: not from retrieved sources]"
STALE_AFTER_DAYS = 730
PROMPT_SAFETY_TOKENS = 150

_URL = re.compile(r"https?://[^\s)\]>\"'`]+")
_CITATION = re.compile(r"([ \t]*)[\[(](S\d+(?:\s*,\s*S\d+)*)[\])]")  # [S2], [S2, S3], (S2), with the space before it
# Only for READING claims (it never changes text): the model also writes "(S7 shows ...)" and "(S8: ...)".
_CITED_ID = re.compile(r"\bS\d+\b")
_RULES_NOTE = re.compile(r"^[ \t]*[*_]*note:[^\n]*\brules?\b[^\n]*\n?", re.IGNORECASE | re.MULTILINE)
_TITLE_CLEAN = re.compile(r"[#*_:`\s]+")


_LETTER_PREFIX = re.compile(r"^\W*(?:section\s+)?[A-G][.):]\s*", re.IGNORECASE)


def _is_title_line(line: str) -> bool:
    """True for a first line that only repeats the section title ("## Recommended Architecture", "**D. ...**")."""
    if len(line) > 90 or not _TITLE_CLEAN.sub(" ", line).strip():
        return False  # too long to be a title, or only punctuation such as a code fence
    stripped = _LETTER_PREFIX.sub("", line)  # "D. Recommended Architecture", "Section E: Environment ..."
    normalized = _TITLE_CLEAN.sub(" ", stripped).strip().lower()
    return normalized == "" or any(normalized.startswith(title.lower()) for title in TITLES.values())


# ----------------------------------------------------------------------------- checking model output


def clean_generated(text: str, ledger: dict[str, Source]) -> tuple[str, list[str], list[str]]:
    """Remove every URL and citation that does not come from the evidence ledger.

    Returns (clean text, removed URLs, removed citation ids). Loopback URLs stay: they are addresses of
    the freelancer's own future app, not sources.
    """
    allowed = {normalize_url(source.url) for source in ledger.values()}
    removed_urls: list[str] = []
    removed_citations: list[str] = []

    def fix_url(match: re.Match) -> str:
        url = match.group(0).rstrip(".,;:")
        trailing = match.group(0)[len(url):]
        host = urlsplit(url).hostname or ""
        if host in LOOPBACK_HOSTS or normalize_url(url) in allowed:
            return match.group(0)
        removed_urls.append(url)
        return REMOVED_LINK + trailing

    def fix_citation(match: re.Match) -> str:
        space = match.group(1)
        ids = [part.strip() for part in match.group(2).split(",")]
        kept = [i for i in ids if i in ledger]
        removed_citations.extend(i for i in ids if i not in ledger)
        if kept:
            return f"{space}{match.group(0)[len(space)]}{', '.join(kept)}{match.group(0)[-1]}"
        following = match.string[match.end():match.end() + 1]
        # "a single codebase [S9]." must not become "a single codebase ."
        return "" if not following or following.isspace() or following in ".,;:!?)" else space

    text = _URL.sub(fix_url, text)
    text = _CITATION.sub(fix_citation, text)
    text = _RULES_NOTE.sub("", text)  # "Note: avoided URLs per the rules": the model leaking its instructions
    first, _, rest = text.strip().partition("\n")
    if _is_title_line(first):  # a title the model added although it was told not to
        text = rest
    return text.strip(), removed_urls, removed_citations


_SENTENCES = re.compile(r"((?<=[.!?])\s+|\n+)")
_LICENSE_CLAIM = re.compile(
    r"\b(CC0(?:[- ]1\.0)?|CC[- ]BY(?:[- ](?:NC|SA|ND))*(?:[- ]\d\.\d)?|MIT|Apache(?:[- ]License)?(?:[- ]?(?:2\.0|v2))?|"
    r"L?GPL(?:[- ]?v?\d(?:\.\d)?)?|BSD(?:[- ]?\d[- ]Clause)?|MPL[- ]?2\.0|Unlicense|OpenRAIL)\b",
    re.IGNORECASE,
)
_COUNT_CLAIM = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d+)\s+(downloads|stars)\b", re.IGNORECASE)


def _license_key(value: str) -> str:
    return re.sub(r"license|[^a-z0-9]", "", value.lower())


def check_claims(text: str, ledger: dict[str, Source]) -> tuple[str, list[str]]:
    """Compare statements that cite sources with the cited sources' retrieved metadata.

    clean_generated only guarantees that cited ids and URLs exist. A small model can still attach a real
    id to a wrong fact, so for each sentence that cites sources this checks that (1) a license it mentions
    is the license of a cited source, (2) a download or star count equals the cited source's count, and
    (3) a source it names is one of the cited sources. A failing sentence is kept but marked [CHECK: ...].
    Returns (marked text, one description per problem).
    """
    problems: list[str] = []
    parts = _SENTENCES.split(text)
    for index in range(0, len(parts), 2):
        sentence = parts[index]
        cited = set(_CITED_ID.findall(sentence)) & set(ledger)
        if not cited:
            continue
        found: list[str] = []

        licenses = {_license_key(part) for sid in cited for part in str(ledger[sid].metadata.get("license", "")).split(",")}
        for claim in {m.group(1) for m in _LICENSE_CLAIM.finditer(sentence)}:
            key = _license_key(claim)
            if key and not any(known and (known.startswith(key) or key.startswith(known)) for known in licenses):
                found.append(f"license '{claim}' is not the license of {', '.join(sorted(cited))}")

        for number, unit in _COUNT_CLAIM.findall(sentence):
            field = "downloads" if unit.lower() == "downloads" else "stars"
            actual = {ledger[sid].metadata.get(field) for sid in cited}
            if int(number.replace(",", "")) not in actual:
                found.append(f"{number} {unit.lower()} does not match {', '.join(sorted(cited))}")

        lowered = sentence.lower()
        for sid, source in ledger.items():
            if sid not in cited and len(source.title) >= 8 and source.title.lower() in lowered:
                found.append(f"names {source.title} ({sid}) but cites {', '.join(sorted(cited))}")

        if found:
            problems.extend(found)
            parts[index] = sentence + f" [CHECK: {'; '.join(found)}]"
    return "".join(parts), problems


# ----------------------------------------------------------------------------- model-written sections


def build_report_messages(letter: str, plan: ResearchPlan | None, ledger: dict[str, Source], deps: AgentDeps, hint: str = "") -> list:
    settings = deps.settings
    budget = settings.ollama_num_ctx - settings.report_max_tokens - PROMPT_SAFETY_TOKENS
    plan_text = render_plan(plan) if plan else "Objective: not available."
    if plan and plan.functional_requirements:
        plan_text += "\nRequirements: " + "; ".join(plan.functional_requirements)
    if plan and plan.technical_constraints:
        plan_text += "\nConstraints: " + "; ".join(plan.technical_constraints)
    lines = [source_line(source, 170) for source in list(ledger.values())[:12]]
    chars = 2200
    while True:
        sources_text, total = [], 0
        for line in lines:
            if total + len(line) + 1 > chars:
                break
            sources_text.append(line)
            total += len(line) + 1
        user = report_user_message(plan_text, "\n".join(sources_text), letter, bool(settings.ollama_reasoning)) + (f"\n\n{hint}" if hint else "")
        if estimate_tokens(REPORT_SYSTEM + user) <= budget or chars <= 400:
            return [SystemMessage(content=REPORT_SYSTEM), HumanMessage(content=user)]
        chars = int(chars * 0.75)


def write_model_section(
    letter: str, state: AgentState, deps: AgentDeps, stats: list[dict[str, Any]]
) -> tuple[str | None, str]:
    """Ask the model for one section. Returns (text, "") or (None, reason it is missing)."""
    if deps.elapsed(state) >= deps.settings.run_timeout_seconds:
        return None, "the run time limit was reached before this section could be written"
    llm = deps.llm_factory(deps.settings.report_max_tokens)
    hint = ""
    for attempt in range(2):
        messages = build_report_messages(letter, state.get("plan"), state["sources"], deps, hint)
        started = time.perf_counter()
        try:
            reply = safe_invoke(llm, messages, deps.settings.ollama_request_timeout)
        except LLMError as error:
            return None, f"the local model failed ({error})"
        stats.append(llm_stat(f"report {letter}" + (" (retry)" if attempt else ""), reply, started, estimate_tokens(messages[1].content + REPORT_SYSTEM)))
        text = message_text(reply)
        if text:
            if (reply.response_metadata or {}).get("done_reason") == "length":
                text += "\n\n_(This section was cut off because the model reached its length limit.)_"
            return text, ""
        hint = SHORT_REASONING_HINT  # ran out of tokens while thinking: try once more, thinking less
    return None, "the model produced no usable text, most likely because it ran out of tokens while thinking"


# ----------------------------------------------------------------------------- evidence-built sections


def section_a(plan: ResearchPlan | None) -> str:
    if plan is None:
        return "No project analysis is available."

    def bullets(items: list[str], empty: str) -> str:
        return "\n".join(f"- {item}" for item in items) if items else empty

    return "\n".join(
        [
            f"**Objective:** {plan.objective}",
            "",
            "**Functional requirements**",
            bullets(plan.functional_requirements, "- None could be extracted from the request."),
            "",
            "**Technical constraints**",
            bullets(plan.technical_constraints, "- None stated in the request."),
            "",
            "**Assumptions**",
            bullets(plan.assumptions, "- None."),
        ]
    )


def assess(source: Source) -> tuple[list[str], list[str]]:
    """Strengths and limitations that follow directly from a source's retrieved metadata."""
    meta, good, bad = source.metadata, [], []
    if source.kind == "dataset":
        license_name = meta.get("license", "not stated")
        if license_name in ("not stated", "unknown"):
            bad.append(f"license {license_name}: check the dataset card before commercial use")
        else:
            good.append(f"license: {license_name}")
        downloads = meta.get("downloads")
        if isinstance(downloads, int):
            (good if downloads >= 1000 else bad).append(f"{downloads:,} downloads" + ("" if downloads >= 1000 else " (little community usage)"))
        if meta.get("tasks"):
            good.append("task tags: " + ", ".join(meta["tasks"]))
        else:
            bad.append("no task tag, so its suitability must be checked by hand")
        age = days_since(meta.get("last_modified"))
        if age is not None and age > STALE_AFTER_DAYS:
            bad.append(f"last updated {meta['last_modified']}")
        if meta.get("gated"):
            bad.append("gated: access terms must be accepted first")
        if meta.get("size_category") not in (None, "not stated"):
            good.append(f"size category {meta['size_category']}")
        languages = meta.get("languages") or []
        if languages and not {code.lower() for code in languages} & {"en", "eng", "english"}:
            bad.append(f"not an English dataset (language tag: {', '.join(languages)})")
        elif languages:
            good.append(f"languages: {', '.join(languages)}")
        else:
            bad.append("no language tag, so its language must be checked by hand")
    elif source.kind in ("repository", "repository_detail"):
        stars = meta.get("stars")
        if isinstance(stars, int):
            (good if stars >= 100 else bad).append(f"{stars:,} stars" + ("" if stars >= 100 else " (small community)"))
        license_name = meta.get("license", "not stated")
        (bad if license_name == "not stated" else good).append("no license stated: reuse rights are unclear" if license_name == "not stated" else f"license: {license_name}")
        if meta.get("possibly_stale"):
            bad.append(f"possibly stale: last push {meta.get('last_push')}")
        elif meta.get("last_push"):
            good.append(f"recently active: last push {meta['last_push']}")
        if source.kind == "repository_detail":
            good.append("README and setup files were read" if meta.get("readme_available") else "inspected, but it has no README")
            if meta.get("dependency_file"):
                good.append(f"dependency file: {meta['dependency_file']}")
    else:
        if meta.get("looks_like_documentation"):
            good.append("the URL pattern suggests documentation or a guide (not verified as official)")
        else:
            bad.append("general web page, not necessarily official documentation")
    return good, bad


def _link(source: Source) -> str:
    return f"[{source.title.replace('[', '(').replace(']', ')')}]({source.url})"


def section_c(plan: ResearchPlan | None, ledger: dict[str, Source], unavailable: dict[str, str]) -> str:
    groups = (
        ("Datasets", "dataset", plan is not None and not plan.needs_datasets, "search_huggingface_datasets"),
        ("GitHub repositories", ("repository", "repository_detail"), plan is not None and not plan.needs_github_examples, "search_github_repositories"),
        ("Documentation and web resources", "web_page", False, "search_web"),
    )
    parts: list[str] = []
    for heading, kinds, not_needed, tool in groups:
        kinds = (kinds,) if isinstance(kinds, str) else kinds
        members = [s for s in ledger.values() if s.kind in kinds]
        parts.append(f"### {heading}")
        if not members:
            if not_needed:
                parts.append("Not needed for this project.")
            elif tool in unavailable:
                parts.append(f"Not researched: {tool} was unavailable ({unavailable[tool]}).")
            else:
                parts.append("Nothing relevant was retrieved.")
            continue
        for source in members:
            good, bad = assess(source)
            facts = f"{_link(source)} [{source.id}]"
            if source.summary:
                facts += f" - {source.summary}"
            parts.append(f"- {facts}")
            if good:
                parts.append(f"  - Advantages: {'; '.join(good)}")
            if bad:
                parts.append(f"  - Limitations: {'; '.join(bad)}")
            if source.detail:
                parts.append(f"  - From the repository: {truncate(source.detail, 420)}")
    return "\n".join(parts)


def build_limitations(state: AgentState, deps: AgentDeps) -> list[str]:
    limitations: list[str] = []
    for tool, reason in state["unavailable"].items():
        if tool == "search_web" and reason == "not_configured":
            limitations.append(
                "Web search was not configured (TAVILY_API_KEY is not set), so documentation, setup and "
                "architecture guidance could not be verified against web sources."
            )
        else:
            limitations.append(f"{tool} was unavailable during this run ({reason}).")
    for execution in state["history"]:
        if execution.status == "error" and execution.tool not in state["unavailable"]:
            limitations.append(f"Step {execution.step} ({execution.tool}) failed: {execution.error.message}")
    reasons = {
        "max_iterations": f"Research stopped at the iteration limit ({deps.settings.max_iterations} turns).",
        "max_tool_calls": f"Research stopped at the tool-call limit ({deps.settings.max_tool_calls} calls).",
        "run_timeout": "Research stopped because the time budget for the run was used up.",
        "no_progress": "Research stopped because several tool rounds in a row returned nothing new.",
        "agent_no_output": "Research stopped because the model produced no usable output.",
        "no_tools_available": "Research stopped because no research tool was available.",
    }
    if state.get("stop_reason") in reasons:
        limitations.append(reasons[state["stop_reason"]])
    evaluation = state.get("evaluation")
    if evaluation:
        for item in evaluation.items:
            if item.status in ("missing", "weak", "unavailable"):
                limitations.append(f"Not fully covered - {item.label}: {item.detail}")
    flagged = [s.id for s in state["sources"].values() if "possible_prompt_injection" in s.flags]
    if flagged:
        limitations.append(
            f"Instruction-like text was found and removed in {len(flagged)} retrieved source(s) ({', '.join(flagged)}); "
            "retrieved content is treated as data, never as instructions."
        )
    limitations.extend(state.get("notes", []))
    return limitations


def section_g(plan: ResearchPlan | None, ledger: dict[str, Source], limitations: list[str]) -> str:
    parts = ["### Verified facts: the sources retrieved by the tools"]
    if ledger:
        parts.append("Every URL below was returned by a research tool during this run. Metadata (stars, downloads, licenses, dates) is copied from the API responses.")
        for source in ledger.values():
            parts.append(f"- [{source.id}] ({source.kind.replace('_', ' ')}) {_link(source)}")
    else:
        parts.append("No sources were retrieved.")
    parts += ["", "### Assumptions"]
    assumptions = list(plan.assumptions) if plan else []
    assumptions.append("The requirements in section A are the model's reading of your request.")
    parts += [f"- {item}" for item in assumptions]
    parts += ["", "### Not verified, missing or unavailable"]
    parts += [f"- {item}" for item in limitations] or ["- Nothing was reported as missing."]
    parts += [
        "- Sections B, D, E and F are model-written recommendations. They are not verified facts, even where they cite a source.",
        "- No command in this report was executed, and no installation or repository was tested.",
    ]
    return "\n".join(parts)


# ----------------------------------------------------------------------------- assembly


def render_markdown(title: str, sections: list[ReportSection]) -> str:
    parts = [f"# {title}", "", BANNER]
    for section in sections:
        parts += ["", f"## {section.id}. {section.title}", "", ORIGIN_NOTES[section.origin], "", section.content]
    return "\n".join(parts).strip() + "\n"


def generate_report(state: AgentState, deps: AgentDeps) -> tuple[TechnicalReport, list[dict[str, Any]]]:
    plan, ledger = state.get("plan"), state["sources"]
    stats: list[dict[str, Any]] = []
    validation = ReportValidation()
    limitations = build_limitations(state, deps)

    generated: dict[str, str] = {}
    for number, letter in enumerate(MODEL_SECTIONS, start=1):
        deps.say(f"[report] writing section {letter} ({TITLES[letter]}), {number} of {len(MODEL_SECTIONS)} (about 40-150 s) ...")
        section_started = time.perf_counter()
        text, reason = write_model_section(letter, state, deps, stats)
        deps.say(f"[report] section {letter} {'written' if text else 'NOT written'} in {time.perf_counter() - section_started:.0f} s")
        if text is None:
            validation.sections_not_generated.append(letter)
            limitations.append(f"Section {letter} ({TITLES[letter]}) could not be generated: {reason}.")
            generated[letter] = f"_This section could not be generated: {reason}. The retrieved evidence is in sections C and G._"
            continue
        text, urls, citations = clean_generated(text, ledger)
        text, claims = check_claims(text, ledger)
        validation.removed_urls += urls
        validation.removed_citations += citations
        validation.unverified_claims += claims
        generated[letter] = text + (f"\n\n{COMMANDS_NOTE}" if letter in ("E", "F") else "")
    if validation.removed_urls:
        limitations.append(f"{len(validation.removed_urls)} link(s) written by the model were removed because they were not retrieved by any tool.")
    if validation.removed_citations:
        limitations.append(f"{len(validation.removed_citations)} citation(s) to unknown sources were removed from model-written sections.")
    if validation.unverified_claims:
        limitations.append(
            f"{len(validation.unverified_claims)} statement(s) in model-written sections do not match the source they cite "
            "(license, download or star count, or the name of the source) and are marked [CHECK]."
        )

    sections = [
        ReportSection(id="A", title=TITLES["A"], content=section_a(plan), origin="derived_from_request"),
        ReportSection(id="B", title=TITLES["B"], content=generated["B"], origin="model_recommendation"),
        ReportSection(id="C", title=TITLES["C"], content=section_c(plan, ledger, state["unavailable"]), origin="tool_evidence"),
        ReportSection(id="D", title=TITLES["D"], content=generated["D"], origin="model_recommendation"),
        ReportSection(id="E", title=TITLES["E"], content=generated["E"], origin="model_recommendation"),
        ReportSection(id="F", title=TITLES["F"], content=generated["F"], origin="model_recommendation"),
        ReportSection(id="G", title=TITLES["G"], content=section_g(plan, ledger, limitations), origin="tool_evidence"),
    ]
    title = "Technical implementation guide" + (f": {short_title(plan.objective)}" if plan else "")
    report = TechnicalReport(
        title=title, sections=sections, markdown=render_markdown(title, sections), limitations=limitations, validation=validation
    )
    return report, stats


def short_title(text: str, limit: int = 90) -> str:
    """The objective as a title: cut at a word boundary, never in the middle of a word."""
    text = text.strip().rstrip(".")
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:-") + "..."


def build_response(state: AgentState, deps: AgentDeps) -> ResearchResponse:
    """The API payload for a finished run."""
    return ResearchResponse(
        project_description=state["request"],
        stop_reason=state.get("stop_reason") or "unknown",
        plan=state.get("plan"),
        report=state["report"],
        sources=list(state["sources"].values()),
        tool_history=list(state["history"]),
        evaluation=state.get("evaluation"),
        stats=RunStats(
            model=deps.settings.ollama_model,
            elapsed_seconds=round(deps.elapsed(state), 1),
            agent_turns=state["iteration"],
            tool_calls_executed=state["tool_calls_made"],
            llm_calls=state["llm_calls"],
        ),
    )
