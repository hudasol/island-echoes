from __future__ import annotations

import pytest

from app.data.islands import IslandStore

SEVEN = {"cocos-keeling", "galapagos", "socotra", "tristan-da-cunha", "pitcairn", "clipperton", "bouvet"}


def test_seven_islands(store):
    assert set(store.islands) == SEVEN


def test_fact_ids_unique_and_prefixed(store):
    prefixes = set()
    for isl in store.islands.values():
        assert isl.prefix not in prefixes
        prefixes.add(isl.prefix)
        assert all(f.id.startswith(isl.prefix + "-") for f in isl.facts)
    assert len(store.all_facts()) == len({f.id for f in store.all_facts()})


def test_every_fact_has_a_real_source(store):
    for f in store.all_facts():
        assert f.source_url.startswith("https://") or f.source_url.startswith("http://")
        assert f.publisher and f.evidence_note and len(f.statement) > 20


def test_all_four_creature_types_present(store):
    types = {c.creature_type for isl in store.islands.values() for c in isl.creatures}
    assert types == {"bird", "marine", "reptile", "mammal"}


def test_each_creature_has_enough_facts(store):
    for isl in store.islands.values():
        for c in isl.creatures:
            assert sum(1 for f in isl.facts if f.subject == c.slug) >= 6, c.slug


def test_galapagos_has_two_creatures(store):
    g = store.get("galapagos")
    assert [c.slug for c in g.creatures] == ["pinta-island-tortoise", "galapagos-sea-lion"]
    assert g.creature("galapagos-sea-lion").creature_type == "mammal"
    with pytest.raises(KeyError):
        g.creature("nope")


def test_default_creature_is_first(store):
    assert store.get("bouvet").creature(None).slug == "macaroni-penguin"


def test_fact_to_evidence_keeps_citation_data(store):
    isl = store.get("socotra")
    ev = IslandStore.fact_to_evidence(isl, isl.facts[0])
    assert ev.id == isl.facts[0].id and ev.kind == "fact"
    assert ev.source_url == isl.facts[0].source_url and ev.text == isl.facts[0].statement


def test_unknown_island_raises(store):
    with pytest.raises(KeyError):
        store.get("atlantis")


def test_pins_are_plausible_for_each_hemisphere(store):
    assert store.get("socotra").pin.lat > 0
    assert store.get("clipperton").pin.lon < -100
    assert store.get("bouvet").pin.lat < -50
