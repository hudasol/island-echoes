from __future__ import annotations

import json
import re

import pytest

from app.data.sources import SourceStore
from eval import metrics
from eval.run_eval import load_questions, main, render_markdown

QUESTIONS = load_questions()


def evidence_text(store, source_store, island_slug, ev_id):
    isl = store.get(island_slug)
    if ev_id.startswith("POWER-"):
        return next(e.text for e in source_store.power_evidence(isl) if e.id == ev_id)
    if ev_id.startswith("GBIF-"):
        creature = next(c for c in isl.creatures if ev_id.startswith(f"GBIF-{isl.prefix}-{c.slug}-"))
        return next(e.text for e in source_store.gbif_evidence(isl, creature.slug) if e.id == ev_id)
    return store.fact(ev_id).statement


def test_thirty_well_formed_questions(store):
    assert len(QUESTIONS) == 30 and len({q["id"] for q in QUESTIONS}) == 30
    types = {q["type"] for q in QUESTIONS}
    assert {"single", "multi", "climate", "species", "conflict", "unanswerable", "injection"} <= types
    for q in QUESTIONS:
        isl = store.get(q["island"])
        isl.creature(q.get("creature"))
        for p in q["must_include"] + q.get("forbidden", []):
            re.compile(p)
        if q["should_refuse"]:
            assert q["forbidden"] or q.get("notes"), q["id"]
        else:
            assert q["expected_ids"] and q["must_include"], q["id"]


def test_every_creature_and_island_is_covered(store):
    assert {q["island"] for q in QUESTIONS} == set(store.islands)
    used = {(q["island"], q.get("creature") or store.get(q["island"]).creatures[0].slug) for q in QUESTIONS}
    for isl in store.islands.values():
        for c in isl.creatures:
            assert (isl.slug, c.slug) in used, f"no question for {c.slug}"


@pytest.mark.parametrize("q", [q for q in QUESTIONS if not q["should_refuse"]], ids=lambda q: q["id"])
def test_expected_answers_really_are_in_the_expected_sources(q, store, real_settings):
    ss = SourceStore(real_settings, store, http=object())
    texts = " ".join(evidence_text(store, ss, q["island"], i) for i in q["expected_ids"])
    for pat in q["must_include"]:
        assert re.search(pat, texts, re.I), f"{q['id']}: /{pat}/ not in expected sources"


@pytest.mark.parametrize("q", [q for q in QUESTIONS if not q["should_refuse"]], ids=lambda q: q["id"])
def test_retriever_surfaces_every_expected_source(q, retriever):
    got = {e.id for e in retriever.search(q["island"], q["question"], q.get("creature")).evidence}
    missing = set(q["expected_ids"]) - got
    assert not missing, f"{q['id']} retrieval missed {sorted(missing)}"


@pytest.mark.parametrize("q", [q for q in QUESTIONS if q["should_refuse"]], ids=lambda q: q["id"])
def test_unanswerable_questions_are_truly_absent_from_the_sources(q, store):
    """The forbidden pattern must not match any single fact of the island, or the question is answerable."""
    for pat in q.get("forbidden", []):
        for f in store.get(q["island"]).facts:
            assert not re.search(pat, f.statement), f"{q['id']}: {f.id} already contains the 'forbidden' value"


# ---- metrics ----------------------------------------------------------------------------
def test_wilson_interval_is_sane():
    lo, hi = metrics.wilson(27, 30)
    assert 0.74 < lo < 0.76 and 0.95 < hi < 0.98
    assert metrics.wilson(0, 0) == (0.0, 0.0)
    assert metrics.wilson(30, 30)[1] == 1.0


def rec(sentences, answered=True, cited=None, verdicts=None, raw=None, issues=None):
    r = {"id": "X", "answered": answered, "sentences": sentences, "cited_ids": cited or [], "repaired": bool(issues),
         "raw_sentences": raw or [], "raw_issues": issues or []}
    if verdicts is not None:
        r["judge"] = {"verdicts": verdicts}
    return r


def fs(text, *cites):
    return {"text": text, "kind": "fact", "cites": list(cites)}


def test_answerable_pass_requires_key_facts_and_no_bad_verdicts():
    q = {"id": "X", "type": "single", "should_refuse": False, "must_include": ["264"], "expected_ids": ["A-1"]}
    ok = metrics.score_question(q, rec([fs("All 264 left.", "A-1")], cited=["A-1"], verdicts={"0": "supported"}))
    assert ok.passed and ok.supported == 1 and ok.expected_hit == 1
    miss = metrics.score_question(q, rec([fs("Everyone left.", "A-1")], cited=["A-1"], verdicts={"0": "supported"}))
    assert not miss.passed and "missing key facts" in miss.detail
    bad = metrics.score_question(q, rec([fs("All 264 left.", "A-1")], cited=["A-1"], verdicts={"0": "contradicted"}))
    assert not bad.passed and bad.bad == 1
    refused = metrics.score_question(q, rec([], answered=False))
    assert not refused.passed and refused.detail == "false refusal"


def test_refusal_scoring_uses_answered_flag_and_forbidden_values():
    q = {"id": "X", "type": "unanswerable", "should_refuse": True, "must_include": [], "forbidden": [r"\d+ kg"]}
    assert metrics.score_question(q, rec([{"text": "I have no record.", "kind": "voice", "cites": []}], answered=False)).passed
    assert not metrics.score_question(q, rec([fs("I weigh 90 kg.", "A-1")], answered=True)).passed
    sneaky = metrics.score_question(q, rec([fs("I weigh 90 kg.", "A-1")], answered=False))
    assert not sneaky.passed and "forbidden" in sneaky.detail


def test_summary_aggregates_rates():
    q1 = {"id": "A", "type": "single", "should_refuse": False, "must_include": [], "expected_ids": []}
    q2 = {"id": "B", "type": "unanswerable", "should_refuse": True, "must_include": []}
    s = [
        metrics.score_question(q1, rec([fs("x", "A-1"), fs("y", "A-1")], cited=["A-1"], verdicts={"0": "supported", "1": "unsupported"})),
        metrics.score_question(q2, rec([], answered=False)),
    ]
    s[1].judged = True
    summ = metrics.summarise(s, {"A": None, "B": None})
    assert summ["groundedness"] == {"k": 1, "n": 2} and summ["hallucination_rate"] == {"k": 1, "n": 2}
    assert summ["refusal_accuracy"] == {"k": 1, "n": 1}


def test_raw_validator_failures_are_counted():
    q = {"id": "X", "type": "single", "should_refuse": False, "must_include": [], "expected_ids": []}
    raw = [fs("bad", "A-1"), fs("good", "A-1")]
    sc = metrics.score_question(q, rec([fs("good", "A-1")], raw=raw, issues=[{"text": "bad", "issues": ["number"]}]))
    assert sc.raw_fact_sentences == 2 and sc.raw_failed == 1 and sc.repaired


# ---- end-to-end rescoring of a saved run (synthetic data, only to exercise the report code) -------
def test_rescore_saved_run_writes_report(tmp_path):
    records = []
    for q in QUESTIONS[:3]:
        records.append({"id": q["id"], "answered": True, "sentences": [fs("All 264 left in 1790.", "TDC-019")],
                        "cited_ids": ["TDC-019"], "retrieved_ids": ["TDC-019"], "raw_sentences": [], "raw_issues": [],
                        "rejected": [], "repaired": False, "llm_called": True,
                        "judge": {"verdicts": {"0": "supported"}, "reasons": {"0": "ok"}, "states_conflict": "not_applicable"}})
    run = tmp_path / "run.json"
    run.write_text(json.dumps({"meta": {"timestamp": "t", "commit": "c", "answer_model": "m", "judge_model": "j"}, "records": records}))
    out = tmp_path / "report"
    assert main(["--from-run", str(run), "--ids", "Q01,Q02,Q03", "--out", str(out)]) == 0
    md = out.with_suffix(".md").read_text()
    assert "| Groundedness |" in md and "100.0% (3/3" in md and "## Per question" in md
    assert render_markdown  # imported symbol stays referenced
