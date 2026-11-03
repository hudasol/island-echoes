from __future__ import annotations

from app.chat.service import ChatService
from eval import arms

from .fakes import ScriptedLLM, fact, reply


def _record(r) -> dict:
    return {
        "id": "X", "answered": r.answered, "sentences": [{"text": s.text, "kind": s.kind, "cites": s.cites} for s in r.sentences],
        "raw_sentences": r.raw_sentences, "raw_issues": r.raw_issues, "second_sentences": r.second_sentences, "repaired": r.repaired,
        "first_answered": r.first_answered, "model_answered": r.model_answered, "llm_called": r.llm_called, "cited_ids": r.cited_ids,
        "rejected": r.rejected,
    }


def test_replayed_arms_match_live_runs(store, retriever):
    bad = reply(fact("The highest point is Mashanig at 1,900 m.", "SOC-011"))
    question = "How tall is the tallest mountain?"
    live = {
        "drop": ChatService(store, retriever, ScriptedLLM(bad, bad), fallback="drop").respond("socotra", question),
        "extractive": ChatService(store, retriever, ScriptedLLM(bad, bad), fallback="extractive").respond("socotra", question),
    }
    rec = _record(live["drop"])
    res = retriever.search("socotra", question)
    ev = {e.id: e for e in res.evidence}
    for arm in ("drop", "extractive"):
        got = arms.derive(rec, arm, ev, res.evidence, question)
        want = live[arm]
        assert got["answered"] == want.answered
        assert [s["text"] for s in got["sentences"]] == [s.text for s in want.sentences]
    raw = arms.derive(rec, "unvalidated", ev, res.evidence, question)
    assert raw["answered"] and "1,900" in raw["sentences"][0]["text"]
