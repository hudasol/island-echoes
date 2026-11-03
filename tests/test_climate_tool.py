from __future__ import annotations

import pytest

from app.chat import grounding
from app.chat.service import ChatService
from app.data.climate_tool import MONTH_FULL, ClimateTool

from .fakes import ScriptedLLM


@pytest.fixture()
def tool(store, retriever):
    return ClimateTool(store, retriever.sources)


def test_wettest_month_comes_from_the_table(tool, store, retriever):
    isl = store.get("clipperton")
    ans = tool.answer(isl, "According to NASA POWER, which month has the most rain on Clipperton Island?")
    assert ans and ans.evidence_ids == ["POWER-CLI-PRECIP"]
    assert "August" in ans.sentences[0]["text"] and "13.4" in ans.sentences[0]["text"]


def test_named_month_value(tool, store):
    ans = tool.answer(store.get("socotra"), "What is the average air temperature on Socotra in June according to NASA POWER?")
    assert ans and "June" in ans.sentences[0]["text"] and "27.05" in ans.sentences[0]["text"]


def test_annual_value_and_comparison_use_both_islands(tool, store):
    ans = tool.answer(store.get("bouvet"), "Comparing annual average wind speed in NASA POWER, is Bouvet Island higher or lower than Pitcairn Island?")
    assert ans and ans.evidence_ids == ["POWER-BOU-WIND", "POWER-PIT-WIND"]
    assert "10.41" in ans.sentences[0]["text"] and "higher than" in ans.sentences[0]["text"]
    ann = tool.answer(store.get("clipperton"), "What is the annual rainfall in the NASA POWER climatology?")
    assert ann and "7.75" in ann.sentences[0]["text"]


@pytest.mark.parametrize("question", ["How old is the island?", "Why is the climate here so harsh for birds?", "Who discovered it?"])
def test_other_questions_fall_through(tool, store, question):
    assert tool.answer(store.get("pitcairn"), question) is None


def test_every_answer_passes_the_validator_when_month_names_are_allowed(tool, store, retriever):
    for slug in store.islands:
        isl = store.get(slug)
        ev = {e.id: e for e in retriever.sources.power_evidence(isl)}
        for q in ("which month is the warmest according to NASA POWER", "which month has the least rain in NASA POWER", "windiest month NASA"):
            ans = tool.answer(isl, q)
            assert ans is not None
            names = grounding.allowed_names(isl.name, isl.alt_names, []) | set(MONTH_FULL)
            checked = grounding.check_sentences(ans.sentences, ev, q, names)
            assert all(c.ok for c in checked), [c.issues for c in checked]


def test_service_routes_to_the_tool_without_calling_the_model(store, retriever):
    llm = ScriptedLLM()
    svc = ChatService(store, retriever, llm, climate=True)
    r = svc.respond("clipperton", "Which month has the most rain in NASA's climate data, and how much falls per day?")
    assert r.answered and not r.llm_called and not llm.calls and r.provider == "climate-tool"
    assert "August" in r.sentences[0].text and r.cited_ids == ["POWER-CLI-PRECIP"]


def test_service_without_the_tool_is_unchanged(store, retriever):
    llm = ScriptedLLM()
    svc = ChatService(store, retriever, llm)
    assert svc.climate is None
