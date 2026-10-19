"""Call every research tool once against the REAL APIs and print what comes back (no LLM involved).

Run from the project root:
    uv run python -m scripts.try_tools
    uv run python -m scripts.try_tools --query "sentiment analysis REST API" --datasets "sentiment"

Web search needs TAVILY_API_KEY; without it that tool reports "not_configured" (which is expected).
GitHub inspection uses the first repository the GitHub search returns.
Exit code 0 when every tool either worked or reported a missing key.
"""

import argparse
import sys

from app.config import get_settings
from app.schemas.research import ToolResult
from app.tools.dataset_search import search_huggingface_datasets
from app.tools.github_search import inspect_github_repository, search_github_repositories
from app.tools.web_search import search_web


def show(result: ToolResult) -> bool:
    print(f"\n=== {result.tool}({result.arguments}) ===")
    if not result.ok:
        print(f"  ERROR {result.error.code}: {result.error.message}")
        if result.error.retry_after_seconds is not None:
            print(f"  retry after {result.error.retry_after_seconds}s")
        return result.error.code == "not_configured"
    print(f"  {len(result.items)} item(s)")
    for item in result.items[:5]:
        print(f"  - {item.title}\n    {item.url}")
        if item.summary:
            print(f"    {item.summary[:150]}")
        interesting = {k: v for k, v in item.metadata.items() if v not in (None, [], "")}
        print(f"    {interesting}")
        if item.detail:
            print(f"    detail: {item.detail[:300]}")
        if item.flags:
            print(f"    FLAGS: {item.flags}")
    for note in result.notes:
        print(f"  note: {note}")
    return True


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the Windows console is cp1252
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", default="fake news detection python")
    parser.add_argument("--datasets", default="fake news")
    args = parser.parse_args()

    settings = get_settings()
    outcomes = [
        show(search_web(args.query + " tutorial", settings)),
        show(search_huggingface_datasets(args.datasets, settings)),
    ]
    repositories = search_github_repositories(args.query, settings)
    outcomes.append(show(repositories))
    if repositories.ok and repositories.items:
        owner, name = repositories.items[0].title.split("/", 1)
        outcomes.append(show(inspect_github_repository(owner, name, settings)))
    print("\nResult:", "all tools behaved correctly" if all(outcomes) else "SOME TOOLS FAILED")
    return 0 if all(outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
