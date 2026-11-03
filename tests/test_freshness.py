from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from scripts import check_freshness as cf


def test_snapshots_have_ages() -> None:
    assert cf.ages()


def test_stale_snapshot_fails(monkeypatch, tmp_path) -> None:
    snaps = tmp_path / "data" / "snapshots" / "power"
    snaps.mkdir(parents=True)
    old = datetime.now(UTC) - timedelta(days=200)
    (snaps / "x.json").write_text(json.dumps({"fetched_at": old.isoformat()}), encoding="utf-8")
    monkeypatch.setattr(cf, "ROOT", tmp_path)
    assert cf.main(["--max-days", "120"]) == 1
    assert cf.main(["--max-days", "300"]) == 0
