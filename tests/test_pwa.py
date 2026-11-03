from __future__ import annotations

from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def test_worker_waits_for_the_person_before_taking_over():
    sw = (WEB / "sw.js").read_text(encoding="utf-8")
    install = sw.split('addEventListener("install"')[1].split("});")[0]
    code = "\n".join(line for line in install.splitlines() if not line.strip().startswith("//"))
    assert "skipWaiting" not in code
    assert 'type === "SKIP_WAITING"' in sw


def test_page_offers_the_update_and_reloads_once():
    js = (WEB / "app.js").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'id="update-banner"' in html and 'id="update-reload"' in html
    assert "SKIP_WAITING" in js and "controllerchange" in js and "reloaded" in js


def test_educator_pages_are_network_first_and_cached_for_offline_use():
    sw = (WEB / "sw.js").read_text(encoding="utf-8")
    assert '"/educator/"' in sw and "/educator.css" in sw
