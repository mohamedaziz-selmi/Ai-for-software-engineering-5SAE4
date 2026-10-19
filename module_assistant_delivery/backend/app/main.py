"""AI Assistant & Delivery Review service: API under /api/ai, UI and assets under /assistant/."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.review_routes import router as review_router
from .api.routes import router
from .api.support_routes import router as support_router
from .config import Settings, load_settings
from .db import connect, init_db, log_llm_call
from .integrations.demo import DemoDirectory
from .llm.clients import ChatClient
from .llm.service import LlmService
from .rag.embeddings import Embedder, LlamaIndexEmbedder
from .rag.vector_store import ChromaChunkStore


def build_llm(settings: Settings) -> LlmService:
    local = ChatClient(name="local", base_url=settings.assistant_base_url, model=settings.assistant_model,
                       timeout_s=settings.assistant_timeout_s, max_attempts=1)
    # The RAFT model lives in the same private Ollama, which keeps only one model in memory (OLLAMA_MAX_LOADED_MODELS=1):
    # choosing it, or falling back to it, unloads the other one, so both never run at the same time.
    local_models = {"base": local}
    if settings.assistant_raft_model:
        local_models["raft"] = ChatClient(name="local-raft", base_url=settings.assistant_base_url, model=settings.assistant_raft_model,
                                          timeout_s=settings.assistant_timeout_s, max_attempts=1)
    extra = {"reasoning_effort": settings.hosted_reasoning_effort} if settings.hosted_reasoning_effort else {}

    def hosted(name: str, model: str, timeout_s: float, attempts: int, seed: int | None = None, max_wait_s: float = 60.0) -> ChatClient:
        body = {**extra, "seed": seed} if seed is not None else extra
        return ChatClient(name=name, base_url=settings.hosted_base_url, model=model, api_key=settings.hosted_api_key,
                          timeout_s=timeout_s, max_attempts=attempts, max_wait_s=max_wait_s, extra_body=body)

    # Assistant backup (only on local failure) and review both use the hosted API when its key is set.
    backup = hosted("backup", settings.backup_model, settings.hosted_timeout_s, 3) if settings.hosted_key_present else None
    if settings.review_provider == "local":
        review, review_by = ChatClient(name="review", base_url=settings.assistant_base_url, model=settings.assistant_model,
                                       timeout_s=settings.review_timeout_s, max_attempts=1), "local"
    else:  # hosted (owner decision); None without a key -> review_failed, never a silent local fallback
        # temperature 0 + a fixed seed: the provider samples as repeatably as it can, so borderline verdicts stay put
        # A review runs in the background, so it may wait out the free tier's per-minute token limit (up to 2 min)
        review = hosted("review", settings.review_model, settings.review_timeout_s, 6, settings.review_seed, 120.0) if settings.hosted_key_present else None
        review_by = "hosted"

    def log_call(**fields) -> None:
        with connect(settings.database_path) as conn:
            log_llm_call(conn, **fields)

    return LlmService(local=local, backup=backup, backup_enabled=settings.backup_enabled, log_call=log_call,
                      review=review, review_served_by=review_by, local_models=local_models)


def create_app(
    settings: Settings | None = None,
    *,
    embedder: Embedder | None = None,
    store: ChromaChunkStore | None = None,
    llm: LlmService | None = None,
    warm_embedder: bool = True,
) -> FastAPI:
    settings = settings or load_settings()
    embedder = embedder or LlamaIndexEmbedder(settings.embedding_model, settings.embedding_device, settings.hf_home)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        def warm() -> None:
            # In the background so /health answers immediately ("loading"). The embedding model first, then one
            # one-token request so Ollama loads the chat model into memory: the first real question is then fast.
            if warm_embedder and hasattr(embedder, "load"):
                _safe(embedder.load)
            if warm_embedder and settings.warm_up:
                _safe(app.state.llm.local.warm_up)
        threading.Thread(target=warm, daemon=True).start()
        yield

    app = FastAPI(title="AI Assistant & Delivery Review", version="0.1.0", lifespan=lifespan,
                  docs_url="/api/ai/docs", openapi_url="/api/ai/openapi.json", redoc_url=None)
    init_db(settings.database_path)
    app.state.settings = settings
    app.state.embedder = embedder
    app.state.store = store or ChromaChunkStore(settings.chroma_path)
    app.state.llm = llm or build_llm(settings)
    app.state.directory = DemoDirectory(settings.seed_dir / "projects.json")

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": "internal_error", "message": "Something went wrong. Please try again."})

    app.include_router(router)
    app.include_router(review_router)
    app.include_router(support_router)

    @app.get("/assistant", include_in_schema=False)
    def assistant_slash() -> RedirectResponse:
        return RedirectResponse("/assistant/", status_code=307)

    if settings.frontend_dir.is_dir():
        app.mount("/assistant/", StaticFiles(directory=settings.frontend_dir, html=True), name="assistant-ui")
    else:
        @app.get("/assistant/{path:path}", include_in_schema=False)
        def ui_not_built(path: str) -> JSONResponse:
            return JSONResponse(status_code=503, content={"error": "ui_not_built", "message": "Run `npm run build` in module_assistant_delivery/frontend."})

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/assistant/", status_code=307)

    return app


def _safe(fn) -> None:
    try:
        fn()
    except Exception:
        pass  # the error is kept on the embedder and reported by /api/ai/health
# Run with: uvicorn --factory app.main:create_app --host 127.0.0.1 --port 8003  (scripts/run_backend.ps1)
