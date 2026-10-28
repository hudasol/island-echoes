"""Facts about the data set itself: what each island holds and how old the external data is.

Computed from the fact files and the committed snapshots, so the numbers on the start view and the
operations page are the same ones the validator and the retriever work from.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from .config import Settings
from .data.islands import IslandStore
from .data.models import Island


def _snapshot(settings: Settings, kind: str, slug: str) -> dict:
    path = Path(settings.snapshots_dir) / kind / f"{slug}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def island_row(settings: Settings, isl: Island) -> dict:
    power, gbif = _snapshot(settings, "power", isl.slug), _snapshot(settings, "gbif", isl.slug)
    creatures = []
    for c in isl.creatures:
        entry = (gbif.get("creatures") or {}).get(c.slug, {})
        iucn = entry.get("iucn") or {}
        creatures.append({
            "slug": c.slug,
            "name": c.common_name,
            "scientific_name": c.scientific_name,
            "type": c.creature_type,
            "status_code": iucn.get("code"),
            "status": (iucn.get("category") or "").replace("_", " ").title() or None,
            "gbif_records": entry.get("local_count"),
        })
    hosts = Counter(_host(f.source_url) for f in isl.facts)
    return {
        "slug": isl.slug,
        "name": isl.name,
        "territory": isl.territory,
        "lat": isl.pin.lat,
        "lon": isl.pin.lon,
        "facts": len(isl.facts),
        "categories": dict(sorted(Counter(f.category for f in isl.facts).items())),
        "confidence": {k: Counter(f.confidence for f in isl.facts).get(k, 0) for k in ("high", "medium", "low")},
        "sources": len(hosts),
        "top_sources": [{"host": h, "facts": n} for h, n in hosts.most_common(3)],
        "creatures": creatures,
        "power_as_of": (power.get("fetched_at") or "")[:10] or None,
        "gbif_as_of": (gbif.get("fetched_at") or "")[:10] or None,
    }


def build_overview(settings: Settings, islands: IslandStore) -> dict:
    rows = [island_row(settings, i) for i in islands.islands.values()]
    all_facts = [f for i in islands.islands.values() for f in i.facts]
    hosts = Counter(_host(f.source_url) for f in all_facts)
    total = len(all_facts)
    return {
        "islands": rows,
        "totals": {
            "islands": len(rows),
            "creatures": sum(len(r["creatures"]) for r in rows),
            "facts": total,
            "distinct_sources": len(hosts),
            "wikipedia_share": round(hosts.get("en.wikipedia.org", 0) / total, 3) if total else 0.0,
            "confidence": {k: Counter(f.confidence for f in all_facts).get(k, 0) for k in ("high", "medium", "low")},
            "categories": dict(sorted(Counter(f.category for f in all_facts).items())),
        },
    }
