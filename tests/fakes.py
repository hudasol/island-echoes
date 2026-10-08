"""Test doubles. Used only by unit tests; real answers always come from the Anthropic API."""

from __future__ import annotations


class ScriptedLLM:
    """Returns pre-written tool outputs in order and records every prompt it was given."""

    def __init__(self, *outputs: dict):
        self.outputs = list(outputs)
        self.calls: list[tuple[str, str]] = []

    def answer(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        if not self.outputs:
            raise AssertionError("ScriptedLLM ran out of scripted outputs")
        return self.outputs.pop(0)


def fact(text: str, *cites: str) -> dict:
    return {"text": text, "kind": "fact", "cites": list(cites)}


def voice(text: str) -> dict:
    return {"text": text, "kind": "voice", "cites": []}


def reply(*sentences: dict, answered: bool = True, missing: str = "") -> dict:
    return {"answered": answered, "sentences": list(sentences), "missing": missing}
