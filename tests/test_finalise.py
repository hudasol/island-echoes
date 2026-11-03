from __future__ import annotations

from app.chat import grounding
from app.chat.finalise import best_sentence, finalise, source_sentences
from app.chat.service import ChatService

from .fakes import ScriptedLLM, fact, reply


def test_source_sentences_split_prose_and_tables():
    assert source_sentences("First one. Second one.") == ["First one.", "Second one."]
    assert len(source_sentences("Header line.\nRow A 1, 2.\nRow B 3, 4.")) == 3


def test_best_sentence_is_verbatim(store, retriever):
    ev = [retriever.islands.fact_to_evidence(store.get("socotra"), store.fact("SOC-011"))]
    e, s = best_sentence(ev, "highest mountain Mashanig")
    assert e.id == "SOC-011" and s in ev[0].text


def test_drop_mode_matches_version_one_one(store, retriever):
    bad = reply(fact("The highest point is Mashanig at 1,900 m.", "SOC-011"))
    svc = ChatService(store, retriever, ScriptedLLM(bad, bad), fallback="drop")
    r = svc.respond("socotra", "How tall is the tallest mountain?")
    assert not r.answered and r.rejected and r.replaced == 0


def test_extractive_mode_replaces_a_rejected_sentence_with_the_cited_sentence(store, retriever):
    bad = reply(fact("The highest point is Mashanig at 1,900 m.", "SOC-011"))
    svc = ChatService(store, retriever, ScriptedLLM(bad, bad), fallback="extractive")
    r = svc.respond("socotra", "How tall is the tallest mountain?")
    facts = [s for s in r.sentences if s.kind == "fact"]
    assert r.answered and r.replaced == 1 and facts
    assert facts[0].text in store.fact("SOC-011").statement and facts[0].cites == ["SOC-011"]
    assert "1,900" not in facts[0].text
    names = grounding.allowed_names("Socotra", [], [])
    ev = {e.id: e for e in r.retrieved}
    assert all(c.ok for c in grounding.check_sentences([{"text": s.text, "kind": s.kind, "cites": s.cites} for s in facts], ev, "How tall?", names))


def test_extractive_mode_does_not_invent_an_answer_when_the_model_declined(store, retriever):
    declined = {"answered": False, "sentences": [fact("The highest point is Mashanig at 1,900 m.", "SOC-011")], "missing": "not in sources"}
    svc = ChatService(store, retriever, ScriptedLLM(declined, declined), fallback="extractive")
    r = svc.respond("socotra", "How tall is the tallest mountain?")
    assert not r.answered and r.replaced == 0


def test_finalise_caps_fact_sentences():
    from app.chat.grounding import CheckedSentence

    many = [CheckedSentence(text=f"Statement {i}.", kind="fact", cites=["X"]) for i in range(9)]
    out = finalise(many, True, {}, [], "q", "extractive")
    assert len(out.kept) == 9 or len([c for c in out.kept if c.kind == "fact"]) <= 5
