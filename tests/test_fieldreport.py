from __future__ import annotations

import re
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_report_page_is_cited_and_trackerless() -> None:
    r = client.get("/report/socotra/socotra-buzzard")
    assert r.status_code == 200
    body = r.text
    assert "<script" not in body and "analytics" not in body.lower()
    assert re.search(r"\[\d+\]", body) and "Retrieved" in body and "IUCN" in body
    assert "not a NASA product" in body
    assert "—" not in body


def test_card_is_valid_svg_with_date_and_code() -> None:
    r = client.get("/report/socotra/socotra-buzzard.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    root = ElementTree.fromstring(r.text)
    assert root.tag.endswith("svg")
    assert "Data as of" in r.text and "IUCN" in r.text


def test_unknown_creature_is_404() -> None:
    assert client.get("/report/socotra/nobody").status_code == 404
    assert client.get("/report/nowhere/x.svg").status_code == 404
