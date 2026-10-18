"""Module settings.

Read from the process environment and the module-local `.env` (module_assistant_delivery/.env),
never from any shared or teammate configuration file. Secrets are held here and never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = MODULE_ROOT / "storage"


def _load_module_dotenv(path: Path) -> None:
    """Minimal KEY=VALUE loader; existing environment variables win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def _flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else MODULE_ROOT / path


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    database_path: Path
    chroma_path: Path
    seed_dir: Path
    frontend_dir: Path
    hf_home: Path
    assistant_base_url: str
    assistant_model: str
    assistant_timeout_s: float
    review_timeout_s: float
    backup_enabled: bool
    hosted_base_url: str
    hosted_api_key: str
    backup_model: str
    review_model: str
    review_provider: str
    hosted_timeout_s: float
    hosted_reasoning_effort: str
    embedding_model: str
    embedding_device: str
    top_k: int

    @property
    def hosted_key_present(self) -> bool:
        return bool(self.hosted_api_key)


def load_settings(*, read_dotenv: bool = True) -> Settings:
    if read_dotenv:
        _load_module_dotenv(MODULE_ROOT / ".env")
    env = os.environ.get
    return Settings(
        host=env("AI_HOST", "127.0.0.1"),
        port=int(env("AI_PORT", "8003")),
        database_path=_path("DATABASE_PATH", STORAGE_DIR / "assistant.sqlite3"),
        chroma_path=_path("CHROMA_PATH", STORAGE_DIR / "chroma"),
        seed_dir=_path("SEED_DIR", MODULE_ROOT / "data" / "seed"),
        frontend_dir=_path("FRONTEND_DIR", MODULE_ROOT / "frontend" / "dist"),
        hf_home=_path("MODULE_HF_HOME", STORAGE_DIR / "hf"),
        assistant_base_url=env("ASSISTANT_BASE_URL", "http://127.0.0.1:11435/v1").rstrip("/"),
        assistant_model=env("ASSISTANT_MODEL", "qwen2.5:7b-instruct"),
        assistant_timeout_s=float(env("ASSISTANT_TIMEOUT_S", "60")),
        review_timeout_s=float(env("REVIEW_TIMEOUT_S", "180")),
        backup_enabled=_flag("ASSISTANT_BACKUP_ENABLED", True),  # owner decision; evals always pass False
        hosted_base_url=env("HOSTED_API_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
        hosted_api_key=env("HOSTED_API_KEY", ""),
        backup_model=env("BACKUP_MODEL", "openai/gpt-oss-120b"),
        review_model=env("REVIEW_MODEL", "openai/gpt-oss-120b"),
        review_provider=env("REVIEW_PROVIDER", "hosted"),  # hosted (owner decision) | local (explicit offline option)
        hosted_timeout_s=float(env("HOSTED_TIMEOUT_S", "60")),
        hosted_reasoning_effort=env("HOSTED_REASONING_EFFORT", "low"),  # gpt-oss on Groq; empty to omit
        embedding_model=env("EMBEDDING_MODEL", "intfloat/multilingual-e5-base"),
        embedding_device=env("EMBEDDING_DEVICE", "cpu"),
        top_k=int(env("RETRIEVAL_TOP_K", "5")),
    )
