"""Deterministic grounding checks on the model's cited sentences.

These checks are intentionally conservative and mechanical. They catch invented citations, missing
citations, numbers that the cited evidence does not contain, and proper nouns that neither the
evidence nor the question contain. They cannot judge subtler entailment; the eval's LLM judge does.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from ..data.models import Evidence

NUM_RE = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?")
WORD_RE = re.compile(r"[A-Za-zÀ-ÿØøÆæ][A-Za-zÀ-ÿØøÆæ'’\-]*")
VOICE_MAX_WORDS = 14
MAX_FACT_SENTENCES = 8


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def numbers(text: str) -> set[str]:
    out = set()
    for m in NUM_RE.finditer(text):
        s = m.group().rstrip(",.").replace(",", "")
        if s:
            out.add(s)
    return out


def proper_nouns(sentence: str) -> list[str]:
    """Capitalised words that are not the first word of the sentence."""
    words = WORD_RE.findall(sentence)
    out = []
    for w in words[1:]:
        base = re.split(r"['’]", w)[0].strip("-")
        if len(base) >= 3 and base[0].isupper() and base.lower() not in {"the", "and"}:
            out.append(base)
    return out


@dataclass
class CheckedSentence:
    text: str
    kind: str
    cites: list[str]
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def check_sentences(
    raw_sentences: list[dict],
    evidence: dict[str, Evidence],
    question: str,
    allowed_names: set[str],
) -> list[CheckedSentence]:
    q_norm = _norm(question)
    allowed = {_norm(n) for n in allowed_names}
    checked: list[CheckedSentence] = []
    for s in raw_sentences[:MAX_FACT_SENTENCES + 4]:
        text = str(s.get("text", "")).strip()
        kind = s.get("kind") if s.get("kind") in ("fact", "voice") else "fact"
        cites = [str(c).strip() for c in (s.get("cites") or []) if str(c).strip()]
        cs = CheckedSentence(text=text, kind=kind, cites=cites)
        checked.append(cs)
        if not text:
            cs.issues.append("empty sentence")
            continue

        if kind == "voice":
            if cites:
                cs.issues.append("voice sentence must not cite")
            if len(text.split()) > VOICE_MAX_WORDS:
                cs.issues.append(f"voice sentence longer than {VOICE_MAX_WORDS} words")
            if re.search(r"\d", text):
                cs.issues.append("voice sentence contains digits")
            for n in proper_nouns(text):
                if _norm(n) not in allowed and _norm(n) not in q_norm:
                    cs.issues.append(f"voice sentence contains name not in sources: {n}")
            continue

        if not cites:
            cs.issues.append("fact sentence has no citation")
            continue
        unknown = [c for c in cites if c not in evidence]
        if unknown:
            cs.issues.append("cites evidence that was not retrieved: " + ", ".join(unknown))
            continue

        cited_text = " \n".join(evidence[c].text for c in cites)
        cited_norm = _norm(cited_text)
        bad_nums = sorted(numbers(text) - numbers(cited_text))
        if bad_nums:
            cs.issues.append("numbers not in cited evidence: " + ", ".join(bad_nums))
        for n in proper_nouns(text):
            nn = _norm(n)
            if nn in allowed or nn in cited_norm:
                continue
            # allow a plural/possessive or a name echoed from the question
            if re.search(r"\b" + re.escape(nn.rstrip("s")), cited_norm) or nn in q_norm:
                continue
            cs.issues.append(f"name not in cited evidence: {n}")
    return checked


def allowed_names(island_name: str, alt_names: list[str], creature_names: list[str]) -> set[str]:
    names: set[str] = set()
    for full in [island_name, *alt_names, *creature_names]:
        for tok in re.findall(r"[A-Za-zÀ-ÿØøÆæ'’\-]+", full):
            if len(tok) >= 3:
                names.add(re.split(r"['’]", tok)[0])
    names |= {"NASA", "POWER", "GBIF", "IUCN", "Red", "List", "Wikipedia"}
    return names
