"""Hosted-API behaviour of the OpenAI-compatible client (Groq free tier: rate limits, JSON modes)."""

import json

import httpx
import pytest

from app.llm.clients import ChatClient, LlmError

OK = {"model": "m", "choices": [{"message": {"content": '{"ok": true}'}}], "usage": {}}
MESSAGES = [{"role": "user", "content": "Reply in JSON."}]


def client(handler, **kw):
    return ChatClient(name="t", base_url="http://fake/v1", model="m", transport=httpx.MockTransport(handler), **kw)


def test_rate_limit_waits_decimal_retry_after_and_records_headers(monkeypatch):
    calls, slept = [], []
    monkeypatch.setattr("app.llm.clients.time.sleep", slept.append)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "2.5", "x-ratelimit-remaining-tokens": "0"})
        return httpx.Response(200, json=OK, headers={"x-ratelimit-remaining-tokens": "7400", "x-ratelimit-limit-tokens": "8000"})

    c = client(handler, max_attempts=3)
    assert c.complete_json(MESSAGES, {}, schema_name="s").content == '{"ok": true}'
    assert slept == [2.5]
    assert c.last_rate_limit["x-ratelimit-remaining-tokens"] == "7400"


def test_quota_wait_longer_than_cap_fails_fast(monkeypatch):
    monkeypatch.setattr("app.llm.clients.time.sleep", lambda s: pytest.fail("must not sleep"))
    c = client(lambda r: httpx.Response(429, headers={"retry-after": "3600"}), max_attempts=6, max_wait_s=60)
    with pytest.raises(LlmError) as error:
        c.complete_json(MESSAGES, {}, schema_name="s")
    assert error.value.kind == "rate_limited" and error.value.retry_after == 3600


def test_strict_schema_rejected_falls_back_to_json_mode_once():
    formats = []

    def handler(request):
        fmt = json.loads(request.content)["response_format"]["type"]
        formats.append(fmt)
        if fmt == "json_schema":
            return httpx.Response(400, json={"error": {"message": "json_schema is not supported for this model"}})
        return httpx.Response(200, json=OK)

    c = client(handler)
    c.complete_json(MESSAGES, {"type": "object"}, schema_name="s")
    c.complete_json(MESSAGES, {"type": "object"}, schema_name="s")
    assert formats == ["json_schema", "json_object", "json_object"]


def test_provider_options_and_key_are_sent_in_the_request():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=OK)

    client(handler, api_key="test-key", extra_body={"reasoning_effort": "low", "seed": 7}).complete_json(MESSAGES, {}, schema_name="s")
    assert seen["body"]["reasoning_effort"] == "low" and seen["auth"] == "Bearer test-key"
    assert seen["body"]["seed"] == 7 and seen["body"]["temperature"] == 0.0  # repeatable review sampling


def test_warm_up_sends_one_token_request_and_never_raises():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK)

    assert client(handler).warm_up() is True
    assert seen["body"]["max_tokens"] == 1 and seen["body"]["model"] == "m"

    def down(request):
        raise httpx.ConnectError("refused")

    assert client(down).warm_up() is False
