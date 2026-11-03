from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from ..data.climate_tool import MONTH_FULL, ClimateTool
from ..data.islands import IslandStore
from ..data.models import Evidence
from ..data.retrieval import Retriever, tokenize
from . import grounding, prompts
from .finalise import finalise
from .llm import AnswerLLM, LLMError


class ChatUnavailable(RuntimeError):
    """Raised when no LLM is configured."""


NO_EVIDENCE_LINE = "My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess."
DROPPED_LINE = "I can't back that with my sources, so I won't state it."


@dataclass
class Sentence:
    text: str
    kind: str
    cites: list[str]


@dataclass
class ChatResult:
    island: str
    creature: str
    answered: bool
    sentences: list[Sentence]
    missing: str
    retrieved: list[Evidence]
    cited_ids: list[str]
    rejected: list[dict] = field(default_factory=list)  # final-stage drops
    raw_sentences: list[dict] = field(default_factory=list)  # model's first attempt, before checks
    raw_issues: list[dict] = field(default_factory=list)
    repaired: bool = False
    second_sentences: list[dict] = field(default_factory=list)  # the repair attempt with its issues, for replay
    replaced: int = 0
    first_answered: bool = False  # the model's own `answered` flag on its first attempt
    model_answered: bool = False  # and on the attempt that was finalised
    llm_called: bool = False
    notes: list[str] = field(default_factory=list)
    retrieval_ms: float = 0.0
    llm_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    provider: str = ""
    model: str = ""
    retrieval_mode: str = ""


@dataclass
class _Meter:
    ms: float = 0.0
    tok_in: int = 0
    tok_out: int = 0


def _checked_missing(text: str, question: str, names: set[str]) -> str:
    """The model's free-text `missing` note is shown to users, so it gets the voice-sentence checks: no digits and
    no names that are not in the question or the island and creature names. A note that fails is replaced."""
    if re.search(r"\d", text):
        return ""
    allowed = {grounding._norm(n) for n in names}
    q = grounding._norm(question)
    if any(grounding._norm(n) not in allowed and grounding._norm(n) not in q for n in grounding.proper_nouns(text)):
        return ""
    return text


class ChatService:
    def __init__(
        self,
        islands: IslandStore,
        retriever: Retriever,
        llm: AnswerLLM | None,
        *,
        fallback: str = "drop",
        climate: bool = False,
        month_names_ok: bool = False,
    ):
        self.islands, self.retriever, self.llm = islands, retriever, llm
        self.fallback, self.month_names_ok = fallback, month_names_ok
        self.climate = ClimateTool(islands, retriever.sources) if climate else None

    # ------------------------------------------------------------------
    def respond(
        self,
        island_slug: str,
        message: str,
        creature_slug: str | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> ChatResult:
        island = self.islands.get(island_slug)
        creature = island.creature(creature_slug)
        message = " ".join(message.split())

        query = message
        if history and len(tokenize(message)) < 4:
            last_user = next((t for who, t in reversed(history) if who == "User"), "")
            query = f"{last_user} {message}".strip()

        t0 = time.perf_counter()
        res = self.retriever.search(island.slug, query, creature.slug)
        retrieval_ms = (time.perf_counter() - t0) * 1000
        meter = _Meter()
        base: dict[str, Any] = dict(
            island=island.slug, creature=creature.slug, retrieved=res.evidence, notes=list(res.notes),
            retrieval_ms=retrieval_ms, retrieval_mode=getattr(self.retriever, "mode", "bm25"),
            provider=getattr(self.llm, "provider", ""), model=getattr(self.llm, "model", ""),
        )

        if self.climate is not None:
            hit = self.climate.answer(island, message)
            if hit is not None:
                return ChatResult(
                    answered=True,
                    sentences=[Sentence(x["text"], x["kind"], x["cites"]) for x in hit.sentences],
                    missing="",
                    cited_ids=hit.evidence_ids,
                    **{**base, "notes": [*base["notes"], f"climate tool: {hit.route}"], "provider": "climate-tool", "model": hit.route},
                )

        if not res.has_evidence:
            return ChatResult(
                answered=False,
                sentences=[Sentence(NO_EVIDENCE_LINE, "voice", [])],
                missing="Nothing in the curated island notes, NASA POWER data or GBIF records relates to this question.",
                cited_ids=[],
                **base,
            )
        if self.llm is None:
            raise ChatUnavailable("ANTHROPIC_API_KEY is not configured")

        evidence = {e.id: e for e in res.evidence}
        names = grounding.allowed_names(island.name, island.alt_names, [creature.common_name, creature.scientific_name])
        if self.month_names_ok:
            names |= set(MONTH_FULL)
        system = prompts.build_system(island, creature)

        out = self._attempt(system, message, res.evidence, history, None, meter)
        checked = grounding.check_sentences(out.get("sentences", []), evidence, message, names)
        first_answered = bool(out.get("answered"))
        raw = [{"text": c.text, "kind": c.kind, "cites": c.cites} for c in checked]
        raw_issues = [{"text": c.text, "issues": c.issues} for c in checked if c.issues]
        repaired = False
        second: list[dict] = []

        if raw_issues:
            repaired = True
            fb = prompts.repair_feedback([(str(i["text"]), list(i["issues"])) for i in raw_issues])
            out2 = self._attempt(system, message, res.evidence, history, fb, meter)
            checked = grounding.check_sentences(out2.get("sentences", []), evidence, message, names)
            out = out2
        second = [{"text": c.text, "kind": c.kind, "cites": c.cites, "issues": c.issues} for c in checked]

        fin = finalise(checked, bool(out.get("answered")), evidence, res.evidence, message, self.fallback)
        kept, dropped = fin.kept, fin.dropped
        fact_kept = [c for c in kept if c.kind == "fact"]

        answered = bool(out.get("answered")) and bool(fact_kept)
        missing = _checked_missing(str(out.get("missing") or "").strip(), message, names)
        sentences = [Sentence(c.text, c.kind, c.cites) for c in kept]
        if not fact_kept and not any(c.kind == "voice" for c in kept):
            sentences = [Sentence(DROPPED_LINE, "voice", [])]
        if not answered and not missing:
            missing = "The retrieved sources do not directly answer this question."

        cited: list[str] = []
        for s in sentences:
            for c in s.cites:
                if c not in cited:
                    cited.append(c)
        return ChatResult(
            answered=answered,
            sentences=sentences,
            missing=missing,
            cited_ids=cited,
            rejected=dropped,
            raw_sentences=raw,
            raw_issues=raw_issues,
            repaired=repaired,
            second_sentences=second,
            replaced=fin.replaced,
            first_answered=first_answered,
            model_answered=bool(out.get("answered")),
            llm_called=True,
            llm_ms=meter.ms,
            tokens_in=meter.tok_in,
            tokens_out=meter.tok_out,
            **base,
        )

    def _attempt(self, system, message, evidence, history, feedback, meter) -> dict:
        assert self.llm is not None
        user = prompts.build_user(message, evidence, history, feedback)
        t0 = time.perf_counter()
        try:
            out = self.llm.answer(system, user)
        finally:
            meter.ms += (time.perf_counter() - t0) * 1000
        usage = getattr(self.llm, "last_usage", None)
        meter.tok_in += getattr(usage, "input_tokens", 0) or 0
        meter.tok_out += getattr(usage, "output_tokens", 0) or 0
        if not isinstance(out, dict) or not isinstance(out.get("sentences", []), list):
            raise LLMError("malformed model output")
        return out
