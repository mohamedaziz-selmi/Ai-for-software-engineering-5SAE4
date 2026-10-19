"""OpenAI-compatible chat clients: the private Ollama (assistant) and the hosted API (backup, review).

Errors are mapped to a small set of kinds so callers can give friendly messages and decide whether
to fall back. API keys are sent only in the Authorization header and never logged.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

import httpx

ERROR_KINDS = ("not_configured", "timeout", "unavailable", "rate_limited", "auth", "model_missing", "bad_response")


class LlmError(Exception):
    def __init__(self, kind: str, detail: str = "", retry_after: float | None = None) -> None:
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind
        self.detail = detail
        self.retry_after = retry_after


@dataclass(frozen=True)
class Completion:
    content: str
    model: str
    tokens_in: int | None
    tokens_out: int | None


def _seconds(value: str | None) -> float | None:
    """Retry-After in seconds (Groq may send decimals such as "2.5")."""
    try:
        return max(0.0, float(value)) if value is not None else None
    except ValueError:
        return None


class ChatClient:
    """Minimal /chat/completions client with JSON-schema constrained output."""

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_s: float = 60,
        max_attempts: int = 1,
        max_wait_s: float = 60.0,
        extra_body: dict | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
        self._timeout = timeout_s
        self._max_attempts = max_attempts
        self._max_wait = max_wait_s
        self._extra = dict(extra_body or {})  # provider options, e.g. {"reasoning_effort": "low"} for gpt-oss on Groq
        self._transport = transport
        self._schema_mode = True  # switched off once if the provider rejects strict json_schema
        self.last_rate_limit: dict[str, str] = {}  # x-ratelimit-* headers of the last response (quota visibility)

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

    def _client(self, timeout: float) -> httpx.Client:
        return httpx.Client(timeout=timeout, headers=self._headers(), transport=self._transport)

    def complete_json(self, messages: list[dict], schema: dict, *, schema_name: str, temperature: float = 0.0) -> Completion:
        def payload() -> dict:
            response_format = ({"type": "json_schema", "json_schema": {"name": schema_name, "schema": schema, "strict": True}}
                               if self._schema_mode else {"type": "json_object"})
            return {"model": self.model, "messages": messages, "temperature": temperature,
                    "response_format": response_format, **self._extra}

        last: LlmError | None = None
        for attempt in range(self._max_attempts):
            try:
                return self._post(payload())
            except LlmError as error:
                last = error
                if error.kind == "bad_response" and self._schema_mode and "HTTP 400" in error.detail:
                    # Provider does not accept this strict schema: fall back to JSON mode once. Output is still
                    # validated with Pydantic, so nothing unvalidated reaches the user.
                    self._schema_mode = False
                    try:
                        return self._post(payload())
                    except LlmError as retry_error:
                        last = error = retry_error
                if error.kind not in {"timeout", "rate_limited", "unavailable"} or attempt + 1 == self._max_attempts:
                    raise
                wait = error.retry_after if error.retry_after is not None else min(8.0, 2**attempt) + random.uniform(0, 0.5)
                if wait > self._max_wait:
                    raise  # e.g. daily quota exhausted: fail now with a clear rate_limited error instead of hanging
                time.sleep(wait)
        raise last or LlmError("unavailable")

    def _post(self, payload: dict) -> Completion:
        try:
            with self._client(self._timeout) as client:
                response = client.post(f"{self.base_url}/chat/completions", json=payload)
        except httpx.TimeoutException as exc:
            raise LlmError("timeout", type(exc).__name__) from exc
        except httpx.HTTPError as exc:
            raise LlmError("unavailable", type(exc).__name__) from exc

        self.last_rate_limit = {k: v for k, v in response.headers.items() if k.lower().startswith("x-ratelimit-")}
        if response.status_code == 429:
            raise LlmError("rate_limited", "HTTP 429", _seconds(response.headers.get("retry-after")))
        if response.status_code in (401, 403):
            raise LlmError("auth", f"HTTP {response.status_code}")
        if response.status_code == 404:
            raise LlmError("model_missing", "HTTP 404")
        if response.status_code >= 500:
            raise LlmError("unavailable", f"HTTP {response.status_code}")
        if response.status_code >= 400:
            raise LlmError("bad_response", f"HTTP {response.status_code}: {response.text[:200]}")
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LlmError("bad_response", "unexpected response shape") from exc
        if not isinstance(content, str) or not content.strip():
            raise LlmError("bad_response", "empty content")
        usage = data.get("usage") or {}
        return Completion(content, data.get("model", self.model), usage.get("prompt_tokens"), usage.get("completion_tokens"))

    def warm_up(self, timeout_s: float = 180.0) -> bool:
        """Load the model into memory with a one-token request (Ollama loads a model on first use). True if it answered."""
        try:
            with self._client(timeout_s) as client:
                response = client.post(f"{self.base_url}/chat/completions",
                                       json={"model": self.model, "messages": [{"role": "user", "content": "ok"}], "max_tokens": 1})
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def probe(self, timeout_s: float = 3.0) -> str:
        """Cheap readiness check: 'up', 'model_missing' or 'down'. Lists models; generates nothing."""
        try:
            with self._client(timeout_s) as client:
                response = client.get(f"{self.base_url}/models")
            if response.status_code != 200:
                return "down"
            ids = {m.get("id") for m in response.json().get("data", [])}
            return "up" if self.model in ids else "model_missing"
        except (httpx.HTTPError, ValueError):
            return "down"
