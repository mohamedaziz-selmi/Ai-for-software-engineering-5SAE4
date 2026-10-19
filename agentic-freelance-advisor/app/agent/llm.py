"""Local LLM access: the ChatOllama factory, Ollama health information and output cleanup."""

import re
import threading
import time
from typing import Any

import httpx
import ollama
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama

from app.config import Settings, get_settings

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


def build_llm(
    settings: Settings | None = None,
    *,
    num_predict: int | None = None,
    temperature: float | None = None,
) -> ChatOllama:
    """Create the only LLM client of the project: a local Ollama model.

    `num_predict` caps generated tokens, thinking included. With a thinking model a cap that
    is too small ends the generation inside the thinking and leaves no answer at all.
    """
    settings = settings or get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        num_ctx=settings.ollama_num_ctx,
        num_gpu=None if settings.ollama_num_gpu < 0 else settings.ollama_num_gpu,
        num_predict=num_predict,
        temperature=settings.ollama_temperature if temperature is None else temperature,
        reasoning=settings.ollama_reasoning,
        client_kwargs={"timeout": settings.ollama_request_timeout},
    )


class LLMError(RuntimeError):
    """The local model could not be reached or failed to answer."""


class LLMTimeout(LLMError):
    """The model did not finish within the wall-clock limit (stalled, or throttled far below normal speed)."""


def _invoke(runnable: Any, messages: Any) -> Any:
    try:
        return runnable.invoke(messages)
    except (httpx.HTTPError, ollama.ResponseError, ConnectionError, OSError) as error:
        raise LLMError(f"Ollama request failed: {type(error).__name__}: {error}") from error


def safe_invoke(runnable: Any, messages: Any, timeout: float | None = None) -> Any:
    """Invoke a chat model, turning transport failures into one clear LLMError.

    `timeout` is a wall-clock limit for the whole call. The httpx timeout cannot provide it: the answer
    streams in token by token, so a read timeout never fires while the model merely trickles along. In a
    live test one call took 852 s instead of about 55 s. The call runs in a worker thread; on timeout the
    run moves on with LLMTimeout (the abandoned request ends on its own, it cannot be cancelled from here).
    """
    if timeout is None:
        return _invoke(runnable, messages)
    outcome: dict[str, Any] = {}

    def work() -> None:
        try:
            outcome["value"] = _invoke(runnable, messages)
        except BaseException as error:  # noqa: BLE001 - re-raised in the caller's thread
            outcome["error"] = error

    worker = threading.Thread(target=work, daemon=True, name="llm-call")
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise LLMTimeout(f"The model did not finish within {timeout:.0f}s.")
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def structured_invoke(
    llm: Any, schema: type, messages: Any, timeout: float | None = None
) -> tuple[Any | None, BaseMessage | None, str | None]:
    """Ask for JSON matching a Pydantic schema, using Ollama's constrained `json_schema` output.

    Returns (parsed object or None, the raw model message, parsing error or None). The default
    `function_calling` method is not used: with this thinking model it ran out of tokens while thinking.
    """
    runnable = llm.with_structured_output(schema, method="json_schema", include_raw=True)
    output = safe_invoke(runnable, messages, timeout)
    error = output.get("parsing_error")
    return output.get("parsed"), output.get("raw"), str(error) if error else None


def message_text(message: BaseMessage) -> str:
    """The visible answer of a model message, without any thinking text."""
    content: Any = message.content
    if isinstance(content, list):
        content = "".join(
            part if isinstance(part, str) else part.get("text", "") for part in content
        )
    text = _THINK_BLOCK.sub("", content or "")
    # Thinking-only builds put `<think>` in the prompt, so only the closing tag is generated.
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text.strip()


def reasoning_text(message: BaseMessage) -> str:
    """The separated thinking text (available when reasoning=True)."""
    return message.additional_kwargs.get("reasoning_content", "") or ""


def generation_stats(message: BaseMessage) -> dict[str, Any]:
    """Token counts and speed from Ollama's response metadata."""
    meta = message.response_metadata or {}
    eval_count = meta.get("eval_count") or 0
    eval_seconds = (meta.get("eval_duration") or 0) / 1e9
    return {
        "output_tokens": eval_count,
        "prompt_tokens": meta.get("prompt_eval_count") or 0,
        "tokens_per_second": round(eval_count / eval_seconds, 1) if eval_seconds else None,
        "load_seconds": round((meta.get("load_duration") or 0) / 1e9, 2),
        "done_reason": meta.get("done_reason"),
    }


def llm_stat(node: str, reply: BaseMessage, started: float, estimated_prompt_tokens: int) -> dict[str, Any]:
    """One row of per-call timing and token statistics, kept in the run state."""
    thinking = reasoning_text(reply)
    return {
        "node": node,
        "seconds": round(time.perf_counter() - started, 1),
        "estimated_prompt_tokens": estimated_prompt_tokens,
        **generation_stats(reply),
        "thinking_chars": len(thinking),
        "thinking_tail": thinking[-400:] if thinking else "",
    }


def ollama_status(settings: Settings | None = None, timeout: float = 3.0) -> dict[str, Any]:
    """Reachability of Ollama and whether the configured model is installed."""
    settings = settings or get_settings()
    status: dict[str, Any] = {
        "base_url": settings.ollama_base_url,
        "model": settings.ollama_model,
        "reachable": False,
        "model_installed": False,
        "installed_models": [],
        "error": None,
    }
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as error:
        status["error"] = f"{type(error).__name__}: {error}"
        return status
    names = [entry.get("name") or entry.get("model") or "" for entry in response.json().get("models", [])]
    status["reachable"] = True
    status["installed_models"] = names
    status["model_installed"] = (
        settings.ollama_model in names or f"{settings.ollama_model}:latest" in names
    )
    return status


def loaded_model_placement(settings: Settings | None = None, timeout: float = 3.0) -> str | None:
    """How the loaded model is split between GPU and CPU, from Ollama's /api/ps."""
    settings = settings or get_settings()
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/ps", timeout=timeout)
        response.raise_for_status()
        for entry in response.json().get("models", []):
            if entry.get("name") == settings.ollama_model or entry.get("model") == settings.ollama_model:
                size, vram = entry.get("size") or 0, entry.get("size_vram") or 0
                if size:
                    return f"{vram / size:.0%} GPU / {1 - vram / size:.0%} CPU ({size / 1e9:.1f} GB loaded)"
    except (httpx.HTTPError, ValueError):
        pass
    return None
