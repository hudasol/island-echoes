"""Scoring for the eval. Pure functions over recorded runs, so scoring never needs the network."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

SUPPORTED = "supported"
PARTIAL = "partially_supported"
BAD = {"unsupported", "contradicted"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def pct(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}; 95% CI {100 * lo:.0f}-{100 * hi:.0f}%)"


def answer_text(rec: dict) -> str:
    return " ".join(s["text"] for s in rec["sentences"])


def key_fact_hits(question: dict, rec: dict) -> tuple[int, int]:
    text = answer_text(rec)
    pats = question.get("must_include", [])
    return sum(1 for p in pats if re.search(p, text, re.I)), len(pats)


def forbidden_hit(question: dict, rec: dict) -> bool:
    text = answer_text(rec)
    return any(re.search(p, text) for p in question.get("forbidden", []))


def refusal_ok(question: dict, rec: dict) -> bool:
    return (not rec["answered"]) and not forbidden_hit(question, rec)


@dataclass
class QuestionScore:
    id: str
    type: str
    should_refuse: bool
    passed: bool
    detail: str
    fact_sentences: int
    supported: int
    partial: int
    bad: int
    key_hits: int
    key_total: int
    expected_hit: int
    expected_total: int
    raw_fact_sentences: int
    raw_failed: int
    repaired: bool
    judged: bool


def score_question(question: dict, rec: dict) -> QuestionScore:
    facts = [s for s in rec["sentences"] if s["kind"] == "fact"]
    verdicts = rec.get("judge", {}).get("verdicts", {})
    judged = bool(verdicts)
    sup = par = bad = 0
    for i, s in enumerate(rec["sentences"]):
        if s["kind"] != "fact":
            continue
        v = verdicts.get(str(i))
        if v == SUPPORTED:
            sup += 1
        elif v == PARTIAL:
            par += 1
        elif v in BAD:
            bad += 1
    kh, kt = key_fact_hits(question, rec)
    cited = set(rec.get("cited_ids", []))
    exp = set(question.get("expected_ids", []))
    raw_facts = [s for s in rec.get("raw_sentences", []) if s["kind"] == "fact"]
    raw_failed = sum(1 for i in rec.get("raw_issues", []) if i["text"] in {s["text"] for s in raw_facts})

    if question["should_refuse"]:
        ok = refusal_ok(question, rec)
        detail = "refused correctly" if ok else ("answered when sources lack it" if rec["answered"] else "asserted a forbidden value")
        if ok and judged and bad:
            ok, detail = False, "refused but added an unsupported claim"
    else:
        ok = rec["answered"] and kt == kh and (not judged or bad == 0)
        if not rec["answered"]:
            detail = "false refusal"
        elif kt != kh:
            detail = f"missing key facts ({kh}/{kt})"
        elif judged and bad:
            detail = "unsupported claim"
        else:
            detail = "ok"
    return QuestionScore(
        id=question["id"], type=question["type"], should_refuse=question["should_refuse"], passed=ok, detail=detail,
        fact_sentences=len(facts), supported=sup, partial=par, bad=bad, key_hits=kh, key_total=kt,
        expected_hit=len(exp & cited), expected_total=len(exp), raw_fact_sentences=len(raw_facts),
        raw_failed=raw_failed, repaired=bool(rec.get("repaired")), judged=judged,
    )


def summarise(scores: list[QuestionScore], conflict: dict[str, bool | None]) -> dict:
    judged = [s for s in scores if s.judged]
    fact_total = sum(s.fact_sentences for s in judged)
    sup = sum(s.supported for s in judged)
    par = sum(s.partial for s in judged)
    bad = sum(s.bad for s in judged)
    answerable = [s for s in scores if not s.should_refuse]
    refuse = [s for s in scores if s.should_refuse]
    exp_h = sum(s.expected_hit for s in answerable)
    exp_t = sum(s.expected_total for s in answerable)
    key_h = sum(s.key_hits for s in answerable)
    key_t = sum(s.key_total for s in answerable)
    raw_t = sum(s.raw_fact_sentences for s in scores)
    raw_f = sum(s.raw_failed for s in scores)
    conf = [v for k, v in conflict.items() if v is not None]
    return {
        "questions": len(scores),
        "judged_questions": len(judged),
        "fact_sentences_judged": fact_total,
        "groundedness": {"k": sup, "n": fact_total},
        "partially_supported": {"k": par, "n": fact_total},
        "hallucination_rate": {"k": bad, "n": fact_total},
        "answers_with_hallucination": {
            "k": sum(1 for s in judged if s.bad > 0) + sum(1 for s in refuse if not s.passed and "answered" in s.detail),
            "n": len(judged) if judged else len(scores),
        },
        "refusal_accuracy": {"k": sum(1 for s in refuse if s.passed), "n": len(refuse)},
        "false_refusals": {"k": sum(1 for s in answerable if s.detail == "false refusal"), "n": len(answerable)},
        "key_fact_recall": {"k": key_h, "n": key_t},
        "expected_source_recall": {"k": exp_h, "n": exp_t},
        "validator_first_pass_failures": {"k": raw_f, "n": raw_t},
        "repaired_answers": {"k": sum(1 for s in scores if s.repaired), "n": len(scores)},
        "conflicts_reported": {"k": sum(1 for v in conf if v), "n": len(conf)},
        "questions_passed": {"k": sum(1 for s in scores if s.passed), "n": len(scores)},
    }
