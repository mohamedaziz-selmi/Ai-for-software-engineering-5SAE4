import pytest

from app.config import Settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Tests must not depend on the developer's shell or .env."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def make_settings():
    """Build Settings that ignore .env, e.g. make_settings(tavily_api_key='tvly-test')."""

    def factory(**overrides) -> Settings:
        return Settings(_env_file=None, **overrides)

    return factory
