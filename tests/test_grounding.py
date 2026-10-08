from __future__ import annotations

from app.chat import grounding as g
from app.data.models import Evidence


def ev(id_, text):
    return Evidence(id=id_, kind="fact", island="x", category="terrain", title="t", text=text,
                    source_url="https://e.org", source_title="t", publisher="Pub", as_of="2026-10-08")


EVIDENCE = {
    "A-001": ev("A-001", "The Socotra buzzard has about 250-500 mature individuals and breeds on Hajhir cliffs."),
    "A-002": ev("A-002", "GBIF holds 8,306 occurrence records, 8,169 near Isabela, according to Wikipedia."),
}
NAMES = g.allowed_names("Socotra", [], ["Socotra buzzard", "Buteo socotraensis"])


def run(sentences, question="How many are there?"):
    return g.check_sentences(sentences, EVIDENCE, question, NAMES)


def test_numbers_normalise_commas_and_ranges():
    assert g.numbers("8,306 records and 250-500 birds, 4.5 km2 in 1507.") == {"8306", "250", "500", "4.5", "1507"}
    assert g.numbers("8,306 and 250-500") == {"8306", "250", "500"}
    assert g.numbers("km2 CO2") == set()  # digits glued to letters are unit/formula suffixes


def test_valid_sentence_passes():
    [s] = run([{"text": "I am told about 250-500 mature individuals remain.", "kind": "fact", "cites": ["A-001"]}])
    assert s.ok, s.issues


def test_thousands_separator_variants_match():
    [s] = run([{"text": "GBIF holds 8306 records, according to Wikipedia.", "kind": "fact", "cites": ["A-002"]}])
    assert s.ok, s.issues


def test_fact_without_citation_fails():
    [s] = run([{"text": "My kind is rare.", "kind": "fact", "cites": []}])
    assert "no citation" in s.issues[0]


def test_unretrieved_citation_fails():
    [s] = run([{"text": "My kind is rare.", "kind": "fact", "cites": ["Z-999"]}])
    assert "not retrieved" in s.issues[0]


def test_invented_number_fails():
    [s] = run([{"text": "About 900 mature individuals remain.", "kind": "fact", "cites": ["A-001"]}])
    assert any("numbers not in cited evidence: 900" in i for i in s.issues)


def test_number_from_other_evidence_is_not_borrowed():
    [s] = run([{"text": "About 8306 mature individuals remain.", "kind": "fact", "cites": ["A-001"]}])
    assert not s.ok  # 8306 is in A-002, not in the cited A-001


def test_invented_name_fails_but_echoed_question_name_passes():
    [bad] = run([{"text": "I nest near Hadibu.", "kind": "fact", "cites": ["A-001"]}])
    assert any("Hadibu" in i for i in bad.issues)
    [ok] = run([{"text": "I nest near Hadibu.", "kind": "fact", "cites": ["A-001"]}], question="Do you nest near Hadibu?")
    assert not any("Hadibu" in i for i in ok.issues)


def test_sentence_initial_capital_is_not_treated_as_a_name():
    [s] = run([{"text": "Cliffs hold my nests, about 250-500 of us.", "kind": "fact", "cites": ["A-001"]}])
    assert s.ok, s.issues


def test_voice_rules():
    ok, digits, long_, named, cited = run([
        {"text": "Let me check my instruments.", "kind": "voice", "cites": []},
        {"text": "I have 3 readings.", "kind": "voice", "cites": []},
        {"text": " ".join(["word"] * 20), "kind": "voice", "cites": []},
        {"text": "Greetings from Narnia.", "kind": "voice", "cites": []},
        {"text": "Hello there.", "kind": "voice", "cites": ["A-001"]},
    ])
    assert ok.ok
    assert not digits.ok and not long_.ok and not named.ok and not cited.ok


def test_empty_and_unknown_kind():
    [e] = run([{"text": "  ", "kind": "fact", "cites": ["A-001"]}])
    assert not e.ok
    [u] = run([{"text": "Cliffs hold my nests.", "kind": "weird", "cites": ["A-001"]}])
    assert u.kind == "fact" and u.ok
