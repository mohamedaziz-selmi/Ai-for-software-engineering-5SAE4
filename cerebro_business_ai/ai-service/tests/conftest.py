import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

@pytest.fixture(autouse=True)
def isolate_llm_configuration(monkeypatch):
    # Unit/API tests must not inherit a running developer's provider credentials.
    # Real inference is tested separately by verify_business and Playwright.
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
