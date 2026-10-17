"""Shared contract for every answer model: same inputs, same structured output, same errors."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

ANSWER_SCHEMA = {
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
}

ANSWER_TOOL = {
    "name": "answer",
    "description": "Return the in-character reply as cited sentences.",
    "input_schema": ANSWER_SCHEMA,
}

JSON_INSTRUCTION = (
    "\n\nReply with a single JSON object and nothing else, matching this schema:\n"
    '{"answered": bool, "sentences": [{"text": str, "kind": "fact" | "voice", "cites": [evidence ids]}], '
    '"missing": str}'
)


class LLMError(RuntimeError):
    pass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


class AnswerLLM(Protocol):
    provider: str
    model: str
    last_usage: Usage

    def answer(self, system: str, user: str) -> dict: ...


def clean_cite(c: str) -> str:
    """Strip formatting noise small models add around an evidence id ("[SOC-011]", ".SOC-011", " SOC-011 ").

    Only the wrapper is cleaned; the id itself is still checked against the retrieved evidence downstream.
    """
    return c.strip().strip("[](){}<>.,;:'\"`").strip()


def parse_answer_json(text: str) -> dict:
    """Pull the answer object out of a model reply, tolerating code fences and surrounding prose."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise LLMError("model did not return JSON") from None
        try:
            obj = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            raise LLMError("model returned malformed JSON") from None
    if not isinstance(obj, dict):
        raise LLMError("model JSON was not an object")
    sents = obj.get("sentences", [])
    if not isinstance(sents, list):
        raise LLMError("model JSON had no sentence list")
    clean = []
    for s in sents:
        if not isinstance(s, dict) or not isinstance(s.get("text"), str):
            continue
        cites = s.get("cites", [])
        clean.append(
            {
                "text": s["text"],
                "kind": s.get("kind") if s.get("kind") in ("fact", "voice") else "fact",
                "cites": [clean_cite(c) for c in (cites if isinstance(cites, list) else [cites]) if isinstance(c, str) and clean_cite(c)],
            }
        )
    return {"answered": bool(obj.get("answered")), "sentences": clean, "missing": str(obj.get("missing") or "")}
