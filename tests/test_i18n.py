"""The Arabic interface: strings only, complete, and free of banned punctuation."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def _tables() -> dict[str, dict[str, str]]:
    js = (WEB / "i18n.js").read_text(encoding="utf-8")
    script = (
        "global.window={};global.document={addEventListener(){},documentElement:{},"
        "querySelectorAll(){return[]},getElementById(){return null}};global.localStorage={getItem(){return null}};"
        f"eval({json.dumps(js)});console.log(JSON.stringify(window.I18N.tables));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_arabic_has_every_english_key() -> None:
    t = _tables()
    assert set(t["en"]) == set(t["ar"])
    assert all(v.strip() for v in t["ar"].values())


def test_html_and_script_keys_exist() -> None:
    t = _tables()["en"]
    html = (WEB / "index.html").read_text(encoding="utf-8")
    keys = set(re.findall(r'data-i18n(?:-aria|-ph)?="([a-z_]+)"', html))
    keys |= set(re.findall(r'\bT\("([a-z_]+)"', (WEB / "app.js").read_text(encoding="utf-8")))
    assert keys and keys <= set(t), sorted(keys - set(t))


def test_no_banned_punctuation() -> None:
    for name in ("en", "ar"):
        for k, v in _tables()[name].items():
            assert "\u2014" not in v and "\u2013" not in v, (name, k)


def test_script_is_cached_for_offline_use() -> None:
    assert "/i18n.js" in (WEB / "sw.js").read_text(encoding="utf-8")
    assert '<script src="i18n.js">' in (WEB / "index.html").read_text(encoding="utf-8")
