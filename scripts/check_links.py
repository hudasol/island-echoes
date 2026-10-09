"""Check that every source URL in the island fact files still resolves.

Usage: python scripts/check_links.py [--limit N]
Exit status 1 if any link is dead (HTTP 404 or 410). Sites that refuse automated requests, time out
or refuse the connection are reported as "blocked" and do not fail the run.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
UA = "island-echoes-link-check/1.0 (+https://github.com/hudasol/island-echoes)"


def urls() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for f in sorted((ROOT / "data" / "islands").glob("*.json")):
        for fact in json.loads(f.read_text(encoding="utf-8"))["facts"]:
            found.setdefault(fact["source_url"], []).append(fact["id"])
    return found


def check(url: str) -> tuple[str, str]:
    try:
        with httpx.Client(follow_redirects=True, timeout=25, headers={"User-Agent": UA}) as c:
            r = c.head(url)
            if r.status_code in (403, 405, 501):
                r = c.get(url)
    except httpx.HTTPError as exc:  # timeouts and refused connections are usually bot-blocking, not dead pages
        return "blocked", type(exc).__name__
    if r.status_code in (404, 410):
        return "dead", str(r.status_code)
    if r.status_code in (403, 429, 999) or r.status_code >= 500:
        return "blocked", str(r.status_code)
    return "ok", str(r.status_code)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    found = urls()
    items = list(found)[: args.limit or None]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(check, items))
    dead = [(u, d) for u, (s, d) in zip(items, results, strict=True) if s == "dead"]
    blocked = sum(1 for s, _ in results if s == "blocked")
    print(f"{len(items)} links checked: {sum(1 for s, _ in results if s == 'ok')} ok, {blocked} blocked or erroring, {len(dead)} dead")
    for u, d in dead:
        print(f"DEAD {d}: {u}  (facts: {', '.join(found[u])})")
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
