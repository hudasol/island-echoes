from __future__ import annotations

import json

from scripts import bench


def test_percentile_picks_the_nearest_rank():
    assert bench.percentile([5, 1, 3, 2, 4], 50) == 3
    assert bench.percentile([1.0], 95) == 1.0


def test_bench_runs_and_writes_its_numbers(tmp_path, capsys):
    out = tmp_path / "b.json"
    assert bench.main(["--rounds", "1", "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert [r["endpoint"] for r in data["results"]][-1] == "POST /api/chat (no model)"
    assert all(r["median_ms"] > 0 for r in data["results"])
    assert "median ms" in capsys.readouterr().out
