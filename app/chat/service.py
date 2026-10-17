from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..data.islands import IslandStore
from ..data.models import Evidence
from ..data.retrieval import Retriever, tokenize
from . import grounding, prompts
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


class ChatService:
    def __init__(self, islands: IslandStore, retriever: Retriever, llm: AnswerLLM | None):
        self.islands, self.retriever, self.llm = islands, retriever, llm

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
        base = dict(
            island=island.slug, creature=creature.slug, retrieved=res.evidence, notes=list(res.notes),
            retrieval_ms=retrieval_ms, retrieval_mode=getattr(self.retriever, "mode", "bm25"),
            provider=getattr(self.llm, "provider", ""), model=getattr(self.llm, "model", ""),
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
        system = prompts.build_system(island, creature)

        out = self._attempt(system, message, res.evidence, history, None, meter)
        checked = grounding.check_sentences(out.get("sentences", []), evidence, message, names)
        raw = [{"text": c.text, "kind": c.kind, "cites": c.cites} for c in checked]
        raw_issues = [{"text": c.text, "issues": c.issues} for c in checked if c.issues]
        repaired = False

        if raw_issues:
            repaired = True
            fb = prompts.repair_feedback([(i["text"], i["issues"]) for i in raw_issues])
            out2 = self._attempt(system, message, res.evidence, history, fb, meter)
            checked = grounding.check_sentences(out2.get("sentences", []), evidence, message, names)
            out = out2

        kept = [c for c in checked if c.ok]
        dropped = [{"text": c.text, "issues": c.issues} for c in checked if not c.ok]
        fact_kept = [c for c in kept if c.kind == "fact"]

        answered = bool(out.get("answered")) and bool(fact_kept)
        missing = str(out.get("missing") or "").strip()
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
