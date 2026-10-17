from __future__ import annotations

import pytest

from app.chat import grounding
from app.chat.tables import parse_rows, table_issues
from app.data.sources import SourceStore


@pytest.fixture(scope="module")
def power(store, real_settings):
    ss = SourceStore(real_settings, store, http=object())

    def get(island: str, ev_id: str):
        return next(e for e in ss.power_evidence(store.get(island)) if e.id == ev_id)

    return get


def test_rows_are_parsed_from_power_evidence(power):
    rows = parse_rows(power("cocos-keeling", "POWER-COC-TEMP").text)
    assert set(rows) == {"T2M", "T2M_MAX", "T2M_MIN"}
    assert rows["T2M_MAX"]["APR"] == 29.7 and len(rows["T2M"]) == 13


def test_a_value_from_the_neighbouring_month_is_caught(power):
    ev = power("cocos-keeling", "POWER-COC-WIND")
    s = "In September, the wind speed at 10 meters (WS10M) at Cocos Island Airport is 8.2 m/s."
    assert table_issues(s, ev.text) == ["8.2 is the AUG value in the cited table, not SEP"]
    assert table_issues("In September, the wind speed at 10 meters is 8.15 m/s.", ev.text) == []


def test_a_false_superlative_month_is_caught(power):
    ev = power("clipperton", "POWER-CLI-PRECIP")
    assert table_issues("March has the most rain in NASA's climate data, with 1.42 mm/day.", ev.text) == [
        "MAR is not the highest month in the cited table"
    ]
    assert table_issues("August is the wettest month, with 13.4 mm/day.", ev.text) == []
    assert table_issues("March is the driest month, with 1.42 mm/day.", ev.text) == []


def test_annual_values_and_parameters_are_bound(power):
    temp, rain = power("socotra", "POWER-SOC-TEMP"), power("socotra", "POWER-SOC-PRECIP")
    both = temp.text + "\n" + rain.text
    ok = "The annual average temperature at your location is 26.28°C, and the annual average daily rainfall is 0.36 mm."
    assert table_issues(ok, both) == []
    assert table_issues("The annual mean temperature is 29.22 C.", temp.text) == [
        "29.22 is the MAY value in the cited table, not ANN"
    ]


def test_verbatim_rows_and_unlabelled_numbers_pass(power):
    ev = power("cocos-keeling", "POWER-COC-WIND")
    row = next(line for line in ev.text.splitlines() if line.startswith("Wind Speed"))
    assert table_issues(row, ev.text) == []
    assert table_issues("The relative humidity is 88.43%.", power("bouvet", "POWER-BOU-HUMID").text) == []
    bou = power("bouvet", "POWER-BOU-WIND")
    assert table_issues("The wind speed at 10 meters is 10.41 m/s (ANN) according to NASA POWER.", bou.text) == []


def test_prose_evidence_is_left_to_the_main_checks():
    assert table_issues("In April about 243 mm falls.", "Rainfall peaks in April at about 243 mm.") == []


def test_validator_applies_the_check_only_when_enabled(power):
    ev = power("cocos-keeling", "POWER-COC-WIND")
    sent = [{"text": "In September the wind speed is 8.2 m/s.", "kind": "fact", "cites": [ev.id]}]
    on = grounding.check_sentences(sent, {ev.id: ev}, "How windy is it in September?", set())
    off = grounding.check_sentences(sent, {ev.id: ev}, "How windy is it in September?", set(), table_check=False)
    assert on[0].issues and not off[0].issues
