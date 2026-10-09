"""Refresh the committed NASA POWER and GBIF snapshots in data/snapshots/.

Usage: python scripts/snapshot_sources.py [island-slug ...]
Both APIs are public and need no key.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402
from app.data.sources import SourceStore  # noqa: E402


def main(argv: list[str]) -> int:
    settings = get_settings()
    islands = IslandStore.load(settings.islands_dir)
    store = SourceStore(settings, islands)
    slugs = argv or list(islands.islands)
    failures = 0
    with httpx.Client(timeout=90) as client:
        for slug in slugs:
            island = islands.get(slug)
            for kind in ("power", "gbif"):
                try:
                    doc = store.refresh_snapshot(kind, island, client)
                    detail = (
                        doc["raw"]["header"].get("range", "")[:60]
                        if kind == "power"
                        else ", ".join(
                            f"{k}: {v['global_count']} global / {v['local_count']} local, usable {(v.get('local_breakdown') or {}).get('usable')}"
                            for k, v in doc["creatures"].items()
                        )
                    )
                    print(f"ok   {slug:<18} {kind:<5} {detail}")
                except Exception as exc:  # noqa: BLE001 - report and continue
                    failures += 1
                    print(f"FAIL {slug:<18} {kind:<5} {exc}")
                time.sleep(0.5)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
