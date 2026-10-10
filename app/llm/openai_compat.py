from __future__ import annotations

import logging

import httpx

from .base import ANSWER_SCHEMA, JSON_INSTRUCTION, LLMError, Usage, parse_answer_json

log = logging.getLogger(__name__)


class OpenAICompatAnswerLLM:
    """Any OpenAI-compatible chat endpoint: Hugging Face Inference Providers (free tier with a free HF token),
    a llama.cpp or vLLM server, LM Studio. Asks for a JSON-schema response and falls back to JSON mode."""

    def __init__(self, base_url: str, model: str, api_key: str | None = None, provider: str = "openai-compat",
                 timeout: float = 90.0, http: httpx.Client | None = None):
        self.provider, self.model, self.base_url = provider, model, base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = http or httpx.Client(timeout=timeout)
        self.last_usage = Usage()

    def _post(self, response_format: dict, system: str, user: str) -> httpx.Response:
        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 900,
            "response_format": response_format,
            "messages": [
                {"role": "system", "content": system + JSON_INSTRUCTION},
                {"role": "user", "content": user},
            ],
        }
        try:
            return self._http.post(f"{self.base_url}/chat/completions", json=body, headers=self._headers)
        except httpx.HTTPError as exc:
            raise LLMError(f"{self.provider} is not reachable ({exc.__class__.__name__})") from exc

    def answer(self, system: str, user: str) -> dict:
        schema_format = {"type": "json_schema", "json_schema": {"name": "answer", "schema": ANSWER_SCHEMA, "strict": False}}
        r = self._post(schema_format, system, user)
        if r.status_code in (400, 422):  # endpoint does not support json_schema: retry in plain JSON mode
            r = self._post({"type": "json_object"}, system, user)
        if r.status_code == 401:
            raise LLMError(f"{self.provider} rejected the token (401). Check the key in .env.")
        if r.status_code == 429:
            raise LLMError(f"{self.provider} rate limit reached. Wait a minute and try again.")
        if r.status_code >= 400:
            raise LLMError(f"{self.provider} error {r.status_code}")
        data = r.json()
        u = data.get("usage") or {}
        self.last_usage = Usage(u.get("prompt_tokens", 0) or 0, u.get("completion_tokens", 0) or 0)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError(f"{self.provider} returned no message") from None
        return parse_answer_json(content)
