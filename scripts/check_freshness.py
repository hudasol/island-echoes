"""Fail when a committed data snapshot is older than the stated maximum age.

    python scripts/check_freshness.py            # default 120 days
    python scripts/check_freshness.py --max-days 90

The snapshots in data/snapshots/ hold NASA POWER climatology and GBIF counts. POWER climatology covers a
fixed 2001 to 2020 period and changes rarely; GBIF counts grow as records are added. The age limit is a
reminder to refresh, not a claim that older data is wrong. Refresh steps are in docs/OPERATIONS.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ages(now: datetime | None = None) -> list[tuple[int, Path]]:
    now = now or datetime.now(UTC)
    out = []
    for f in sorted((ROOT / "data" / "snapshots").glob("*/*.json")):
        stamp = datetime.fromisoformat(json.loads(f.read_text(encoding="utf-8"))["fetched_at"])
        out.append(((now - stamp).days, f.relative_to(ROOT)))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-days", type=int, default=120)
    args = ap.parse_args(argv)
    rows = ages()
    stale = [(d, p) for d, p in rows if d > args.max_days]
    oldest = max(rows)[0] if rows else 0
    print(f"{len(rows)} snapshots, oldest {oldest} days, limit {args.max_days} days")
    for d, p in stale:
        print(f"STALE {p}: {d} days old")
    return 1 if stale or not rows else 0


if __name__ == "__main__":
    sys.exit(main())
