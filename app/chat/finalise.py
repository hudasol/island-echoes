"""What to show after the grounding checks have run.

`drop` is the behaviour of version 1.1: a sentence that still fails after the repair attempt is removed. `extractive`
replaces such a fact sentence with the sentence of the cited source that best matches it, copied word for word, so a
rejection no longer turns an answer into a refusal. A replacement is only made when the model said it could answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..data.models import Evidence
from ..data.retrieval import tokenize
from .grounding import CheckedSentence

MAX_FACT_SENTENCES = 5
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n+")


@dataclass
class Finalised:
    kept: list[CheckedSentence]
    dropped: list[dict]
    replaced: int


def source_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SPLIT.split(text) if p.strip()]
    return parts or [text.strip()]


def best_sentence(evidence: list[Evidence], reference: str) -> tuple[Evidence, str] | None:
    """The source sentence that shares most words with `reference`, copied verbatim."""
    ref = set(tokenize(reference))
    best: tuple[int, int, Evidence, str] | None = None
    for ei, e in enumerate(evidence):
        for s in source_sentences(e.text):
            score = len(ref & set(tokenize(s)))
            if score == 0:
                continue
            cand = (score, -ei, e, s)
            if best is None or cand[:2] > best[:2]:
                best = cand
    return (best[2], best[3]) if best else None


def finalise(
    checked: list[CheckedSentence],
    answered: bool,
    evidence: dict[str, Evidence],
    ranked: list[Evidence],
    question: str,
    mode: str = "drop",
) -> Finalised:
    dropped = [{"text": c.text, "issues": c.issues} for c in checked if not c.ok]
    if mode != "extractive" or not answered:
        return Finalised([c for c in checked if c.ok], dropped, 0)
    out: list[CheckedSentence] = []
    seen: set[str] = set()
    replaced = 0
    for c in checked:
        if c.ok:
            out.append(c)
            seen.add(c.text)
            continue
        if c.kind != "fact" or not c.text.strip():
            continue
        pool = [evidence[i] for i in c.cites if i in evidence] or ranked[:3]
        hit = best_sentence(pool, c.text + " " + question) or best_sentence(ranked, question)
        if hit is None or hit[1] in seen:
            continue
        e, s = hit
        seen.add(s)
        out.append(CheckedSentence(text=s, kind="fact", cites=[e.id]))
        replaced += 1
    facts = 0
    final: list[CheckedSentence] = []
    for c in out:
        if c.kind == "fact":
            facts += 1
            if facts > MAX_FACT_SENTENCES:
                continue
        final.append(c)
    return Finalised(final, dropped, replaced)
