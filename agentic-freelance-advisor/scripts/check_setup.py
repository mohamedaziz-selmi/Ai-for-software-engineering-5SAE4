"""Verify the local setup without needing the Ollama model.

Run from the project root:  uv run python -m scripts.check_setup

Exit code 0 when the dependencies import and the configuration loads.
A missing key, an unreachable Ollama or a model that is not pulled yet are warnings.
"""

import sys
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version

from app.agent.llm import ollama_status
from app.config import PROJECT_ROOT, get_settings

# distribution name -> (module, attribute the project relies on)
DEPENDENCIES = {
    "langgraph": ("langgraph.graph", "StateGraph"),
    "langchain": ("langchain.messages", "AIMessage"),
    "langchain-core": ("langchain_core.tools", "tool"),
    "langchain-ollama": ("langchain_ollama", "ChatOllama"),
    "fastapi": ("fastapi", "FastAPI"),
    "uvicorn": ("uvicorn", "run"),
    "pydantic": ("pydantic", "BaseModel"),
    "pydantic-settings": ("pydantic_settings", "BaseSettings"),
    "python-dotenv": ("dotenv", "load_dotenv"),
    "ollama": ("ollama", "Client"),
    "huggingface-hub": ("huggingface_hub", "HfApi"),
    "httpx": ("httpx", "Client"),
}


def check_dependencies() -> bool:
    print("Dependencies")
    ok = True
    for dist, (module, attr) in DEPENDENCIES.items():
        try:
            getattr(import_module(module), attr)
            print(f"  OK    {dist:<20} {version(dist)}")
        except (ImportError, AttributeError, PackageNotFoundError) as error:
            ok = False
            print(f"  FAIL  {dist:<20} {type(error).__name__}: {error}")
    return ok


def check_ollama() -> None:
    print("Ollama")
    status = ollama_status()
    if not status["reachable"]:
        print(f"  WARN  not reachable at {status['base_url']} ({status['error']}). Start Ollama first.")
        return
    print(f"  OK    reachable at {status['base_url']} ({len(status['installed_models'])} model(s) installed)")
    if status["model_installed"]:
        print(f"  OK    model '{status['model']}' is installed")
    else:
        print(f"  WARN  model '{status['model']}' is not installed yet (ollama pull {status['model']})")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the Windows console is cp1252
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Python:       {sys.version.split()[0]}\n")

    deps_ok = check_dependencies()

    print("\nConfiguration")
    settings = get_settings()
    print(f"  model={settings.ollama_model}  num_ctx={settings.ollama_num_ctx}  "
          f"num_gpu={settings.ollama_num_gpu}  reasoning={settings.ollama_reasoning}")
    print(f"  limits: iterations={settings.max_iterations}  tool_calls={settings.max_tool_calls}  "
          f"per_round={settings.max_calls_per_round}  run_timeout={settings.run_timeout_seconds}s")
    for name, present in settings.configured_keys().items():
        print(f"  {'OK  ' if present else 'WARN'}  {name} key {'set' if present else 'not set'}")

    print()
    check_ollama()

    print("\nResult:", "ready" if deps_ok else "dependency problems found")
    return 0 if deps_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
