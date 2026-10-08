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
