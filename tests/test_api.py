from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.chat.llm import LLMError
from app.chat.service import ChatService
from app.config import Settings
from app.main import create_app
from app.ratelimit import RateLimiter

from .fakes import ScriptedLLM, fact, reply


@pytest.fixture()
def settings(tmp_settings) -> Settings:
    return tmp_settings


def client_with(settings, store, retriever, llm, **cfg):
    for k, v in cfg.items():
        setattr(settings, k, v)
    app = create_app(settings, ChatService(store, retriever, llm))
    return TestClient(app)


def test_health_reports_chat_state(settings, store, retriever):
    off = client_with(settings, store, retriever, None).get("/api/health").json()
    on = client_with(settings, store, retriever, ScriptedLLM()).get("/api/health").json()
    assert off["chat_enabled"] is False and on["chat_enabled"] is True and on["islands"] == 7


def test_islands_listing_and_detail(settings, store, retriever):
    c = client_with(settings, store, retriever, None)
    items = c.get("/api/islands").json()
    assert len(items) == 7 and {i["slug"] for i in items} >= {"socotra", "bouvet"}
    gal = next(i for i in items if i["slug"] == "galapagos")
    assert [x["creature_type"] for x in gal["creatures"]] == ["reptile", "mammal"]
    detail = c.get("/api/islands/socotra").json()
    assert detail["fact_count"] == len(detail["facts"]) == 39
    assert detail["facts"][0]["source_url"].startswith("http")
    assert c.get("/api/islands/atlantis").status_code == 404


def test_narration_is_cited_and_per_creature(settings, store, retriever):
    c = client_with(settings, store, retriever, None)
    r = c.get("/api/islands/galapagos/narration", params={"creature": "galapagos-sea-lion"}).json()
    assert r["creature_type"] == "mammal" and r["sentences"][0]["kind"] == "voice"
    facts = [s for s in r["sentences"] if s["kind"] == "fact"]
    assert facts and all(s["cites"] for s in facts)
    assert {e["id"] for e in r["evidence"]} == {i for s in facts for i in s["cites"]}
    assert c.get("/api/islands/galapagos/narration", params={"creature": "x"}).status_code == 404
    for slug in store.islands:  # every creature of every island has a narration
        for cr in store.get(slug).creatures:
            assert c.get(f"/api/islands/{slug}/narration", params={"creature": cr.slug}).status_code == 200


def test_chat_returns_cited_answer_with_evidence_cards(settings, store, retriever):
    llm = ScriptedLLM(reply(fact("The highest point is Mashanig at about 1,503 m, according to Wikipedia.", "SOC-011")))
    c = client_with(settings, store, retriever, llm)
    body = c.post("/api/chat", json={"island": "socotra", "message": "What is the tallest mountain?"}).json()
    assert body["answered"] is True
    assert body["sentences"][0]["cites"] == ["SOC-011"]
    cited = [e for e in body["evidence"] if e["cited"]]
    assert [e["id"] for e in cited] == ["SOC-011"] and cited[0]["source_url"].startswith("http")
    assert body["evidence"][0]["id"] == "SOC-011"  # cited evidence listed first
    assert body["grounding"]["retrieved"] >= 1 and body["grounding"]["llm_called"] is True


def test_chat_without_key_is_503_but_no_overlap_still_answers(settings, store, retriever):
    c = client_with(settings, store, retriever, None)
    r = c.post("/api/chat", json={"island": "socotra", "message": "What is the tallest mountain?"})
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]
    ok = c.post("/api/chat", json={"island": "pitcairn", "message": "How do I bake sourdough bread?"})
    assert ok.status_code == 200 and ok.json()["answered"] is False


def test_chat_validation_and_unknowns(settings, store, retriever):
    c = client_with(settings, store, retriever, ScriptedLLM())
    assert c.post("/api/chat", json={"island": "atlantis", "message": "hi"}).status_code == 404
    assert c.post("/api/chat", json={"island": "socotra", "message": "hi", "creature": "zzz"}).status_code == 404
    assert c.post("/api/chat", json={"island": "socotra", "message": ""}).status_code == 422
    assert c.post("/api/chat", json={"island": "socotra", "message": "x" * 501}).status_code == 422


def test_llm_failure_is_502(settings, store, retriever):
    class Boom:
        def answer(self, *_):
            raise LLMError("down")

    c = client_with(settings, store, retriever, Boom())
    r = c.post("/api/chat", json={"island": "socotra", "message": "What is the tallest mountain?"})
    assert r.status_code == 502


def test_rate_limit_per_minute_and_daily_cap():
    t = [0.0]
    rl = RateLimiter(per_minute=2, daily_cap=3, clock=lambda: t[0], wall=lambda: 1_000_000.0)
    rl.check("a"); rl.check("a")
    with pytest.raises(Exception) as e:
        rl.check("a")
    assert e.value.status_code == 429
    t[0] = 61.0
    rl.check("a")  # window slid, but this was the third call of the day
    with pytest.raises(Exception) as e2:
        rl.check("b")
    assert e2.value.status_code == 429 and "daily" in e2.value.detail


def test_security_headers_present(settings, store, retriever):
    r = client_with(settings, store, retriever, None).get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"


def test_sensors_come_from_nasa_power_snapshot(settings, store, retriever):
    c = client_with(settings, store, retriever, None)
    body = c.get("/api/islands/socotra/sensors").json()
    assert body["island"] == "socotra" and "2001" in body["period"] and body["as_of"]
    by = {i["key"]: i for i in body["items"]}
    assert set(by) == {"temp", "rain", "wind", "humidity"}
    assert by["temp"]["unit"] == "°C" and by["temp"]["value"] == 26.28
    assert by["rain"]["unit"] == "mm/day" and by["rain"]["evidence_id"] == "POWER-SOC-PRECIP"
    assert all(len(i["monthly"]) == 12 for i in body["items"])
    assert c.get("/api/islands/atlantis/sensors").status_code == 404


def test_every_island_has_all_four_sensors(settings, store, retriever):
    c = client_with(settings, store, retriever, None)
    for slug in store.islands:
        items = c.get(f"/api/islands/{slug}/sensors").json()["items"]
        assert len(items) == 4 and all(i["value"] is not None for i in items), slug
