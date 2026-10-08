from __future__ import annotations

import pytest

from app.data.retrieval import MIN_OVERLAP_SCORE, expand, tokenize

# (island, creature, question, a fact id that must be retrieved)
ANSWERABLE = [
    ("socotra", None, "How high is the tallest mountain?", "SOC-011"),
    ("bouvet", None, "How much of the island is covered by ice?", "BOU-012"),
    ("tristan-da-cunha", None, "Why were people evacuated?", "TDC-023"),
    ("galapagos", "pinta-island-tortoise", "Tell me about Lonesome George", "GAL-033"),
    ("galapagos", "galapagos-sea-lion", "What do you eat?", "GAL-105"),
]
NO_OVERLAP = [
    ("pitcairn", "How do I bake sourdough bread?"),
    ("cocos-keeling", "What is your favourite colour?"),
    ("tristan-da-cunha", "How much does a ticket cost?"),
]


@pytest.mark.parametrize("island,creature,q,fact_id", ANSWERABLE)
def test_answerable_questions_retrieve_the_right_fact(retriever, island, creature, q, fact_id):
    res = retriever.search(island, q, creature)
    assert fact_id in [e.id for e in res.evidence], [e.id for e in res.evidence]
    assert res.top_score >= MIN_OVERLAP_SCORE


@pytest.mark.parametrize("island,q", NO_OVERLAP)
def test_zero_overlap_questions_return_nothing(retriever, island, q):
    res = retriever.search(island, q)
    assert not res.has_evidence and res.evidence == []


def test_retrieval_is_scoped_to_the_island(retriever, store):
    res = retriever.search("socotra", "Tell me about the history of the island")
    assert res.evidence and all(e.island == "socotra" for e in res.evidence)


def test_other_creatures_facts_are_not_mixed_in(retriever):
    res = retriever.search("galapagos", "Tell me about your diet and threats", "galapagos-sea-lion")
    assert all(e.subject in ("island", "galapagos-sea-lion") for e in res.evidence)
    res2 = retriever.search("galapagos", "Tell me about your diet and threats", "pinta-island-tortoise")
    assert all(e.subject in ("island", "pinta-island-tortoise") for e in res2.evidence)


def test_decade_tokens_match_indexed_years(retriever):
    res = retriever.search("socotra", "Who ruled the island in the 1500s?")
    ids = [e.id for e in res.evidence]
    assert "SOC-017" in ids  # Portuguese period facts carry 1507 / 1511 style years


def test_climate_questions_pull_nasa_power(retriever):
    res = retriever.search("socotra", "How hot is it in July?")
    assert "climate" in res.intents and res.evidence[0].id == "POWER-SOC-TEMP"
    res = retriever.search("bouvet", "Is it windy and how much rain falls?")
    ids = {e.id for e in res.evidence}
    assert {"POWER-BOU-WIND", "POWER-BOU-PRECIP"} <= ids


def test_species_questions_pull_gbif_for_the_selected_creature(retriever):
    res = retriever.search("galapagos", "How many GBIF records exist?", "galapagos-sea-lion")
    ids = [e.id for e in res.evidence]
    assert "GBIF-GAL-galapagos-sea-lion-OCC" in ids
    assert not any("pinta" in i for i in ids)


def test_category_questions_pull_that_category(retriever, store):
    res = retriever.search("cocos-keeling", "What threatens you?")
    assert any(e.category == "threats" for e in res.evidence)


def test_accents_and_plurals_normalise():
    assert tokenize("Galápagos tortoises") == tokenize("Galapagos tortoise")
    assert "rainfal" not in expand("how much rain")  # no mangled stems
    assert "rainfall" in expand("how much rain")


def test_evidence_is_capped(retriever):
    res = retriever.search("galapagos", "Tell me everything about the climate history threats and species records")
    assert len(res.evidence) <= 24
