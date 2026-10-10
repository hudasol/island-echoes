from __future__ import annotations

import logging
from pathlib import Path

from .base import ANSWER_SCHEMA, JSON_INSTRUCTION, LLMError, Usage, parse_answer_json

log = logging.getLogger(__name__)


class LlamaCppAnswerLLM:
    """In-process GGUF model through llama-cpp-python (optional dependency). Grammar-constrained JSON output,
    so the reply always parses. Used for reproducible offline evals and for running without any server."""

    provider = "llamacpp"

    def __init__(self, model_path: str, n_ctx: int = 6144, n_threads: int | None = None):
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise LLMError("llama-cpp-python is not installed (pip install -r requirements-ml.txt)") from exc
        if not Path(model_path).exists():
            raise LLMError(f"GGUF model not found at {model_path}")
        self.model = Path(model_path).stem
        self._llm = Llama(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads, verbose=False)
        self.last_usage = Usage()

    def answer(self, system: str, user: str) -> dict:
        try:
            r = self._llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system + JSON_INSTRUCTION},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object", "schema": ANSWER_SCHEMA},
                temperature=0,
                max_tokens=700,
            )
        except Exception as exc:  # noqa: BLE001 - llama.cpp raises plain ValueError/RuntimeError
            raise LLMError(f"llama.cpp failed: {exc.__class__.__name__}") from exc
        u = r.get("usage") or {}
        self.last_usage = Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        return parse_answer_json(r["choices"][0]["message"]["content"])
