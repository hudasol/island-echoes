from __future__ import annotations

import httpx
import respx

from app.data import gbif, power

POWER_SAMPLE = {
    "geometry": {"type": "Point", "coordinates": [96.828, -12.187, 0.01]},
    "properties": {
        "parameter": {
            "T2M": {**{m: 27.0 for m in power.MONTHS}, "ANN": 26.92},
            "T2M_MAX": {**{m: 28.0 for m in power.MONTHS}, "ANN": 29.7},
            "T2M_MIN": {**{m: -999.0 for m in power.MONTHS}, "ANN": 23.88},
            "PRECTOTCORR": {**{m: 3.5 for m in power.MONTHS}, "ANN": 3.43},
            "RH2M": {**{m: 79.0 for m in power.MONTHS}, "ANN": 79.33},
            "WS10M": {**{m: 6.0 for m in power.MONTHS}, "ANN": 6.9},
        }
    },
    "header": {"range": "20-year climatology (January 2001 - December 2020)"},
    "parameters": {
        "T2M": {"units": "C", "longname": "Temperature at 2 Meters"},
        "T2M_MAX": {"units": "C", "longname": "Temperature at 2 Meters Maximum"},
        "T2M_MIN": {"units": "C", "longname": "Temperature at 2 Meters Minimum"},
        "PRECTOTCORR": {"units": "mm/day", "longname": "Precipitation Corrected"},
        "RH2M": {"units": "%", "longname": "Relative Humidity at 2 Meters"},
        "WS10M": {"units": "m/s", "longname": "Wind Speed at 10 Meters"},
    },
}


@respx.mock
def test_power_request_and_shape():
    route = respx.get(power.POWER_URL).mock(return_value=httpx.Response(200, json=POWER_SAMPLE))
    data = power.fetch_climatology(-12.1869, 96.8283)
    assert data["properties"]["parameter"]["T2M"]["ANN"] == 26.92
    q = route.calls[0].request.url.params
    assert q["community"] == "RE" and q["latitude"] == "-12.1869" and q["longitude"] == "96.8283"
    assert "PRECTOTCORR" in q["parameters"]


@respx.mock
def test_power_rejects_unexpected_shape():
    respx.get(power.POWER_URL).mock(return_value=httpx.Response(200, json={"nope": 1}))
    try:
        power.fetch_climatology(0, 0)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_power_text_marks_fill_values_and_units():
    text = power.topic_text(POWER_SAMPLE, "TEMP", -12.1869, 96.8283)
    assert "ANN 26.92" in text and "(T2M, C)" in text
    assert "JAN n/a" in text  # -999 fill value is not printed as a temperature
    assert "-999" not in text
    assert "January 2001 - December 2020" in text


def test_power_text_precip_uses_mm_per_day():
    text = power.topic_text(POWER_SAMPLE, "PRECIP", -12.1869, 96.8283)
    assert "mm/day" in text and "ANN 3.43" in text


@respx.mock
def test_gbif_fetch_counts_global_and_local():
    respx.get(f"{gbif.GBIF}/species/match").mock(
        return_value=httpx.Response(
            200,
            json={"usageKey": 2383313, "canonicalName": "Cheilinus undulatus", "rank": "SPECIES",
                  "status": "ACCEPTED", "matchType": "EXACT", "confidence": 99, "kingdom": "Animalia",
                  "family": "Labridae", "genus": "Cheilinus"},
        )
    )
    occ = respx.get(f"{gbif.GBIF}/occurrence/search").mock(
        side_effect=[httpx.Response(200, json={"count": 5480}), httpx.Response(200, json={"count": 23})]
    )
    d = gbif.fetch_creature("Cheilinus undulatus", -12.1869, 96.8283, 1.0)
    assert d["global_count"] == 5480 and d["local_count"] == 23
    assert occ.calls[1].request.url.params["geometry"].startswith("POLYGON((95.8283 -13.1869")
    assert d["box"]["half_width_deg"] == 1.0


@respx.mock
def test_gbif_no_match_has_no_counts():
    respx.get(f"{gbif.GBIF}/species/match").mock(
        return_value=httpx.Response(200, json={"matchType": "NONE", "confidence": 100})
    )
    d = gbif.fetch_creature("Nonexistus animalus", 0, 0, 1.0)
    assert d["global_count"] is None
    assert "no match" in gbif.species_text("thing", d)
    assert "unavailable" in gbif.occurrence_text("thing", "Nowhere", d)


def test_gbif_text_states_box_and_caveat():
    d = {
        "match": {"usageKey": 1, "canonicalName": "X y", "rank": "SPECIES", "status": "ACCEPTED",
                  "matchType": "EXACT", "confidence": 99, "kingdom": "Animalia"},
        "global_count": 1234, "local_count": 5,
        "box": gbif.box_bounds(10.0, 20.0, 2.0),
    }
    text = gbif.occurrence_text("thing", "Isle", d)
    assert "1,234" in text and "5 records" in text and "±2.0°" in text and "not true abundance" in text
