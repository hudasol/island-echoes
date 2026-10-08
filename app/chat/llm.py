from __future__ import annotations

from typing import Protocol

ANSWER_TOOL = {
    "name": "answer",
    "description": "Return the in-character reply as cited sentences.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answered": {
                "type": "boolean",
                "description": "True only if the evidence directly answers the question.",
            },
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "kind": {"type": "string", "enum": ["fact", "voice"]},
                        "cites": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["text", "kind", "cites"],
                },
            },
            "missing": {
                "type": "string",
                "description": "What the sources do not contain, or an empty string.",
            },
        },
        "required": ["answered", "sentences", "missing"],
    },
}


class LLMError(RuntimeError):
    pass


class AnswerLLM(Protocol):
    def answer(self, system: str, user: str) -> dict: ...


class AnthropicAnswerLLM:
    """Calls the Anthropic Messages API with a forced `answer` tool for structured output."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 1200):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, timeout=45.0, max_retries=2)
        self.model = model
        self.max_tokens = max_tokens

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
            try:
                resp = self.client.messages.create(temperature=0, **kwargs)
            except self._anthropic.BadRequestError as exc:  # some models reject sampling params
                if "temperature" not in str(exc).lower():
                    raise
                resp = self.client.messages.create(**kwargs)
        except self._anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc.__class__.__name__}") from exc
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "answer":
                return dict(block.input)
        raise LLMError("model did not return an answer")
