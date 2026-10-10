from __future__ import annotations

import logging

import httpx

from .base import ANSWER_SCHEMA, JSON_INSTRUCTION, LLMError, Usage, parse_answer_json

log = logging.getLogger(__name__)


class OllamaAnswerLLM:
    """Local model through an Ollama server (default http://localhost:11434). No key, no cost.

    Uses Ollama's structured outputs (`format` = JSON schema) so even small models return parseable JSON.
    """

    provider = "ollama"

    def __init__(self, model: str, base_url: str = "http://localhost:11434", timeout: float = 180.0,
                 num_ctx: int = 8192, http: httpx.Client | None = None):
        self.model, self.base_url, self.num_ctx = model, base_url.rstrip("/"), num_ctx
        self._http = http or httpx.Client(timeout=timeout)
        self.last_usage = Usage()

    def answer(self, system: str, user: str) -> dict:
        body = {
            "model": self.model,
            "stream": False,
            "format": ANSWER_SCHEMA,
            "options": {"temperature": 0, "num_ctx": self.num_ctx},
            "messages": [
                {"role": "system", "content": system + JSON_INSTRUCTION},
                {"role": "user", "content": user},
            ],
        }
        try:
            r = self._http.post(f"{self.base_url}/api/chat", json=body)
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama is not reachable at {self.base_url} ({exc.__class__.__name__}). Is it running?") from exc
        if r.status_code == 404:
            raise LLMError(f"Ollama does not have the model {self.model!r}. Run: ollama pull {self.model}")
        if r.status_code >= 400:
            raise LLMError(f"Ollama error {r.status_code}")
        data = r.json()
        self.last_usage = Usage(data.get("prompt_eval_count", 0) or 0, data.get("eval_count", 0) or 0)
        return parse_answer_json((data.get("message") or {}).get("content", ""))
