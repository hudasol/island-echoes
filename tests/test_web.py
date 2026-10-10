from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

WEB = Path(__file__).resolve().parents[1] / "web"


def _client(tmp_settings):
    tmp_settings.web_dir = WEB
    return TestClient(create_app(tmp_settings))


def test_shell_pages_are_served(tmp_settings):
    c = _client(tmp_settings)
    assert "Island Echoes" in c.get("/").text
    for p in ("/app.js", "/style.css", "/creatures.js", "/vendor/globe.gl.min.js", "/icons/icon-512.png"):
        assert c.get(p).status_code == 200, p


def test_service_worker_is_not_cached_and_has_root_scope(tmp_settings):
    r = _client(tmp_settings).get("/sw.js")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
    assert r.headers["service-worker-allowed"] == "/"


def test_manifest_is_installable():
    m = json.loads((WEB / "manifest.webmanifest").read_text())
    assert m["display"] == "standalone" and m["start_url"] == "/"
    assert {"192x192", "512x512"} <= {i["sizes"] for i in m["icons"]}
    assert all((WEB / i["src"]).exists() for i in m["icons"])


def test_service_worker_precache_list_exists_on_disk():
    sw = (WEB / "sw.js").read_text()
    paths = re.findall(r'"(/[^"]*)"', sw.split("ASSETS = [")[1].split("]")[0])
    assert len(paths) >= 5
    for p in paths:
        assert p == "/" or (WEB / p.lstrip("/")).exists(), p


def test_every_creature_type_has_an_animation_scene(store):
    js = (WEB / "creatures.js").read_text()
    for t in ("bird", "marine", "reptile", "mammal"):
        assert re.search(rf"^\s{{4}}{t}\(ctx", js, re.M), t
    used = {c.creature_type for i in store.islands.values() for c in i.creatures}
    assert used == {"bird", "marine", "reptile", "mammal"}


def test_frontend_uses_nasa_gibs_and_has_no_secrets():
    app = (WEB / "app.js").read_text()
    assert "gibs.earthdata.nasa.gov/wmts/epsg3857/best" in app
    assert "ANTHROPIC" not in app and "sk-ant" not in app


def test_nasa_credits_and_no_endorsement_are_in_the_shell():
    html = (WEB / "index.html").read_text()
    for needle in (
        "Global Imagery Browse Services (GIBS)",
        "NASA Langley Research Center (LaRC) POWER Project",
        "GBIF.org",
        "not a NASA product",
    ):
        assert needle.lower() in html.lower(), needle


def test_sensor_caveat_names_the_grid_cell_limit():
    assert "larger than the island" in (WEB / "index.html").read_text()


def test_accessibility_basics_present():
    html = (WEB / "index.html").read_text()
    assert 'class="skip"' in html and "<noscript>" in html and "<dialog" in html
    assert 'role="radiogroup"' not in html
    js = (WEB / "app.js").read_text()
    assert "ArrowRight" in js and "aria-pressed" in js
    css = (WEB / "style.css").read_text()
    assert "prefers-reduced-motion" in css and "forced-colors" in css


def test_library_cards_always_show_confidence():
    js = (WEB / "app.js").read_text()
    assert "conf-${e.confidence}" in js


def test_fact_cards_link_to_a_prefilled_issue():
    js = (WEB / "app.js").read_text()
    assert "github.com/hudasol/island-echoes/issues/new" in js and "Report a problem" in js


def test_stats_page_is_served_and_csp_safe(tmp_settings, store, retriever):
    from fastapi.testclient import TestClient

    from app.chat.service import ChatService
    from app.main import create_app

    c = TestClient(create_app(tmp_settings, ChatService(store, retriever, None)))
    page = c.get("/stats.html")
    assert page.status_code == 200 and "<script src=\"/stats.js\">" in page.text
    assert "onclick" not in page.text and "<script>" not in page.text  # CSP is script-src 'self'
    assert c.get("/stats.js").status_code == 200 and c.get("/stats.css").status_code == 200
    assert c.get("/api/stats").json()["events"] == 0


def test_chat_box_follows_the_server_not_a_query_flag():
    js = (WEB / "app.js").read_text()
    assert "has(\"claude\")" not in js and "h.chat_enabled" in js
