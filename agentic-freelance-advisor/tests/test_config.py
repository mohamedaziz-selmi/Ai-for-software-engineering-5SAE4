import pytest
from pydantic import ValidationError

from app.config import Settings

def load() -> Settings:
    return Settings(_env_file=None)


def test_defaults():
    settings = load()
    assert settings.ollama_model == "qwen3:4b"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_num_ctx == 4096
    assert settings.ollama_reasoning is True
    assert settings.max_iterations == 6
    assert settings.max_tool_calls == 8
    assert settings.configured_keys() == {"tavily": False, "github": False, "huggingface": False}


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b-instruct")
    monkeypatch.setenv("MAX_ITERATIONS", "3")
    monkeypatch.setenv("OLLAMA_REASONING", "false")
    monkeypatch.setenv("MAX_GAP_NUDGES", "0")
    settings = load()
    assert settings.ollama_model == "qwen3:4b-instruct"
    assert settings.max_iterations == 3
    assert settings.ollama_reasoning is False
    assert settings.max_gap_nudges == 0


def test_empty_value_counts_as_unset(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("OLLAMA_REASONING", "")
    settings = load()
    assert settings.tavily_api_key is None
    assert settings.ollama_reasoning is True  # empty falls back to the default


def test_secrets_are_hidden_but_usable(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-secret-value")
    settings = load()
    assert "tvly-secret-value" not in repr(settings)
    assert settings.tavily_api_key.get_secret_value() == "tvly-secret-value"
    assert settings.configured_keys()["tavily"] is True


@pytest.mark.parametrize(
    ("variable", "value"),
    [("MAX_ITERATIONS", "0"), ("OLLAMA_NUM_CTX", "512"), ("API_PORT", "70000")],
)
def test_invalid_limits_are_rejected(monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)
    with pytest.raises(ValidationError):
        load()
