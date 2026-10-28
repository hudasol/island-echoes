from __future__ import annotations

import pytest

from app.chat.service import NO_EVIDENCE_LINE
from app.data.sources import SourceStore
from eval import baselines
from eval.retrieval_eval import baseline_ranking, paired_hit5, score_question

from .fakes import ScriptedLLM, fact, reply, voice

QUESTION = "What is the tallest mountain?"


# ---- retrieval floors ------------------------------------------------------------------------------------
def test_candidates_are_the_pool_the_real_retriever_ranks(retriever):
    pool = baselines.candidates(retriever, "socotra", None)
    ids = {e.id for e in pool}
    assert "SOC-011" in ids
    assert all(e.subject in ("island", "socotra-buzzard") for e in pool)


def test_file_order_keeps_the_order_of_the_file(retriever):
    pool = baselines.candidates(retriever, "socotra", None)
    assert [e.id for e in baselines.rank_file_order(pool)] == [e.id for e in pool]


def test_random_is_reproducible_for_a_seed_and_differs_between_seeds(retriever):
    pool = baselines.candidates(retriever, "socotra", None)
    a1, a2, b = (baselines.rank_random(pool, s) for s in (1, 1, 2))
    assert [e.id for e in a1] == [e.id for e in a2]
    assert [e.id for e in a1] != [e.id for e in b]
    assert sorted(e.id for e in a1) == sorted(e.id for e in pool)


def test_overlap_ranks_shared_plain_words_and_drops_facts_with_none(retriever):
    pool = baselines.candidates(retriever, "socotra", None)
    ranked = baselines.rank_overlap(pool, "Where is the highest point?")
    assert ranked and "highest point" in ranked[0].text.lower()
    assert len(ranked) < len(pool)
    assert baselines.rank_overlap(pool, "zzz qqq") == []


def test_overlap_does_not_stem(retriever):
    pool = baselines.candidates(retriever, "socotra", None)
    top_plural = baselines.rank_overlap(pool, "mountains")
    top_singular = baselines.rank_overlap(pool, "mountain")
    assert [e.id for e in top_plural] != [e.id for e in top_singular]


def test_random_baseline_scores_are_an_expectation_between_zero_and_one(retriever):
    q = {"island": "socotra", "creature": None, "question": QUESTION}
    sc, ids = baseline_ranking("random", retriever, q, {"SOC-011"})
    assert 0 < sc["hit@12"] < 1 and 0 < sc["mrr"] < 1 and ids


def test_a_floor_scores_the_same_way_as_a_retriever(retriever):
    q = {"island": "socotra", "creature": None, "question": QUESTION}
    sc, ids = baseline_ranking("overlap", retriever, q, {"SOC-011"})
    assert sc == score_question(ids, {"SOC-011"})


def test_paired_hit5_counts_the_questions_only_one_mode_got_right():
    by_mode = {
        "a": {"questions": [{"id": "1", "hit@5": 1.0}, {"id": "2", "hit@5": 1.0}, {"id": "3", "hit@5": 0.0}]},
        "b": {"questions": [{"id": "1", "hit@5": 1.0}, {"id": "2", "hit@5": 0.0}, {"id": "3", "hit@5": 0.0}]},
    }
    out = paired_hit5(by_mode, "a", "b")
    assert (out["only_a"], out["only_b"]) == (1, 0) and out["p"] == 1.0
    assert paired_hit5(by_mode, "a", "missing") is None


# ---- end to end systems ----------------------------------------------------------------------------------
def test_refuse_all_never_answers_and_never_calls_a_model(store, retriever):
    r = baselines.make_service("refuse-all", store, retriever, None).respond("socotra", QUESTION)
    assert not r.answered and r.sentences[0].text == NO_EVIDENCE_LINE and not r.llm_called and r.cited_ids == []


def test_closed_book_sends_no_evidence_and_keeps_no_citations(store, retriever):
    llm = ScriptedLLM(reply(fact("The tallest peak is about 1,500 m high.", "SOC-011"), voice("Let me think.")))
    r = baselines.make_service("closed-book", store, retriever, llm).respond("socotra", QUESTION)
    system, user = llm.calls[0]
    assert "<evidence>" not in user and "SOC-011" not in user and "no documents" in system
    assert r.answered and r.retrieved == [] and r.cited_ids == [] and all(s.cites == [] for s in r.sentences)
    assert r.retrieval_mode == "none"


def test_closed_book_can_decline(store, retriever):
    llm = ScriptedLLM(reply(voice("I do not know."), answered=False, missing="No knowledge of that."))
    r = baselines.make_service("closed-book", store, retriever, llm).respond("socotra", QUESTION)
    assert not r.answered and r.missing == "No knowledge of that."


def test_unvalidated_shows_a_bad_citation_but_records_what_a_validator_would_catch(store, retriever):
    wrong = fact("The highest point is Mashanig at 1,900 m.", "SOC-011")
    llm = ScriptedLLM(reply(wrong))
    r = baselines.make_service("unvalidated", store, retriever, llm).respond("socotra", QUESTION)
    assert len(llm.calls) == 1  # no repair
    assert r.answered and [s.text for s in r.sentences] == [wrong["text"]]
    assert not r.rejected and not r.repaired
    assert r.raw_issues and "1900" in r.raw_issues[0]["issues"][0]


def test_unvalidated_refuses_when_nothing_is_retrieved(store, retriever):
    llm = ScriptedLLM()
    r = baselines.make_service("unvalidated", store, retriever, llm).respond("socotra", "zzzz qqqq xxxx")
    assert not r.answered and not llm.calls


def test_full_is_the_production_service(store, retriever):
    from app.chat.service import ChatService

    assert isinstance(baselines.make_service("full", store, retriever, ScriptedLLM()), ChatService)
    with pytest.raises(ValueError):
        baselines.make_service("nope", store, retriever, None)


# ---- claims outside the sources --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def pools(store, real_settings):
    return baselines.build_pools(store, SourceStore(real_settings, store, http=object()))


def test_a_number_from_the_sources_is_not_flagged(pools):
    assert baselines.claims_outside_sources("The highest point is about 1,503 m.", QUESTION, pools["socotra"]) == []


def test_a_number_found_nowhere_in_the_sources_is_flagged(pools):
    out = baselines.claims_outside_sources("The highest point is about 1,987 m.", QUESTION, pools["socotra"])
    assert out == ["number 1987"]


def test_a_number_copied_from_the_question_is_not_flagged(pools):
    assert baselines.claims_outside_sources("You asked about 4242 m.", "Is it 4242 m tall?", pools["socotra"]) == []


def test_a_name_found_nowhere_is_flagged_and_island_names_are_allowed(pools):
    out = baselines.claims_outside_sources("It was named by Zorblax the Navigator.", QUESTION, pools["socotra"])
    assert any("Zorblax" in x for x in out)
    assert baselines.claims_outside_sources("It lives on Socotra.", QUESTION, pools["socotra"]) == []


def test_summary_counts_sentences_and_answers_over_answered_records_only(pools):
    run = {"records": [
        {"id": "A", "answered": True, "sentences": [
            {"text": "The peak is 1,987 m.", "kind": "fact", "cites": []},
            {"text": "The peak is 1,503 m.", "kind": "fact", "cites": []},
            {"text": "Hello.", "kind": "voice", "cites": []},
        ]},
        {"id": "B", "answered": False, "sentences": [{"text": "No.", "kind": "voice", "cites": []}]},
        {"id": "C", "error": "timeout"},
    ]}
    qs = {i: {"question": QUESTION, "island": "socotra"} for i in "ABC"}
    out = baselines.outside_sources_summary(run, qs, pools)
    assert out == {"sentences": {"k": 1, "n": 2}, "answers": {"k": 1, "n": 1}}
