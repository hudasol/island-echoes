from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.educator import build_sheet, render_html
from app.main import create_app
from scripts import contrast

WEB = Path(__file__).resolve().parents[1] / "web"


def test_every_fact_has_a_numbered_source(store, retriever):
    for slug in store.islands:
        sheet = build_sheet(store.get(slug), store, retriever.sources)
        n_refs = len(sheet["references"])
        assert n_refs and sheet["sections"] and len(sheet["questions"]) >= 4
        for s in sheet["sections"]:
            for f in s["facts"]:
                assert 1 <= f["ref"] <= n_refs
                assert f["text"] == store.fact(f["id"]).statement  # quoted, never rewritten


def test_question_stems_only_name_numbered_facts(store, retriever):
    sheet = build_sheet(store.get("socotra"), store, retriever.sources)
    numbers = {f["n"] for s in sheet["sections"] for f in s["facts"]}
    for q in sheet["questions"]:
        for m in re.finditer(r"[Ff]acts? (\d+)(?: and (\d+))?", q):
            assert {int(g) for g in m.groups() if g} <= numbers


def test_html_escapes_text_and_links_sources(store, retriever):
    sheet = build_sheet(store.get("pitcairn"), store, retriever.sources)
    sheet["sections"][0]["facts"][0]["text"] = "<script>alert(1)</script>"
    page = render_html(sheet)
    assert "<script>alert" not in page and "&lt;script&gt;" in page
    assert 'id="ref1"' in page and "not a NASA product" in page


@pytest.fixture()
def client(tmp_settings):
    tmp_settings.web_dir = WEB
    return TestClient(create_app(tmp_settings))


def test_routes(client):
    r = client.get("/educator/bouvet")
    assert r.status_code == 200 and "Bouvet" in r.text and "Print or save as PDF" in r.text
    assert client.get("/api/islands/bouvet/educator").json()["island"] == "bouvet"
    assert client.get("/educator/nowhere").status_code == 404
    assert client.get("/educator/bouvet.pdf").status_code in (200, 404)
    assert client.get("/educator/..%2f..%2fetc%2fpasswd.pdf").status_code == 404


def test_pink_palette_meets_wcag_aa():
    assert contrast.check(WEB / "educator.css") == []
