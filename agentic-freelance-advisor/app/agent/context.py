"""Builds the bounded text the LLM sees: evidence ledger updates, digests and tool observations.

The model has a 4096-token window shared by the prompt, the tool schemas and its own thinking.
Everything here therefore works with hard character budgets instead of replaying raw tool output.
"""

import re
from urllib.parse import urlsplit

from app.schemas.research import EvidenceItem, ResearchPlan, Source, ToolExecution, ToolResult
from app.tools.common import truncate

_WORDS = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset("a an the for of in on to and or with using use how best build create make guide".split())


def estimate_tokens(text: str) -> int:
    """Deliberately pessimistic token estimate (about 3 characters per token)."""
    return len(text) // 3 + 1


# ----------------------------------------------------------------------------- evidence ledger


def normalize_url(url: str) -> str:
    """Key for de-duplicating sources: host and path, case-insensitive, no query or fragment."""
    parts = urlsplit(url.strip())
    return f"{parts.netloc.lower().removeprefix('www.')}{parts.path.rstrip('/')}".lower()


def register_items(
    sources: dict[str, Source], items: list[EvidenceItem], step: int
) -> tuple[dict[str, Source], list[str], list[str]]:
    """Add items to the ledger. Returns (new ledger, ids of all items, ids that are new).

    The same URL found twice keeps one id; its metadata, detail and flags are merged.
    """
    ledger = {sid: source.model_copy(deep=True) for sid, source in sources.items()}
    index = {normalize_url(source.url): sid for sid, source in ledger.items()}
    all_ids: list[str] = []
    new_ids: list[str] = []
    for item in items:
        key = normalize_url(item.url)
        if key in index:
            sid = index[key]
            existing = ledger[sid]
            existing.metadata = {**existing.metadata, **item.metadata}
            existing.summary = existing.summary or item.summary
            existing.detail = existing.detail or item.detail
            existing.flags = sorted(set(existing.flags) | set(item.flags))
            if item.kind == "repository_detail":
                existing.kind = "repository_detail"
            if step not in existing.found_by:
                existing.found_by.append(step)
        else:
            sid = f"S{len(ledger) + 1}"
            ledger[sid] = Source(**item.model_dump(), id=sid, found_by=[step])
            index[key] = sid
            new_ids.append(sid)
        if sid not in all_ids:
            all_ids.append(sid)
    return ledger, all_ids, new_ids


def count_enriched(before: dict[str, Source], after: dict[str, Source], ids: list[str]) -> int:
    """Known sources that gained README / dependency detail in this round (a repository inspection).

    That is real progress even though no new source id appeared, so it must not count as an idle round.
    """
    return sum(1 for sid in ids if sid in before and not before[sid].detail and after[sid].detail)


# ----------------------------------------------------------------------------- redundancy


def _query_tokens(text: str) -> frozenset[str]:
    return frozenset(word.rstrip("s") for word in _WORDS.findall(text.lower()) if word not in _STOPWORDS)


def find_redundant_call(tool: str, arguments: dict, history: list[ToolExecution]) -> ToolExecution | None:
    """An earlier successful call that makes this one pointless: identical or near-identical."""
    for previous in history:
        if previous.tool != tool or previous.status != "ok":
            continue
        if tool == "inspect_github_repository":
            same = (
                str(arguments.get("owner", "")).lower() == str(previous.arguments.get("owner", "")).lower()
                and str(arguments.get("repo", "")).lower() == str(previous.arguments.get("repo", "")).lower()
            )
            if same:
                return previous
            continue
        new_tokens = _query_tokens(str(arguments.get("query", "")))
        old_tokens = _query_tokens(str(previous.arguments.get("query", "")))
        if not new_tokens or not old_tokens:
            continue
        overlap = len(new_tokens & old_tokens) / len(new_tokens | old_tokens)
        if overlap >= 0.8:
            return previous
    return None


# ----------------------------------------------------------------------------- rendering


def source_line(source: Source, width: int = 170) -> str:
    meta = source.metadata
    if source.kind == "dataset":
        facts = [
            f"{meta.get('downloads')} downloads" if meta.get("downloads") is not None else None,
            f"license {meta.get('license', 'not stated')}",
            f"tasks {','.join(meta['tasks'])}" if meta.get("tasks") else None,
            f"lang {','.join(meta['languages'])}" if meta.get("languages") else None,
        ]
        label = "dataset"
    elif source.kind in ("repository", "repository_detail"):
        facts = [
            f"{meta.get('stars')} stars",
            str(meta.get("language", "")),
            f"license {meta.get('license', 'not stated')}",
            f"pushed {meta.get('last_push')}" + (" (stale)" if meta.get("possibly_stale") else ""),
            "README+setup inspected" if source.kind == "repository_detail" else None,
        ]
        label = "repo"
    else:
        facts = [meta.get("domain"), "documentation" if meta.get("looks_like_documentation") else None]
        label = "web"
    head = f"{source.id} [{label}] {truncate(source.title, 60)} | " + ", ".join(f for f in facts if f)
    if source.flags:
        head += " | FLAGGED"
    remaining = width - len(head) - 3
    if source.summary and remaining > 25:
        head += " | " + truncate(source.summary, remaining)
    return truncate(head, width)


def _arguments_text(arguments: dict) -> str:
    return ", ".join(f"{key}={value!r}" for key, value in arguments.items())


def _execution_lines(execution: ToolExecution, sources: dict[str, Source], detailed: bool) -> list[str]:
    header = f"#{execution.step} {execution.tool}({_arguments_text(execution.arguments)})"
    if execution.status == "skipped":
        return [f"{header} -> SKIPPED ({execution.error.code}): {truncate(execution.error.message, 110)}"]
    if execution.status == "error":
        return [f"{header} -> FAILED ({execution.error.code}): {truncate(execution.error.message, 110)}"]
    ids = execution.source_ids
    if not ids:
        return [f"{header} -> 0 results. {truncate(' '.join(execution.notes), 110)}"]
    if not detailed:
        return [f"{header} -> {len(ids)} result(s): {', '.join(ids)}"]
    return [f"{header} -> {len(ids)} result(s)"] + [f"   {source_line(sources[sid])}" for sid in ids if sid in sources]


def render_digest(history: list[ToolExecution], sources: dict[str, Source], max_chars: int = 2400) -> str:
    """What has been researched so far. The last executions are detailed, older ones one line each."""
    if not history:
        return "Nothing has been researched yet."
    for detailed_count in (2, 1, 0):
        lines: list[str] = []
        for index, execution in enumerate(history):
            lines.extend(_execution_lines(execution, sources, index >= len(history) - detailed_count))
        text = "\n".join(lines)
        if len(text) <= max_chars:
            return text
    return "...\n" + text[-(max_chars - 4) :]


def render_observation(execution: ToolExecution, result: ToolResult | None, sources: dict[str, Source]) -> str:
    """Text of the ToolMessage for one call. Retrieved content is fenced as untrusted data."""
    header = f"Step {execution.step}: {execution.tool}({_arguments_text(execution.arguments)})"
    if execution.status != "ok":
        return f"{header}\n{_execution_lines(execution, sources, True)[0].split('-> ', 1)[1]}"
    lines = [source_line(sources[sid]) for sid in execution.source_ids if sid in sources]
    body = "\n".join(lines) if lines else "(no results)"
    notes = f"\nNotes: {' '.join(execution.notes)}" if execution.notes else ""
    return f"{header}\n<untrusted_data>\n{body}\n</untrusted_data>{notes}"


def render_plan(plan: ResearchPlan) -> str:
    """The plan as the short text the agent prompt carries."""
    topics = "; ".join(truncate(topic, 50) for topic in plan.key_topics[:5])
    datasets = "yes" if plan.needs_datasets else "no"
    examples = "yes" if plan.needs_github_examples else "no"
    return (
        f"Objective: {truncate(plan.objective, 220)}\n"
        f"Needs datasets: {datasets}. Needs GitHub examples: {examples}.\n"
        f"Topics: {topics}"
    )
