"""Baselines to measure the system against.

Retrieval floors (used by `python -m eval.retrieval_eval`):
    random       a random order of the island's facts, averaged over many seeds
    file-order   the facts in the order they appear in the file
    overlap      count of shared plain words with the question: no stemming, no IDF, no synonyms

End to end systems (used by `python -m eval.run_eval --system NAME`):
    refuse-all   says the sources lack the answer to everything. No model.
    closed-book  the same model and persona with no retrieval and no sources
    unvalidated  the same retrieval and prompt, but the model's first reply is shown as it is: no checks,
                 no repair. Citations that the model invents or gets wrong are not removed.
    full         the real pipeline (retrieval, model, grounding validator, one repair)

Every system is scored by the same code in eval/metrics.py, plus `claims_outside_sources` below, which does
not rely on citations and so can be applied to a system that makes none.
"""

from __future__ import annotations

import random
import re
import statistics
from dataclasses import dataclass

from app.chat import grounding, prompts
from app.chat.service import NO_EVIDENCE_LINE, ChatResult, Sentence, _Meter
from app.data.islands import IslandStore
from app.data.models import Evidence
from app.data.retrieval import Retriever
from app.data.sources import SourceStore, SourceUnavailable

SYSTEMS = ("full", "unvalidated", "closed-book", "refuse-all")
RETRIEVAL_BASELINES = ("random", "file-order", "overlap")
RANDOM_SEEDS = 200

_STOP = frozenset(
    "a an and are as at be but by do does for from had has have how i if in into is it its me my no not of on or "
    "so than that the their then there these they this to was we were what when where which who why will with you your".split()
)


# --------------------------------------------------------------------------- retrieval floors
def candidates(retriever: Retriever, island_slug: str, creature_slug: str | None) -> list[Evidence]:
    """The pool the real retriever ranks: island level facts and the selected creature's facts."""
    island = retriever.islands.get(island_slug)
    creature = island.creature(creature_slug)
    return [retriever.islands.fact_to_evidence(island, f) for f in island.facts if f.subject in ("island", creature.slug)]


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1}


def rank_file_order(pool: list[Evidence]) -> list[Evidence]:
    return list(pool)


def rank_overlap(pool: list[Evidence], question: str) -> list[Evidence]:
    """Most shared plain words first; ties keep file order. Facts sharing no word are left out, like BM25 does."""
    q = _words(question)
    scored = [(len(q & _words(e.text)), i, e) for i, e in enumerate(pool)]
    return [e for s, _i, e in sorted(scored, key=lambda t: (-t[0], t[1])) if s > 0]


def rank_random(pool: list[Evidence], seed: int) -> list[Evidence]:
    out = list(pool)
    random.Random(seed).shuffle(out)
    return out


def mean_scores(per_seed: list[dict]) -> dict:
    """Average metric dictionaries from several random orderings into one expected score per question."""
    return {k: statistics.fmean(d[k] for d in per_seed) for k in per_seed[0]}


# --------------------------------------------------------------------------- end to end systems
CLOSED_BOOK_SYSTEM = """You are the {common_name} ({scientific_name}) of {island_name}, speaking in the first person \
as a field agent that reports on its own island.

You have no documents. Answer the user's question from what you already know. If you do not know, say so: set \
`answered` to false and explain in `missing`.

Return your reply as JSON. FACT sentences (kind "fact") state information; leave `cites` empty because you have \
no sources. VOICE sentences (kind "voice") carry no information, at most 12 words. Answer in at most 5 fact \
sentences. Plain first-person prose, no markdown."""


def _no_evidence(island: str, creature: str, model_name: str, missing: str) -> ChatResult:
    return ChatResult(
        island=island, creature=creature, answered=False,
        sentences=[Sentence(NO_EVIDENCE_LINE, "voice", [])], missing=missing, retrieved=[], cited_ids=[],
        provider="none", model=model_name,
    )


class RefuseAllService:
    """Never answers. The floor for refusal accuracy, and the ceiling for false refusals."""

    llm = None

    def __init__(self, islands: IslandStore, retriever: Retriever, llm=None):
        self.islands, self.retriever = islands, retriever

    def respond(self, island_slug: str, message: str, creature_slug: str | None = None, history=None) -> ChatResult:
        isl = self.islands.get(island_slug)
        c = isl.creature(creature_slug)
        return _no_evidence(isl.slug, c.slug, "refuse-all", "This baseline declines every question.")


class ClosedBookService:
    """The model answers from memory: no retrieval, no sources, no checks."""

    def __init__(self, islands: IslandStore, retriever: Retriever, llm):
        self.islands, self.retriever, self.llm = islands, retriever, llm

    def respond(self, island_slug: str, message: str, creature_slug: str | None = None, history=None) -> ChatResult:
        isl = self.islands.get(island_slug)
        c = isl.creature(creature_slug)
        system = CLOSED_BOOK_SYSTEM.format(common_name=c.common_name, scientific_name=c.scientific_name, island_name=isl.name)
        meter = _Meter()
        out = _call(self.llm, system, f"<question>\n{' '.join(message.split())}\n</question>", meter)
        sentences = [Sentence(s["text"], s["kind"], []) for s in out["sentences"] if s["text"].strip()]
        answered = bool(out["answered"]) and any(s.kind == "fact" for s in sentences)
        return ChatResult(
            island=isl.slug, creature=c.slug, answered=answered, sentences=sentences, missing=out["missing"],
            retrieved=[], cited_ids=[], llm_called=True, llm_ms=meter.ms, tokens_in=meter.tok_in,
            tokens_out=meter.tok_out, provider=self.llm.provider, model=self.llm.model, retrieval_mode="none",
        )


class UnvalidatedService:
    """Retrieval and the model exactly as in production, but the first reply is shown as it is."""

    def __init__(self, islands: IslandStore, retriever: Retriever, llm):
        self.islands, self.retriever, self.llm = islands, retriever, llm

    def respond(self, island_slug: str, message: str, creature_slug: str | None = None, history=None) -> ChatResult:
        isl = self.islands.get(island_slug)
        c = isl.creature(creature_slug)
        message = " ".join(message.split())
        res = self.retriever.search(isl.slug, message, c.slug)
        base = dict(island=isl.slug, creature=c.slug, retrieved=res.evidence, notes=list(res.notes),
                    retrieval_mode=getattr(self.retriever, "mode", "bm25"), provider=self.llm.provider, model=self.llm.model)
        if not res.has_evidence:
            return ChatResult(answered=False, sentences=[Sentence(NO_EVIDENCE_LINE, "voice", [])],
                              missing="Nothing in the sources relates to this question.", cited_ids=[], **base)
        meter = _Meter()
        out = _call(self.llm, prompts.build_system(isl, c), prompts.build_user(message, res.evidence), meter)
        evidence = {e.id: e for e in res.evidence}
        names = grounding.allowed_names(isl.name, isl.alt_names, [c.common_name, c.scientific_name])
        checked = grounding.check_sentences(out["sentences"], evidence, message, names)
        # the checks run only to count what a validator would have caught; every sentence is kept
        sentences = [Sentence(c_.text, c_.kind, c_.cites) for c_ in checked if c_.text]
        cited = list(dict.fromkeys(i for s in sentences for i in s.cites))
        return ChatResult(
            answered=bool(out["answered"]) and any(s.kind == "fact" for s in sentences), sentences=sentences,
            missing=out["missing"], cited_ids=cited, raw_sentences=[{"text": c_.text, "kind": c_.kind, "cites": c_.cites} for c_ in checked],
            raw_issues=[{"text": c_.text, "issues": c_.issues} for c_ in checked if c_.issues], llm_called=True,
            llm_ms=meter.ms, tokens_in=meter.tok_in, tokens_out=meter.tok_out, **base,
        )


def _call(llm, system: str, user: str, meter: _Meter) -> dict:
    import time

    t0 = time.perf_counter()
    try:
        out = llm.answer(system, user)
    finally:
        meter.ms += (time.perf_counter() - t0) * 1000
    usage = getattr(llm, "last_usage", None)
    meter.tok_in += getattr(usage, "input_tokens", 0) or 0
    meter.tok_out += getattr(usage, "output_tokens", 0) or 0
    return {"answered": bool(out.get("answered")), "sentences": list(out.get("sentences") or []), "missing": str(out.get("missing") or "")}


def make_service(system: str, islands: IslandStore, retriever: Retriever, llm):
    """The object run_eval answers questions with. `full` is the production service."""
    from app.chat.service import ChatService

    if system == "full":
        return ChatService(islands, retriever, llm)
    if system == "refuse-all":
        return RefuseAllService(islands, retriever)
    if system == "closed-book":
        return ClosedBookService(islands, retriever, llm)
    if system == "unvalidated":
        return UnvalidatedService(islands, retriever, llm)
    raise ValueError(f"unknown system {system!r}; choose from {', '.join(SYSTEMS)}")


# --------------------------------------------------------------------------- claims outside the sources
@dataclass
class IslandPool:
    text_norm: str
    numbers: set[str]
    names: set[str]


def build_pools(islands: IslandStore, sources: SourceStore) -> dict[str, IslandPool]:
    """Everything the system may legitimately say about each island: its facts, NASA POWER and GBIF text."""
    pools: dict[str, IslandPool] = {}
    for isl in islands.islands.values():
        texts = [f.statement for f in isl.facts]
        try:
            texts += [e.text for e in sources.power_evidence(isl, None)]
        except SourceUnavailable:
            pass
        for c in isl.creatures:
            try:
                texts += [e.text for e in sources.gbif_evidence(isl, c.slug)]
            except SourceUnavailable:
                pass
        joined = "\n".join(texts)
        names = grounding.allowed_names(isl.name, isl.alt_names, [x for c in isl.creatures for x in (c.common_name, c.scientific_name)])
        pools[isl.slug] = IslandPool(grounding._norm(joined), grounding.numbers(joined), {grounding._norm(n) for n in names})
    return pools


def claims_outside_sources(sentence: str, question: str, pool: IslandPool) -> list[str]:
    """Numbers and names in a sentence that appear nowhere in the island's sources or the question.

    A lower bound on unsupported content: a sentence built only from words that occur in the sources can still
    be wrong. It does not use citations, so it applies to a system that gives none.
    """
    out = [f"number {n}" for n in sorted(grounding.numbers(sentence) - pool.numbers - grounding.numbers(question))]
    q = grounding._norm(question)
    for n in grounding.proper_nouns(sentence):
        nn = grounding._norm(n)
        if nn in pool.names or nn in pool.text_norm or nn in q or re.search(r"\b" + re.escape(nn.rstrip("s")), pool.text_norm):
            continue
        out.append(f"name {n}")
    return out


def outside_sources_summary(run: dict, questions: dict[str, dict], pools: dict[str, IslandPool]) -> dict:
    """Over a stored run: fact sentences and answers that contain a number or name found nowhere in the sources."""
    sent_k = sent_n = ans_k = ans_n = 0
    for rec in run["records"]:
        q = questions.get(rec["id"])
        if not q or "error" in rec or not rec.get("answered"):
            continue
        bad = 0
        facts = [s for s in rec["sentences"] if s["kind"] == "fact"]
        for s in facts:
            if claims_outside_sources(s["text"], q["question"], pools[q["island"]]):
                bad += 1
        sent_n += len(facts)
        sent_k += bad
        ans_n += 1
        ans_k += bool(bad)
    return {"sentences": {"k": sent_k, "n": sent_n}, "answers": {"k": ans_k, "n": ans_n}}


__all__ = [
    "RETRIEVAL_BASELINES", "SYSTEMS", "build_pools", "candidates", "claims_outside_sources", "make_service",
    "mean_scores", "outside_sources_summary", "rank_file_order", "rank_overlap", "rank_random",
]
