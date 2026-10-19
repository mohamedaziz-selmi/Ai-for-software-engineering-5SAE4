"""Web search tool, backed by the Tavily Search API."""

from urllib.parse import urlparse

import httpx

from app.config import Settings, get_settings
from app.schemas.research import ErrorCode, EvidenceItem, ToolResult
from app.tools.common import (
    clean_query,
    error_from_exception,
    failure,
    make_client,
    retry_after_from_headers,
    sanitize_untrusted,
)

TOOL_NAME = "search_web"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
MISSING_KEY_MESSAGE = (
    "TAVILY_API_KEY is not set. Create a free key (1,000 credits/month, no credit card) "
    "at https://app.tavily.com and add it to .env."
)


def _looks_like_documentation(host: str, url: str, title: str) -> bool:
    path = urlparse(url).path.lower()
    lowered = title.lower()
    return (
        host.startswith(("docs.", "doc.", "developer.", "developers.", "learn."))
        or "readthedocs" in host
        or any(
            part in path
            for part in ("/docs", "/documentation", "/quickstart", "/reference", "/tutorial", "/user-guide",
                         "/getting-started", "/en/stable", "/en/latest", "/stable/", "/latest/")
        )
        or "documentation" in lowered
        or " docs" in f" {lowered}"
    )


def _tavily_error(status: int, headers: httpx.Headers) -> tuple[ErrorCode, str, int | None]:
    if status == 401:
        return "auth_failed", "Tavily rejected TAVILY_API_KEY (missing or invalid).", None
    if status == 429:
        return "rate_limited", "Tavily rate limit reached.", retry_after_from_headers(headers)
    if status in (432, 433):
        return "quota_exceeded", "The Tavily plan or usage limit has been exceeded.", None
    if status in (400, 422):
        return "invalid_input", f"Tavily rejected the request (HTTP {status}).", None
    return "http_error", f"Tavily returned HTTP {status}.", None


def search_web(query: str, settings: Settings | None = None) -> ToolResult:
    """Search the web through Tavily and return normalised, sanitised results."""
    settings = settings or get_settings()
    arguments = {"query": query}
    try:
        query = clean_query(query)
    except ValueError as error:
        return failure(TOOL_NAME, arguments, "invalid_input", str(error))
    if settings.tavily_api_key is None:
        return failure(TOOL_NAME, arguments, "not_configured", MISSING_KEY_MESSAGE)

    body = {
        "query": query,
        "search_depth": "basic",
        "max_results": settings.max_results_per_tool,
        "topic": "general",
        "include_answer": False,
    }
    headers = {"Authorization": f"Bearer {settings.tavily_api_key.get_secret_value()}"}
    try:
        with make_client(settings.tool_timeout_seconds, headers) as client:
            response = client.post(TAVILY_SEARCH_URL, json=body)
    except httpx.HTTPError as error:
        code, message = error_from_exception(error, "Tavily")
        return failure(TOOL_NAME, arguments, code, message)

    if response.status_code != 200:
        code, message, retry_after = _tavily_error(response.status_code, response.headers)
        return failure(TOOL_NAME, arguments, code, message, retry_after)
    try:
        results = response.json().get("results") or []
    except ValueError:
        return failure(TOOL_NAME, arguments, "unexpected", "Tavily returned a response that is not valid JSON.")

    items: list[EvidenceItem] = []
    seen_urls: set[str] = set()
    for result in results:
        url = result.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        host = urlparse(url).netloc.lower().removeprefix("www.")
        title, title_flagged = sanitize_untrusted(result.get("title"), 120)
        summary, summary_flagged = sanitize_untrusted(result.get("content"), 320)
        score = result.get("score")
        items.append(
            EvidenceItem(
                kind="web_page",
                title=title or host,
                url=url,
                summary=summary,
                metadata={
                    "domain": host,
                    "relevance_score": round(score, 2) if isinstance(score, (int, float)) else None,
                    "looks_like_documentation": _looks_like_documentation(host, url, title),
                },
                flags=["possible_prompt_injection"] if title_flagged or summary_flagged else [],
            )
        )
        if len(items) >= settings.max_results_per_tool:
            break

    # Low-scoring results are noise (a press release, a finance video): drop them, but always keep the best two.
    minimum = settings.web_min_relevance
    relevant = [
        item for position, item in enumerate(items)
        if position < 2 or item.metadata["relevance_score"] is None or item.metadata["relevance_score"] >= minimum
    ]
    notes = [] if items else ["No web results for this query; try different or more specific keywords."]
    if len(relevant) < len(items):
        notes.append(f"{len(items) - len(relevant)} low-relevance result(s) (Tavily score below {minimum}) were left out.")
    return ToolResult(tool=TOOL_NAME, arguments=arguments, ok=True, items=relevant, notes=notes)
