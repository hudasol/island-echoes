from __future__ import annotations

import logging

from .base import ANSWER_TOOL, LLMError, Usage

log = logging.getLogger(__name__)


class AnthropicAnswerLLM:
    """Calls the Anthropic Messages API with a forced `answer` tool for structured output."""

    provider = "anthropic"

    def __init__(self, api_key: str, model: str, max_tokens: int = 1200):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, timeout=45.0, max_retries=2)
        self.model = model
        self.max_tokens = max_tokens
        self.last_usage = Usage()

    def answer(self, system: str, user: str) -> dict:
        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[ANSWER_TOOL],
            tool_choice={"type": "tool", "name": "answer"},
        )
        try:
            resp = self.client.messages.create(**kwargs)
        except self._anthropic.APIError as exc:
            log.warning("Anthropic API error: %s", exc)
            if "credit balance" in str(exc).lower():
                raise LLMError("The Anthropic account has no credit left. Add credit under Plans & Billing.") from exc
            raise LLMError(f"Anthropic API error: {exc.__class__.__name__}") from exc
        u = getattr(resp, "usage", None)
        self.last_usage = Usage(getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0)
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "answer":
                return dict(block.input)
        raise LLMError("model did not return an answer")
