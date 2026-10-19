"""The research tools, exposed to the LLM as LangChain tools.

Each tool is a plain function that returns a `ToolResult` (see the modules in this package).
The LangChain wrapper only adds the name, description and argument schema the model sees.
"""

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.tools.dataset_search import search_huggingface_datasets
from app.tools.github_search import inspect_github_repository, search_github_repositories
from app.tools.web_search import search_web

WEB_SEARCH = "search_web"
GITHUB_SEARCH = "search_github_repositories"
GITHUB_INSPECT = "inspect_github_repository"
DATASET_SEARCH = "search_huggingface_datasets"
TOOL_NAMES = (WEB_SEARCH, GITHUB_SEARCH, GITHUB_INSPECT, DATASET_SEARCH)


class WebSearchInput(BaseModel):
    query: str = Field(description="Specific technical search query, e.g. 'scikit-learn text classification tutorial'.")


class GithubSearchInput(BaseModel):
    query: str = Field(description="Short keywords describing the project, e.g. 'fake news detection python'.")


class GithubInspectInput(BaseModel):
    owner: str = Field(description="Repository owner exactly as it appears in a search result.")
    repo: str = Field(description="Repository name exactly as it appears in a search result.")


class DatasetSearchInput(BaseModel):
    query: str = Field(description="One or two short keywords, e.g. 'fake news' or 'sentiment'. Not a sentence.")


def build_tools(settings: Settings | None = None) -> dict[str, StructuredTool]:
    """Create the LangChain tools, bound to the given settings."""
    settings = settings or get_settings()
    return {
        WEB_SEARCH: StructuredTool.from_function(
            func=lambda query: search_web(query, settings),
            name=WEB_SEARCH,
            description=(
                "Search the web for official documentation, framework and library guides, installation and "
                "configuration instructions, and implementation approaches. Returns titles, URLs and snippets."
            ),
            args_schema=WebSearchInput,
        ),
        GITHUB_SEARCH: StructuredTool.from_function(
            func=lambda query: search_github_repositories(query, settings),
            name=GITHUB_SEARCH,
            description=(
                "Search public GitHub repositories for open-source implementations of a similar project. "
                "Returns name, URL, description, language, stars, license and last update."
            ),
            args_schema=GithubSearchInput,
        ),
        GITHUB_INSPECT: StructuredTool.from_function(
            func=lambda owner, repo: inspect_github_repository(owner, repo, settings),
            name=GITHUB_INSPECT,
            description=(
                "Inspect ONE repository that a GitHub search already returned: its README outline, setup "
                "instructions and dependency file. Use it only when a repository looks genuinely useful."
            ),
            args_schema=GithubInspectInput,
        ),
        DATASET_SEARCH: StructuredTool.from_function(
            func=lambda query: search_huggingface_datasets(query, settings),
            name=DATASET_SEARCH,
            description=(
                "Search Hugging Face Hub dataset metadata (the search matches dataset names). Returns dataset id, "
                "URL, downloads, likes, license, tasks and languages. Never downloads data."
            ),
            args_schema=DatasetSearchInput,
        ),
    }


def unconfigured_tools(settings: Settings | None = None) -> dict[str, str]:
    """Tools that cannot work right now (missing API key), mapped to the reason."""
    return {entry["name"]: "not_configured" for entry in tool_status(settings) if not entry["configured"]}


def tool_status(settings: Settings | None = None) -> list[dict[str, Any]]:
    """Name, purpose and configuration status of each tool, for the /tools endpoint."""
    settings = settings or get_settings()
    github_note = (
        "Authenticated with GITHUB_TOKEN (30 search requests/min)."
        if settings.github_token
        else "No GITHUB_TOKEN: works, but limited to 10 search requests/min and 60 other requests/hour."
    )
    tools = build_tools(settings)
    return [
        {
            "name": WEB_SEARCH,
            "description": tools[WEB_SEARCH].description,
            "provider": "Tavily",
            "requires_key": True,
            "configured": settings.tavily_api_key is not None,
            "note": "Ready."
            if settings.tavily_api_key
            else "TAVILY_API_KEY is not set. Free key at https://app.tavily.com",
        },
        {
            "name": GITHUB_SEARCH,
            "description": tools[GITHUB_SEARCH].description,
            "provider": "GitHub REST API",
            "requires_key": False,
            "configured": True,
            "note": github_note,
        },
        {
            "name": GITHUB_INSPECT,
            "description": tools[GITHUB_INSPECT].description,
            "provider": "GitHub REST API",
            "requires_key": False,
            "configured": True,
            "note": github_note,
        },
        {
            "name": DATASET_SEARCH,
            "description": tools[DATASET_SEARCH].description,
            "provider": "Hugging Face Hub",
            "requires_key": False,
            "configured": True,
            "note": "Authenticated with HF_TOKEN." if settings.hf_token else "Anonymous access works for public metadata.",
        },
    ]
