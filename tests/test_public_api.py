from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.ratelimit import RateLimiter
from scripts import export_openapi

WEB = Path(__file__).resolve().parents[1] / "web"


@pytest.fixture()
def client(tmp_settings):
    tmp_settings.web_dir = WEB
    return TestClient(create_app(tmp_settings))


def test_v1_and_legacy_paths_return_the_same_data(client):
    assert client.get("/api/v1/islands").json() == client.get("/api/islands").json()
    assert client.get("/api/v1/health").json()["status"] == "ok"
    a = client.get("/api/v1/library/search", params={"island": "socotra", "q": "highest point"}).json()
    b = client.get("/api/library/search", params={"island": "socotra", "q": "highest point"}).json()
    assert a == b and a["results"]


def test_openapi_documents_version_one_only(client):
    spec = client.get("/api/v1/openapi.json").json()
    assert spec["paths"] and all(p.startswith("/api/v1/") for p in spec["paths"])


def test_committed_openapi_file_is_current():
    committed = (Path(__file__).resolve().parents[1] / "docs" / "openapi.json")
    assert committed.exists() and committed.read_text(encoding="utf-8") == export_openapi.current()


def test_any_site_may_read_but_not_post(client):
    r = client.options("/api/v1/islands", headers={"Origin": "https://example.org", "Access-Control-Request-Method": "GET"})
    assert r.headers["access-control-allow-origin"] == "*"
    r = client.options("/api/v1/chat", headers={"Origin": "https://example.org", "Access-Control-Request-Method": "POST"})
    assert r.status_code == 400  # preflight for POST is refused


def test_rate_limit_tells_the_caller_when_to_retry():
    lim = RateLimiter(2, 100)
    lim.check("a")
    lim.check("a")
    with pytest.raises(Exception) as exc:
        lim.check("a")
    assert exc.value.status_code == 429 and 1 <= int(exc.value.headers["Retry-After"]) <= 61


def test_embed_assets_are_served_and_safe(client):
    js = client.get("/embed.js")
    assert js.status_code == 200 and "attachShadow" in js.text and "innerHTML =" in js.text
    assert "e.text" in js.text and "insertAdjacentHTML" not in js.text  # results are written as text, not markup
    assert "Ask an island" in client.get("/embed-demo.html").text
    json.loads(client.get("/api/v1/openapi.json").text)
