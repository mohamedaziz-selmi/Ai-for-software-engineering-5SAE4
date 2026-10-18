"""Local embeddings through LlamaIndex's HuggingFaceEmbedding (sentence-transformers underneath), CPU by default.

Each supported model declares its query/passage instructions; e5 requires "query: " / "passage: ".
The tokenizer of the same model counts tokens for chunking, so chunks fit its input limit.
The model cache lives in the module's storage/hf, not a shared cache.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Protocol

import numpy as np

# model -> (query instruction, passage instruction, max input tokens)
MODEL_PROFILES: dict[str, tuple[str, str, int]] = {
    "intfloat/multilingual-e5-base": ("query: ", "passage: ", 512),
    "intfloat/multilingual-e5-large": ("query: ", "passage: ", 512),
    "BAAI/bge-m3": ("", "", 8192),
    "Qwen/Qwen3-Embedding-0.6B": (
        "Instruct: Given a question about a freelance project's documents, retrieve the passages that answer it\nQuery: ", "", 8192),
}


class Embedder(Protocol):
    model_name: str

    def status(self) -> str: ...

    def count_tokens(self, text: str) -> int: ...

    def embed_passages(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


class LlamaIndexEmbedder:
    def __init__(self, model_name: str, device: str, cache_dir: Path) -> None:
        if model_name not in MODEL_PROFILES:
            raise ValueError(f"No embedding profile for {model_name}; add one to MODEL_PROFILES.")
        self.model_name = model_name
        self.query_instruction, self.passage_instruction, self.max_tokens = MODEL_PROFILES[model_name]
        self._device = device
        self._cache_dir = cache_dir
        self._model = None
        self._tokenizer = None
        self._error: str | None = None
        self._lock = threading.Lock()

    def status(self) -> str:
        if self._model is not None:
            return "loaded"
        if self._error:
            return "error"
        return "loading" if self._lock.locked() else "not_loaded"

    @property
    def error(self) -> str | None:
        return self._error

    def load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
                os.environ.setdefault("HF_HOME", str(self._cache_dir))
                from llama_index.embeddings.huggingface import HuggingFaceEmbedding

                self._model = HuggingFaceEmbedding(
                    model_name=self.model_name,
                    device=self._device,
                    cache_folder=str(self._cache_dir / "sentence-transformers"),
                    query_instruction=self.query_instruction,
                    text_instruction=self.passage_instruction,
                    normalize=True,
                    max_length=min(self.max_tokens, 512),
                    embed_batch_size=16,
                )
                self._tokenizer = self._model._model.tokenizer
                self._error = None
            except Exception as exc:  # reported by /health; never raised to end users
                self._error = f"{type(exc).__name__}: {exc}"[:300]
                raise

    def count_tokens(self, text: str) -> int:
        self.load()
        return len(self._tokenizer.encode(f"{self.passage_instruction}{text}", add_special_tokens=True))

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        self.load()
        return np.asarray(self._model.get_text_embedding_batch(texts), dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        self.load()
        return np.asarray(self._model.get_query_embedding(text), dtype=np.float32)
