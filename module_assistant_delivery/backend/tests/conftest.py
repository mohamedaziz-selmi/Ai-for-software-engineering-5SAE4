"""Test fixtures: a deterministic fake embedder, a scripted OpenAI-compatible model server (httpx
MockTransport, so the real client code runs), and a real Chroma store + SQLite in a temp folder.
No network, no GPU, no shared resources."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.db import connect, log_llm_call
from app.llm.clients import ChatClient
from app.llm.service import LlmService
from app.main import create_app
from app.rag.chunking import approx_tokens
from app.rag.vector_store import ChromaChunkStore

MODULE_ROOT = Path(__file__).resolve().parents[2]
FREELANCER, CLIENT, OTHER = "demo-freelancer-a", "demo-client-b", "demo-freelancer-c"


class FakeEmbedder:
    """Hashed bag-of-words vectors: similar wording -> similar vectors. Deterministic and offline."""

    model_name = "fake-hash-embedder"

    def status(self) -> str:
        return "loaded"

    def count_tokens(self, text: str) -> int:
        return approx_tokens(text)

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(256, dtype=np.float32)
        for word in re.findall(r"[a-zà-ÿ0-9]+", text.lower()):
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % 256] += 1.0
        n = np.linalg.norm(v)
        return v / n if n else v

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return np.stack([self._vec(t) for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._vec(text)


Responder = Callable[[list[dict]], str]


class FakeModelServer:
    """Scripted /v1 server. `responses` is consumed in order; each item is a str or a callable(messages)."""

    def __init__(self, model: str, *, up: bool = True) -> None:
        self.model = model
        self.up = up
        self.responses: list[str | Responder] = []
        self.requests: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if not self.up:
            raise httpx.ConnectError("connection refused", request=request)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": self.model}]})
        body = json.loads(request.content)
        self.requests.append(body)
        item = self.responses.pop(0) if self.responses else '{"answer": "x", "citations": [], "grounded": false, "scope_verdict": null}'
        if isinstance(item, httpx.Response):  # scripted HTTP error (429, 400, ...)
            return item
        content = item(body["messages"]) if callable(item) else item
        return httpx.Response(200, json={"model": self.model, "choices": [{"message": {"content": content}}],
                                         "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

    def client(self, name: str) -> ChatClient:
        return ChatClient(name=name, base_url="http://fake/v1", model=self.model, transport=httpx.MockTransport(self.handler))


def chunks_in_prompt(messages: list[dict]) -> dict[str, str]:
    user = next(m["content"] for m in messages if m["role"] == "user" and "<chunk" in m["content"])
    return {m.group(1): m.group(2) for m in re.finditer(r'<chunk id="(C\d+)"[^>]*>\n(.*?)\n</chunk>', user, re.S)}


def cite(phrase: str, *, grounded: bool = True) -> Responder:
    """A well-behaved fake model: cites the provided chunk that contains `phrase`."""

    def respond(messages: list[dict]) -> str:
        for label, text in chunks_in_prompt(messages).items():
            if phrase in text:
                return json.dumps({"answer": f"The documents say: {phrase}.", "grounded": grounded, "scope_verdict": None,
                                   "citations": [{"chunk_id": label, "quote": phrase}]})
        return json.dumps({"answer": "Not in the documents.", "citations": [], "grounded": False, "scope_verdict": None})

    return respond


@pytest.fixture()
def env(tmp_path):
    settings = replace(
        load_settings(read_dotenv=False),
        database_path=tmp_path / "test.sqlite3",
        chroma_path=tmp_path / "chroma",
        seed_dir=MODULE_ROOT / "data" / "seed",
        frontend_dir=tmp_path / "ui",
        backup_enabled=False,
        hosted_api_key="",
    )
    settings.frontend_dir.mkdir()
    (settings.frontend_dir / "index.html").write_text("<!doctype html><title>Assistant</title>", encoding="utf-8")
    local = FakeModelServer("fake-local")
    raft = FakeModelServer("fake-raft")  # the RAFT model: a selectable choice and the base model's local backup
    backup = FakeModelServer("fake-backup")
    hosted = FakeModelServer("fake-hosted-review")

    def make(*, backup_enabled: bool = False, review: str = "hosted") -> TestClient:
        """review: "hosted" (key set, owner decision), "missing" (no key) or "local" (explicit offline option)."""

        def log_call(**fields):
            with connect(settings.database_path) as conn:
                log_llm_call(conn, **fields)

        review_client = {"hosted": hosted.client("review"), "missing": None, "local": local.client("review")}[review]
        llm = LlmService(local=local.client("local"), backup=backup.client("backup") if backup_enabled else None,
                         backup_enabled=backup_enabled, log_call=log_call, review=review_client,
                         review_served_by="local" if review == "local" else "hosted",
                         local_models={"raft": raft.client("local-raft")})
        app = create_app(replace(settings, backup_enabled=backup_enabled), embedder=FakeEmbedder(),
                         store=ChromaChunkStore(settings.chroma_path), llm=llm, warm_embedder=False)
        return TestClient(app)

    return {"settings": settings, "local": local, "raft": raft, "backup": backup, "hosted": hosted, "make": make}


def upload(client: TestClient, user: str, project_id: str, path: Path, name: str | None = None) -> httpx.Response:
    return client.post("/api/ai/documents", headers={"X-Demo-User": user},
                       data={"project_id": project_id, "doc_type": "cahier_des_charges"},
                       files={"file": (name or path.name, path.read_bytes(), "text/markdown")})


SEED_DOCS = MODULE_ROOT / "data" / "seed" / "documents"
