from __future__ import annotations

import pytest

from app.chat.llm import LLMError
from app.chat.service import DROPPED_LINE, ChatService, ChatUnavailable

from .fakes import ScriptedLLM, fact, reply, voice


def svc(store, retriever, llm):
    return ChatService(store, retriever, llm)


def test_happy_path_returns_cited_answer(store, retriever):
    llm = ScriptedLLM(reply(
        voice("Checking my instruments."),
        fact("Socotra's highest point is Mashanig in the Hajhir Mountains at about 1,503 m, according to Wikipedia.", "SOC-011"),
    ))
    r = svc(store, retriever, llm).respond("socotra", "What is the tallest mountain?")
    assert r.answered and r.cited_ids == ["SOC-011"] and not r.repaired and not r.rejected
    assert r.llm_called and len(llm.calls) == 1
    system, user = llm.calls[0]
    assert "Socotra buzzard" in system and "[SOC-011]" in user and "<question>" in user


def test_invented_number_triggers_one_repair_then_passes(store, retriever):
    llm = ScriptedLLM(
        reply(fact("The highest point is Mashanig at 1,900 m.", "SOC-011")),
        reply(fact("The highest point is Mashanig at about 1,503 m, according to Wikipedia.", "SOC-011")),
    )
    r = svc(store, retriever, llm).respond("socotra", "How tall is the tallest mountain?")
    assert r.repaired and r.answered and not r.rejected
    assert r.raw_issues and "1900" in r.raw_issues[0]["issues"][0]
    assert "<validation_feedback>" in llm.calls[1][1] and "1900" in llm.calls[1][1]
    assert "<validation_feedback>" not in llm.calls[0][1]


def test_unfixable_claims_are_dropped_not_shown(store, retriever):
    bad = reply(fact("The highest point is Mashanig at 1,900 m.", "SOC-011"))
    llm = ScriptedLLM(bad, bad)
    r = svc(store, retriever, llm).respond("socotra", "How tall is the tallest mountain?")
    assert not r.answered and r.cited_ids == []
    assert [s.text for s in r.sentences] == [DROPPED_LINE]
    assert r.rejected and "1900" in r.rejected[0]["issues"][0]


def test_model_can_decline_with_missing(store, retriever):
    llm = ScriptedLLM(reply(
        voice("My sensors hold nothing on that."),
        answered=False,
        missing="The sources give no visitor numbers.",
    ))
    r = svc(store, retriever, llm).respond("socotra", "How many tourists visit the island each year?")
    assert not r.answered and r.missing == "The sources give no visitor numbers."
    assert r.sentences[0].kind == "voice"


def test_answered_true_without_any_surviving_fact_is_not_answered(store, retriever):
    llm = ScriptedLLM(reply(voice("Here you go.")))
    r = svc(store, retriever, llm).respond("socotra", "Tell me about the history of the island")
    assert not r.answered and r.missing


def test_no_overlap_question_never_calls_the_model(store, retriever):
    llm = ScriptedLLM()
    r = svc(store, retriever, llm).respond("pitcairn", "How do I bake sourdough bread?")
    assert not r.answered and not r.llm_called and llm.calls == []
    assert r.sentences[0].kind == "voice" and r.retrieved == []


def test_missing_llm_raises_only_when_it_is_needed(store, retriever):
    service = svc(store, retriever, None)
    assert not service.respond("pitcairn", "How do I bake sourdough bread?").answered
    with pytest.raises(ChatUnavailable):
        service.respond("socotra", "What is the tallest mountain?")


def test_llm_errors_propagate(store, retriever):
    class Boom:
        def answer(self, *_):
            raise LLMError("down")

    with pytest.raises(LLMError):
        svc(store, retriever, Boom()).respond("socotra", "What is the tallest mountain?")


def test_malformed_output_is_an_error(store, retriever):
    with pytest.raises(LLMError):
        svc(store, retriever, ScriptedLLM({"answered": True, "sentences": "nope", "missing": ""})).respond(
            "socotra", "What is the tallest mountain?"
        )


def test_followup_uses_previous_question_for_retrieval(store, retriever):
    llm = ScriptedLLM(reply(fact("Portuguese forces took the port of Suq in 1507.", "SOC-017")))
    history = [("User", "Who ruled the island in the 1500s?"), ("Agent", "Portuguese forces took Suq.")]
    r = svc(store, retriever, llm).respond("socotra", "Tell me more", history=history)
    assert "SOC-017" in [e.id for e in r.retrieved]
    assert "<earlier_conversation>" in llm.calls[0][1]


def test_creature_selection_changes_persona_and_scope(store, retriever):
    llm = ScriptedLLM(reply(fact("I eat mainly sardines.", "GAL-105")))
    r = svc(store, retriever, llm).respond("galapagos", "What do you eat?", "galapagos-sea-lion")
    assert "Galápagos sea lion" in llm.calls[0][0] and r.creature == "galapagos-sea-lion"


def test_climate_answer_can_cite_nasa_power_numbers(store, retriever):
    r0 = retriever.search("socotra", "How hot is it?")
    power = next(e for e in r0.evidence if e.id == "POWER-SOC-TEMP")
    # build the claim from the evidence text itself so the test tracks the snapshot
    val = power.text.split("(T2M, C): ")[1].split("ANN ")[1].split(",")[0].rstrip(".")
    llm = ScriptedLLM(reply(fact(f"NASA POWER puts my annual mean air temperature at {val} C.", "POWER-SOC-TEMP")))
    r = svc(store, retriever, llm).respond("socotra", "How hot is it?")
    assert r.answered and not r.rejected, r.rejected

    # and a number that is not in the table is rejected, then dropped after the failed repair
    wrong = reply(fact("NASA POWER puts my annual mean air temperature at 99.9 C.", "POWER-SOC-TEMP"))
    r2 = svc(store, retriever, ScriptedLLM(wrong, wrong)).respond("socotra", "How hot is it?")
    assert not r2.answered and "99.9" in r2.rejected[0]["issues"][0]


def test_anthropic_client_never_sends_sampling_params_and_maps_billing_errors():
    from app.chat.llm import AnthropicAnswerLLM, LLMError

    class FakeClient:
        class messages:  # noqa: N801
            seen: dict = {}

            @classmethod
            def create(cls, **kw):  # a strict signature like the real SDK's for newer models
                cls.seen = kw
                raise FakeAnthropic.BadRequestError("Your credit balance is too low to access the Anthropic API")

    class FakeAnthropic:
        class APIError(Exception):
            pass

        class BadRequestError(APIError):
            pass

    llm = AnthropicAnswerLLM.__new__(AnthropicAnswerLLM)
    llm._anthropic, llm.client, llm.model, llm.max_tokens = FakeAnthropic, FakeClient, "m", 10
    try:
        llm.answer("s", "u")
    except LLMError as exc:
        assert "no credit" in str(exc)
    else:
        raise AssertionError("expected LLMError")
    assert "temperature" not in FakeClient.messages.seen
