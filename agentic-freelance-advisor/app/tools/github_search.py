"""GitHub tools: repository search and repository inspection, through the GitHub REST API.

Nothing is cloned or executed. Only public metadata, the README and one dependency file are read.
"""

import re
import time
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.schemas.research import ErrorCode, EvidenceItem, ToolResult
from app.tools.common import (
    clean_query,
    days_since,
    error_from_exception,
    failure,
    make_client,
    retry_after_from_headers,
    sanitize_untrusted,
    to_date,
    truncate,
)

SEARCH_TOOL = "search_github_repositories"
INSPECT_TOOL = "inspect_github_repository"
GITHUB_API = "https://api.github.com"
STALE_AFTER_DAYS = 730
DEPENDENCY_FILES = (
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "environment.yaml",
    "Pipfile",
    "setup.py",
    "package.json",
    "pubspec.yaml",  # Dart / Flutter
    "composer.json",  # PHP / Laravel / WordPress
    "pom.xml",  # Java / Maven
    "build.gradle",
    "build.gradle.kts",  # Java, Kotlin, Android / Gradle
    "Cargo.toml",  # Rust
    "go.mod",  # Go
    "Gemfile",  # Ruby / Rails
    "Package.swift",  # Swift
)

_NAME_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_HEADING = re.compile(r"^\s{0,3}#{1,4}\s+(.+?)\s*#*\s*$", re.MULTILINE)
_SETUP_HEADING = re.compile(
    r"install|setup|set up|usage|getting started|quick ?start|requirements|dependenc|dataset|train|run", re.I
)


def _headers(settings: Settings, *, raw: bool = False) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token is not None:
        headers["Authorization"] = f"Bearer {settings.github_token.get_secret_value()}"
    return headers


def _api_message(response: httpx.Response) -> str:
    try:
        return str(response.json().get("message", ""))
    except ValueError:
        return ""


def _github_error(response: httpx.Response, settings: Settings) -> tuple[ErrorCode, str, int | None]:
    status = response.status_code
    message = _api_message(response)
    if status in (403, 429) and (
        response.headers.get("x-ratelimit-remaining") == "0"
        or "rate limit" in message.lower()
        or response.headers.get("retry-after")
    ):
        hint = "" if settings.github_token else " Add GITHUB_TOKEN to .env for much higher limits."
        return (
            "rate_limited",
            f"GitHub rate limit reached.{hint}",
            retry_after_from_headers(response.headers),
        )
    if status == 401:
        return "auth_failed", "GitHub rejected GITHUB_TOKEN (invalid or expired).", None
    if status == 404:
        return "not_found", "GitHub returned 404: the repository does not exist or is private.", None
    if status == 422:
        return "invalid_input", f"GitHub rejected the query: {truncate(message, 120)}", None
    if status == 403:
        return "http_error", "GitHub refused the request (HTTP 403).", None
    return "http_error", f"GitHub returned HTTP {status}.", None


def _license_name(repo: dict[str, Any]) -> str:
    license_info = repo.get("license")
    if isinstance(license_info, dict):
        return license_info.get("spdx_id") or license_info.get("name") or "not stated"
    return "not stated"


def _repo_metadata(repo: dict[str, Any]) -> dict[str, Any]:
    pushed = to_date(repo.get("pushed_at"))
    age = days_since(pushed)
    return {
        "full_name": repo.get("full_name"),
        "stars": repo.get("stargazers_count"),
        "forks": repo.get("forks_count"),
        "language": repo.get("language") or "not stated",
        "license": _license_name(repo),
        "topics": (repo.get("topics") or [])[:6],
        "last_push": pushed,
        "days_since_last_push": age,
        "possibly_stale": age is not None and age > STALE_AFTER_DAYS,
        "open_issues": repo.get("open_issues_count"),
    }


def search_github_repositories(query: str, settings: Settings | None = None) -> ToolResult:
    """Search public GitHub repositories, best match first, without forks and archived repositories."""
    settings = settings or get_settings()
    arguments = {"query": query}
    try:
        query = clean_query(query)
    except ValueError as error:
        return failure(SEARCH_TOOL, arguments, "invalid_input", str(error))

    try:
        with make_client(settings.tool_timeout_seconds) as client:
            response = client.get(
                f"{GITHUB_API}/search/repositories",
                params={"q": query, "per_page": 30},
                headers=_headers(settings),
            )
    except httpx.HTTPError as error:
        code, message = error_from_exception(error, "GitHub")
        return failure(SEARCH_TOOL, arguments, code, message)
    if response.status_code != 200:
        code, message, retry_after = _github_error(response, settings)
        return failure(SEARCH_TOOL, arguments, code, message, retry_after)
    try:
        payload = response.json()
    except ValueError:
        return failure(SEARCH_TOOL, arguments, "unexpected", "GitHub returned a response that is not valid JSON.")

    items: list[EvidenceItem] = []
    for repo in payload.get("items") or []:
        if repo.get("fork") or repo.get("archived") or not repo.get("html_url"):
            continue
        description, flagged = sanitize_untrusted(repo.get("description"), 200)
        items.append(
            EvidenceItem(
                kind="repository",
                title=repo.get("full_name") or "unknown repository",
                url=repo["html_url"],
                summary=description,
                metadata=_repo_metadata(repo),
                flags=["possible_prompt_injection"] if flagged else [],
            )
        )
    # The 30 best matches are all relevant; among them the popular ones are the more useful examples. Best-match
    # order alone returned five repositories with 0-3 stars and no license while a 639-star one was ranked lower.
    items.sort(key=lambda item: -(item.metadata.get("stars") or 0))
    items = items[: settings.max_results_per_tool]

    notes = [f"{payload.get('total_count', 0)} repositories match; showing the {len(items)} most starred of the 30 best matches."]
    if not items:
        notes.append("No usable repositories found; try different or fewer keywords.")
    return ToolResult(tool=SEARCH_TOOL, arguments=arguments, ok=True, items=items, notes=notes)


def summarize_readme(text: str, max_chars: int = 900) -> str:
    """Headings, the opening paragraph and the install/usage passages of a README, sanitised."""
    headings = [h.strip() for h in _HEADING.findall(text)][:12]
    parts: list[str] = []
    flagged_any = False

    body = _HEADING.sub("", text)
    for paragraph in re.split(r"\n\s*\n", body):
        candidate, flagged = sanitize_untrusted(paragraph, 300)
        flagged_any |= flagged
        if len(candidate) >= 60:
            parts.append(f"Intro: {candidate}")
            break

    for match in _HEADING.finditer(text):
        if len(parts) >= 3:
            break
        if _SETUP_HEADING.search(match.group(1)):
            following, flagged = sanitize_untrusted(text[match.end() : match.end() + 500], 220)
            flagged_any |= flagged
            if following:
                parts.append(f"Section '{match.group(1).strip()}': {following}")

    if headings:
        parts.insert(0, "Headings: " + "; ".join(sanitize_untrusted(h, 50)[0] for h in headings))
    summary = " | ".join(parts)
    return truncate(summary + (" [injection-like text removed]" if flagged_any else ""), max_chars)


def inspect_github_repository(owner: str, repo: str, settings: Settings | None = None) -> ToolResult:
    """Read metadata, the README and one dependency file of a public repository."""
    settings = settings or get_settings()
    arguments = {"owner": owner, "repo": repo}
    if not (isinstance(owner, str) and isinstance(repo, str) and _NAME_PART.match(owner) and _NAME_PART.match(repo)):
        return failure(INSPECT_TOOL, arguments, "invalid_input", "owner and repo must be plain GitHub names.")

    base = f"{GITHUB_API}/repos/{owner}/{repo}"
    deadline = time.monotonic() + settings.tool_timeout_seconds * 2
    notes: list[str] = []

    try:
        with make_client(settings.tool_timeout_seconds) as client:
            meta_response = client.get(base, headers=_headers(settings))
            if meta_response.status_code != 200:
                code, message, retry_after = _github_error(meta_response, settings)
                return failure(INSPECT_TOOL, arguments, code, message, retry_after)
            meta = meta_response.json()

            readme_summary = ""
            readme_response = client.get(f"{base}/readme", headers=_headers(settings, raw=True))
            if readme_response.status_code == 200:
                readme_summary = summarize_readme(readme_response.text)
            elif readme_response.status_code == 404:
                notes.append("The repository has no README.")
            else:
                notes.append(f"README not read: {_github_error(readme_response, settings)[1]}")

            root_files: list[str] = []
            dependency_name = ""
            dependency_excerpt = ""
            if time.monotonic() < deadline:
                listing = client.get(f"{base}/contents", headers=_headers(settings))
                if listing.status_code == 200 and isinstance(listing.json(), list):
                    root_files = [entry.get("name", "") for entry in listing.json() if entry.get("name")]
                    dependency_name = next((name for name in DEPENDENCY_FILES if name in root_files), "")
                else:
                    notes.append(f"Root file list not read: {_github_error(listing, settings)[1]}")
            if dependency_name and time.monotonic() < deadline:
                dependency = client.get(f"{base}/contents/{dependency_name}", headers=_headers(settings, raw=True))
                if dependency.status_code == 200:
                    lines = [line.strip() for line in dependency.text.splitlines() if line.strip()]
                    lines = [line for line in lines if not line.startswith("#")][:15]
                    dependency_excerpt, _ = sanitize_untrusted(", ".join(lines), 400)
                else:
                    notes.append(f"{dependency_name} not read: {_github_error(dependency, settings)[1]}")
    except httpx.HTTPError as error:
        code, message = error_from_exception(error, "GitHub")
        return failure(INSPECT_TOOL, arguments, code, message)
    except ValueError:
        return failure(INSPECT_TOOL, arguments, "unexpected", "GitHub returned a response that is not valid JSON.")

    description, flagged = sanitize_untrusted(meta.get("description"), 200)
    detail_parts = []
    if readme_summary:
        detail_parts.append(f"README -> {readme_summary}")
    if root_files:
        detail_parts.append("Root files: " + ", ".join(root_files[:15]))
    if dependency_excerpt:
        detail_parts.append(f"{dependency_name} -> {dependency_excerpt}")
    metadata = _repo_metadata(meta)
    metadata.update(
        {
            "default_branch": meta.get("default_branch"),
            "readme_available": bool(readme_summary),
            "dependency_file": dependency_name or None,
            "root_files": root_files[:15],
        }
    )
    item = EvidenceItem(
        kind="repository_detail",
        title=meta.get("full_name") or f"{owner}/{repo}",
        url=meta.get("html_url") or f"https://github.com/{owner}/{repo}",
        summary=description,
        detail=" | ".join(detail_parts),
        metadata=metadata,
        flags=["possible_prompt_injection"] if flagged or "[injection-like" in readme_summary else [],
    )
    return ToolResult(tool=INSPECT_TOOL, arguments=arguments, ok=True, items=[item], notes=notes)
