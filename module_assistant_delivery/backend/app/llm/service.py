"""LLM layer used by every runtime AI call (spec 8.4). Not the API gateway.

Assistant calls: mask PII -> the chosen local model (base or RAFT) -> validate JSON (one repair retry) -> on
failure, the other local model, then the hosted backup (both only if backups are enabled) -> unmask for display.
Every attempt is logged without content.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from .clients import ChatClient, Completion, LlmError
from .masking import Masker

CallLogger = Callable[..., None]


class AssistantUnavailable(Exception):
    def __init__(self, attempts: list[dict]) -> None:
        super().__init__("assistant unavailable")
        self.attempts = attempts


class ReviewNotConfigured(Exception):
    """The hosted review model has no API key. The review never falls back to the local model (spec 8.4)."""


@dataclass
class LlmResult:
    parsed: BaseModel
    served_by: str  # "local" (the chosen model) | "local_backup" (the other local model) | "backup" (hosted)
    model: str
    latency_ms: int
    masker: Masker
    attempts: list[dict] = field(default_factory=list)


def _parse(content: str, model_type: type[BaseModel]) -> BaseModel:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :]
    return model_type.model_validate(json.loads(text))


class LlmService:
    def __init__(
        self, *, local: ChatClient, backup: ChatClient | None, backup_enabled: bool, log_call: CallLogger,
        review: ChatClient | None = None, review_served_by: str = "hosted", local_models: dict[str, ChatClient] | None = None,
    ) -> None:
        self.local = local
        # Selectable local models: "base" (default) and, when configured, "raft". Each is the other's backup.
        self.local_models: dict[str, ChatClient] = {"base": local, **{k: v for k, v in (local_models or {}).items() if k != "base"}}
        self.backup = backup
        self.backup_enabled = backup_enabled
        # Review client: the hosted model (owner decision), or None when its key is missing. The local model is
        # used for review only if REVIEW_PROVIDER=local is configured explicitly (offline demos and tests).
        self.review = review
        self.review_served_by = review_served_by
        self._log = log_call

    @property
    def backup_status(self) -> str:
        if not self.backup_enabled:
            return "disabled"
        if self.backup is None:
            return "not_configured"
        return "configured"

    def _call_validated(
        self, client: ChatClient, messages: list[dict], schema: dict, schema_name: str, model_type: type[BaseModel],
        *, feature: str, served_by: str, prompt_version: str,
    ) -> tuple[BaseModel, Completion]:
        conversation = list(messages)
        for attempt in (1, 2):
            started = time.perf_counter()
            try:
                completion = client.complete_json(conversation, schema, schema_name=schema_name)
            except LlmError as error:
                self._log(feature=feature, served_by=served_by, model=client.model, prompt_version=prompt_version,
                          latency_ms=int((time.perf_counter() - started) * 1000), status="error", error_type=error.kind)
                raise
            latency = int((time.perf_counter() - started) * 1000)
            try:
                parsed = _parse(completion.content, model_type)
            except (ValueError, ValidationError) as error:
                self._log(feature=feature, served_by=served_by, model=client.model, prompt_version=prompt_version,
                          latency_ms=latency, status="invalid_output", error_type="invalid_json",
                          tokens_in=completion.tokens_in, tokens_out=completion.tokens_out)
                if attempt == 2:
                    raise LlmError("bad_response", "invalid JSON after one repair retry") from error
                # One repair retry with the validation error fed back (spec 8.2).
                conversation = conversation + [
                    {"role": "assistant", "content": completion.content[:4000]},
                    {"role": "user", "content": f"Your reply was not valid for the required JSON schema ({str(error)[:300]}). Reply again with only the corrected JSON object."},
                ]
                continue
            self._log(feature=feature, served_by=served_by, model=completion.model, prompt_version=prompt_version,
                      latency_ms=latency, status="ok", tokens_in=completion.tokens_in, tokens_out=completion.tokens_out)
            return parsed, completion
        raise LlmError("bad_response")

    def _structured(
        self, routes: list[tuple[str, ChatClient]], messages: list[dict], schema: dict, model_type: type[BaseModel],
        *, schema_name: str, prompt_version: str, feature: str, fail_first: bool = False,
    ) -> LlmResult:
        masker = Masker()
        masked = [{"role": m["role"], "content": masker.mask(m["content"])} for m in messages]
        started = time.perf_counter()
        attempts: list[dict] = []
        for index, (served_by, client) in enumerate(routes):
            if fail_first and index == 0:  # failure drill: the chosen model is skipped as if it had failed
                attempts.append({"served_by": served_by, "model": client.model, "error": "simulated_failure"})
                continue
            try:
                parsed, completion = self._call_validated(
                    client, masked, schema, schema_name, model_type,
                    feature=feature, served_by=served_by, prompt_version=prompt_version,
                )
            except LlmError as error:
                attempts.append({"served_by": served_by, "model": client.model, "error": error.kind})
                continue
            return LlmResult(parsed, served_by, completion.model, int((time.perf_counter() - started) * 1000), masker, attempts)
        raise AssistantUnavailable(attempts)

    def assistant_json(
        self, messages: list[dict], schema: dict, model_type: type[BaseModel], *, schema_name: str, prompt_version: str,
        feature: str = "assistant", model: str = "base", simulate_failure: bool = False,
    ) -> LlmResult:
        """The chosen local model ("base" or "raft") first. If it fails: the other local model, then the hosted
        backup; both only when backups are enabled (never during evals). `simulate_failure` is the demo's failure
        drill: the chosen model is skipped so the backup chain can be shown without stopping anything."""
        chosen = self.local_models.get(model, self.local)
        routes: list[tuple[str, ChatClient]] = [("local", chosen)]
        if self.backup_enabled:
            routes += [("local_backup", client) for client in self.local_models.values() if client is not chosen]
            if self.backup is not None:
                routes.append(("backup", self.backup))
        return self._structured(routes, messages, schema, model_type, schema_name=schema_name,
                                prompt_version=prompt_version, feature=feature, fail_first=simulate_failure)

    def review_json(
        self, messages: list[dict], schema: dict, model_type: type[BaseModel], *, schema_name: str, prompt_version: str,
    ) -> LlmResult:
        """The review never falls back to another model (spec 8.4)."""
        if self.review is None:
            raise ReviewNotConfigured()
        return self._structured([(self.review_served_by, self.review)], messages, schema, model_type,
                                schema_name=schema_name, prompt_version=prompt_version, feature="review")
