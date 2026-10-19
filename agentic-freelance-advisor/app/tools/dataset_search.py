"""Hugging Face dataset search. Reads Hub metadata only; no dataset is ever downloaded."""

import re
from typing import Any

import httpx
from huggingface_hub import HfApi
from huggingface_hub.errors import HfHubHTTPError

from app.config import Settings, get_settings
from app.schemas.research import ErrorCode, EvidenceItem, ToolResult
from app.tools.common import (
    clean_query,
    error_from_exception,
    failure,
    retry_after_from_headers,
    sanitize_untrusted,
    to_date,
)

TOOL_NAME = "search_huggingface_datasets"
HUB_DATASET_URL = "https://huggingface.co/datasets/"
_TEMPLATE_TEXT = re.compile(
    r"^TODO\b|add yaml tags|dataset card aims to be a base template|^\W*\[?more information needed", re.IGNORECASE
)
_ENGLISH = {"en", "eng", "english"}
_LANGUAGE_NAMES = (
    "spanish", "french", "german", "arabic", "chinese", "hindi", "portuguese", "italian", "russian", "japanese",
    "korean", "turkish", "dutch", "polish", "indonesian", "vietnamese", "filipino", "tagalog", "urdu", "bengali",
    "persian", "hebrew", "greek", "swedish", "ukrainian", "czech", "thai", "malay", "swahili", "multilingual",
)
EXPAND_FIELDS = ["author", "cardData", "description", "downloads", "likes", "lastModified", "tags", "gated"]


def _tag_values(tags: list[str], prefix: str) -> list[str]:
    return [tag.split(":", 1)[1] for tag in tags if tag.startswith(prefix)]


def _license(card_data: Any, tags: list[str]) -> str:
    """The declared license, or 'not stated'. The card can hold a string or a list."""
    value: Any = None
    if card_data is not None:
        try:
            value = card_data.get("license")
        except AttributeError:
            value = getattr(card_data, "license", None)
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(part) for part in value)
    if not value:
        from_tags = _tag_values(tags, "license:")
        value = ", ".join(from_tags) if from_tags else None
    return str(value) if value else "not stated"


def _other_language(dataset_id: str, tags: list[str]) -> str | None:
    """Why a dataset is not an English one, or None. Tags are trusted first, then the name (many cards carry no tag)."""
    languages = {code.lower() for code in _tag_values(tags, "language:")}
    if languages and not languages & _ENGLISH:
        return f"tagged {', '.join(sorted(languages))}"
    name = dataset_id.lower()
    return next((f"named after {word}" for word in _LANGUAGE_NAMES if word in name), None)


def _hub_error(error: HfHubHTTPError) -> tuple[ErrorCode, str, int | None]:
    status = getattr(error.response, "status_code", None)
    if status in (401, 403):
        return "auth_failed", "Hugging Face rejected the request (check HF_TOKEN).", None
    if status == 429:
        headers = getattr(error.response, "headers", httpx.Headers())
        return "rate_limited", "Hugging Face rate limit reached.", retry_after_from_headers(headers)
    return "http_error", f"Hugging Face returned HTTP {status}.", None


def search_huggingface_datasets(query: str, settings: Settings | None = None) -> ToolResult:
    """Search dataset metadata on the Hugging Face Hub, most downloaded first."""
    settings = settings or get_settings()
    arguments = {"query": query}
    try:
        query = clean_query(query)
    except ValueError as error:
        return failure(TOOL_NAME, arguments, "invalid_input", str(error))

    token = settings.hf_token.get_secret_value() if settings.hf_token else None
    english_only = settings.dataset_language == "en" and not any(word in query.lower() for word in _LANGUAGE_NAMES)
    try:
        datasets = list(
            HfApi(token=token).list_datasets(
                search=query, sort="downloads", expand=EXPAND_FIELDS,
                # ask for more than needed: some of the most downloaded ones will be filtered out below
                limit=settings.max_results_per_tool * (4 if english_only else 1),
            )
        )
    except HfHubHTTPError as error:
        code, message, retry_after = _hub_error(error)
        return failure(TOOL_NAME, arguments, code, message, retry_after)
    except httpx.HTTPError as error:
        code, message = error_from_exception(error, "Hugging Face")
        return failure(TOOL_NAME, arguments, code, message)
    except Exception as error:  # noqa: BLE001 - the library can raise other types; never crash the agent
        return failure(TOOL_NAME, arguments, "unexpected", f"Hugging Face search failed: {type(error).__name__}: {error}")

    left_out: list[str] = []
    if english_only:
        english = []
        for dataset in datasets:
            reason = _other_language(dataset.id, list(dataset.tags or []))
            if reason:
                left_out.append(f"{dataset.id} ({reason})")
            else:
                english.append(dataset)
        datasets = english
    datasets = datasets[: settings.max_results_per_tool]

    items: list[EvidenceItem] = []
    for dataset in datasets:
        tags = list(dataset.tags or [])
        description, flagged = sanitize_untrusted(dataset.description, 200)
        if _TEMPLATE_TEXT.search(description):
            description = ""  # an unfilled dataset-card template says nothing about the dataset
        license_name = _license(dataset.card_data, tags)
        items.append(
            EvidenceItem(
                kind="dataset",
                title=dataset.id,
                url=f"{HUB_DATASET_URL}{dataset.id}",
                summary=description,
                metadata={
                    "downloads": dataset.downloads,
                    "likes": dataset.likes,
                    "last_modified": to_date(dataset.last_modified),
                    "license": license_name,
                    "tasks": _tag_values(tags, "task_categories:")[:3],
                    "languages": _tag_values(tags, "language:")[:4],
                    "size_category": next(iter(_tag_values(tags, "size_categories:")), "not stated"),
                    "gated": bool(dataset.gated),
                },
                flags=["possible_prompt_injection"] if flagged else [],
            )
        )

    notes = []
    if left_out:
        notes.append(
            f"{len(left_out)} dataset(s) in other languages were left out: {'; '.join(left_out[:4])}. "
            "Name a language in the query, or set DATASET_LANGUAGE=any, to include them."
        )
    if not items:
        notes.append(
            "No datasets matched. The Hub searches dataset names, so use short keywords "
            "(for example 'fake news' or 'sentiment') rather than a full sentence."
        )
    return ToolResult(tool=TOOL_NAME, arguments=arguments, ok=True, items=items, notes=notes)
