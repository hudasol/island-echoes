from __future__ import annotations

import re

from .base import Usage

_ID = re.compile(r"\[([A-Za-z0-9._-]+)\]\s*\(")
_BLOCK = re.compile(r"\[([A-Za-z0-9._-]+)\] \([^\n]*\)\n(.*?)(?=\n\n\[[A-Za-z0-9._-]+\] \(|\n</evidence>|\Z)", re.S)
_EV = re.compile(r"<evidence>\n(.*?)\n</evidence>", re.S)
_Q = re.compile(r"<question>\n(.*?)\n</question>", re.S)


def first_sentence(text: str, limit: int = 320) -> str:
    text = " ".join(text.split())
    m = re.match(r"(.+?[.!?])(?:\s+[A-Z(]|$)", text)
    s = m.group(1) if m else text
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "."


class ExtractiveAnswerLLM:
    """No model. Returns the opening sentence of the top retrieved items, each cited to itself.

    It is the floor for the eval: whatever a language model adds over this baseline is the measured gain,
    and it is a safe fallback because every sentence is copied from a cited source.
    """

    provider = "extractive"
    model = "top-evidence"

    def __init__(self, max_sentences: int = 3):
        self.max_sentences = max_sentences
        self.last_usage = Usage()

    def answer(self, system: str, user: str) -> dict:
        m = _EV.search(user)
        blocks = _BLOCK.findall(m.group(1)) if m else []
        if not blocks:
            return {"answered": False, "sentences": [], "missing": "No evidence was retrieved."}
        sents = [
            {"text": first_sentence(text), "kind": "fact", "cites": [eid]} for eid, text in blocks[: self.max_sentences]
        ]
        return {"answered": True, "sentences": sents, "missing": ""}
