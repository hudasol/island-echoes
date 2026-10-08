from __future__ import annotations

import httpx
import respx

from app.data import power
from app.data.islands import IslandStore
from app.data.sources import SourceStore

from .conftest import age_snapshot


def make(tmp_settings, store, http=None):
    return SourceStore(tmp_settings, store, http=http)


def test_fresh_snapshot_is_used_without_network(tmp_settings, store):
    ss = make(tmp_settings, store, http=object())  # any HTTP use would blow up
    ev = ss.power_evidence(store.get("socotra"))
    assert [e.id for e in ev] == ["POWER-SOC-TEMP", "POWER-SOC-PRECIP", "POWER-SOC-WIND", "POWER-SOC-HUMID"]
    assert all(e.publisher == "NASA POWER Project" and e.kind == "power" for e in ev)


def test_real_snapshots_cover_every_island_and_month(store, real_settings):
    ss = SourceStore(real_settings, store, http=object())
    for isl in store.islands.values():
        ev = {e.id: e for e in ss.power_evidence(isl)}
        temp = ev[f"POWER-{isl.prefix}-TEMP"].text
        for m in power.MONTHS + ["ANN"]:
            assert f"{m} " in temp
        assert "n/a" not in temp, isl.slug  # no missing months in any snapshot


def test_gbif_evidence_for_each_creature(store, real_settings):
    ss = SourceStore(real_settings, store, http=object())
    gal = store.get("galapagos")
    tort = ss.gbif_evidence(gal, "pinta-island-tortoise")
    lion = ss.gbif_evidence(gal, "galapagos-sea-lion")
    assert tort[0].id == "GBIF-GAL-pinta-island-tortoise-SPECIES"
    assert "Chelonoidis abingdonii" in tort[0].text
    assert lion[1].id == "GBIF-GAL-galapagos-sea-lion-OCC" and "Zalophus wollebaeki" not in lion[1].text
    assert "records" in lion[1].text


@respx.mock
def test_stale_snapshot_is_refreshed_live_and_cached(tmp_settings, store):
    age_snapshot(tmp_settings.snapshots_dir / "power" / "bouvet.json", days=90)
    sample = __import__("json").loads((tmp_settings.snapshots_dir / "power" / "bouvet.json").read_text())["raw"]
    route = respx.get(power.POWER_URL).mock(return_value=httpx.Response(200, json=sample))
    ss = make(tmp_settings, store)
    ss.power_evidence(store.get("bouvet"))
    assert route.call_count == 1
    assert (tmp_settings.cache_dir / "power" / "bouvet.json").exists()
    ss.power_evidence(store.get("bouvet"))  # now served from the fresh cache
    assert route.call_count == 1


@respx.mock
def test_stale_snapshot_used_when_network_fails_and_backs_off(tmp_settings, store):
    age_snapshot(tmp_settings.snapshots_dir / "power" / "pitcairn.json", days=90)
    route = respx.get(power.POWER_URL).mock(side_effect=httpx.ConnectError("offline"))
    ss = make(tmp_settings, store)
    first = ss.power_evidence(store.get("pitcairn"))
    second = ss.power_evidence(store.get("pitcairn"))
    assert first and second
    assert route.call_count == 1  # backoff stops hammering a dead network


def test_missing_data_and_no_network_raises(tmp_settings, store):
    import pytest

    from app.data.sources import SourceUnavailable

    (tmp_settings.snapshots_dir / "power" / "clipperton.json").unlink()
    with respx.mock:
        respx.get(power.POWER_URL).mock(side_effect=httpx.ConnectError("offline"))
        with pytest.raises(SourceUnavailable):
            make(tmp_settings, store).power_evidence(store.get("clipperton"))


def test_evidence_urls_are_reproducible(store, real_settings):
    ss = SourceStore(real_settings, store, http=object())
    e = ss.power_evidence(store.get("cocos-keeling"), ["TEMP"])[0]
    assert e.source_url.startswith(power.POWER_URL) and "latitude=-12.1869" in e.source_url
    assert IslandStore  # keep import used
