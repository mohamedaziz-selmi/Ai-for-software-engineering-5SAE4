"""Application settings, read from environment variables and the project-root .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # `KEY=` in .env means "not set"
        extra="ignore",
    )

    # --- Local LLM (Ollama) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    # Sized for an RTX 2050 (4 GB VRAM): 4096 runs ~67% on GPU, 8192 only ~58% and ~25% slower.
    # Every prompt the agent builds must fit this window together with the model's thinking.
    ollama_num_ctx: int = Field(4096, ge=2048)
    # 0.6 is the model's own default. Thinking models degrade at near-greedy temperatures.
    ollama_temperature: float = Field(0.6, ge=0.0, le=1.0)
    # qwen3:4b is a thinking-only build. reasoning=False does NOT disable thinking (the thinking
    # text leaks into `content`); True keeps `content` clean and puts it in `reasoning_content`.
    ollama_reasoning: bool | None = True
    ollama_request_timeout: float = Field(300.0, gt=0)  # per LLM call, seconds
    # Layers to offload to the GPU. Measured on the RTX 2050 (4 GB): Ollama's own choice put 67% of the
    # model on the GPU (17 tok/s); forcing all layers (99) fits in 3.2 GB and runs at ~32 tok/s.
    # Use -1 to let Ollama decide (e.g. if another program needs the GPU memory).
    ollama_num_gpu: int = Field(99, ge=-1)
    # Cap on generated tokens per agent turn, THINKING INCLUDED. Too low and the model is cut off
    # mid-thought and answers nothing; too high and the prompt no longer fits the context window.
    agent_max_tokens: int = Field(1600, ge=256)
    # Caps include THINKING. Every prompt ends with a request to think briefly (see prompts.BREVITY), but the model
    # still runs away on some calls. Measured: caps 1600/2000/2000 gave a complete 773 s run; lowering them to
    # 1200/1400/1400 made the plan and a report section fail in the next live run (1,185 s), so they stay high.
    plan_max_tokens: int = Field(2000, ge=512)
    report_max_tokens: int = Field(2000, ge=512)

    # --- Research tool credentials ---
    tavily_api_key: SecretStr | None = None
    github_token: SecretStr | None = None
    hf_token: SecretStr | None = None

    # --- Agent limits ---
    max_iterations: int = Field(6, ge=1, le=20)
    max_tool_calls: int = Field(8, ge=1, le=50)
    max_calls_per_round: int = Field(2, ge=1, le=5)
    # How often the evaluator may send the agent back to research after it said DONE with gaps open.
    max_gap_nudges: int = Field(2, ge=0, le=5)
    tool_timeout_seconds: float = Field(20.0, gt=0)  # per HTTP request and per tool call
    max_results_per_tool: int = Field(5, ge=1, le=10)  # keeps observations small for the context window
    # "en": leave out datasets that are tagged for, or named after, another language (unless the query names one).
    # Ranked by downloads alone, 3 of 5 datasets for an English "fake news" project were Filipino or Spanish.
    dataset_language: Literal["en", "any"] = "en"
    # Tavily results scoring below this are dropped (the two best are always kept): a Hugging Face press
    # release and a CNBC video made it into a fake-news report as "sources".
    web_min_relevance: float = Field(0.3, ge=0.0, le=1.0)
    # Whole run. Research stops at 50% of it so the report still has time to be written. A full run needs
    # 10-25 minutes on the throttled RTX 2050 (see README), hence 30 minutes.
    run_timeout_seconds: float = Field(1800.0, gt=0)

    # --- API ---
    api_host: str = "127.0.0.1"
    api_port: int = Field(8000, ge=1, le=65535)
    # Vite dev server of the front end (port 8766), as a fallback to its proxy.
    cors_origins: list[str] = ["http://localhost:8766", "http://127.0.0.1:8766"]

    def configured_keys(self) -> dict[str, bool]:
        """Which credentials are set. Never exposes the values themselves."""
        return {
            "tavily": self.tavily_api_key is not None,
            "github": self.github_token is not None,
            "huggingface": self.hf_token is not None,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
