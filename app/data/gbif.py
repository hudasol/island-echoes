"""GBIF client: backbone species match and occurrence counts. Public API, no key."""

from __future__ import annotations

import httpx

GBIF = "https://api.gbif.org/v1"


def _box_wkt(lat: float, lon: float, deg: float) -> str:
    x0, x1 = lon - deg, lon + deg
    y0, y1 = lat - deg, lat + deg
    return f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"


def box_bounds(lat: float, lon: float, deg: float) -> dict:
    return {
        "min_lat": round(lat - deg, 4),
        "max_lat": round(lat + deg, 4),
        "min_lon": round(lon - deg, 4),
        "max_lon": round(lon + deg, 4),
        "half_width_deg": deg,
    }


def fetch_creature(
    scientific_name: str,
    lat: float,
    lon: float,
    box_deg: float,
    *,
    client: httpx.Client | None = None,
) -> dict:
    """Match a name on the GBIF backbone and count occurrence records (global and in a box)."""
    own = client is None
    client = client or httpx.Client(timeout=60)
    try:
        m = client.get(f"{GBIF}/species/match", params={"name": scientific_name})
        m.raise_for_status()
        match = m.json()
        key = match.get("usageKey")
        out: dict = {"match": match, "global_count": None, "local_count": None}
        if key:
            g = client.get(f"{GBIF}/occurrence/search", params={"taxonKey": key, "limit": 0})
            g.raise_for_status()
            out["global_count"] = g.json().get("count")
            loc = client.get(
                f"{GBIF}/occurrence/search",
                params={"taxonKey": key, "geometry": _box_wkt(lat, lon, box_deg), "limit": 0},
            )
            loc.raise_for_status()
            out["local_count"] = loc.json().get("count")
        out["box"] = box_bounds(lat, lon, box_deg)
        return out
    finally:
        if own:
            client.close()


def species_text(creature_common: str, data: dict) -> str:
    m = data["match"]
    if not m.get("usageKey") or m.get("matchType") == "NONE":
        return f"GBIF backbone returned no match for the name used for the {creature_common}."
    lineage = ", ".join(
        f"{rank} {m[rank]}" for rank in ("kingdom", "phylum", "class", "order", "family", "genus") if m.get(rank)
    )
    return (
        f"GBIF backbone match for the {creature_common}: {m.get('canonicalName')} "
        f"(usageKey {m['usageKey']}, rank {m.get('rank')}, taxonomic status {m.get('status')}, "
        f"match type {m.get('matchType')}, confidence {m.get('confidence')}). Lineage: {lineage}."
    )


def occurrence_text(creature_common: str, island_name: str, data: dict) -> str:
    b = data["box"]
    g, loc = data.get("global_count"), data.get("local_count")
    if g is None:
        return f"GBIF occurrence counts are unavailable for the {creature_common}."
    return (
        f"GBIF holds {g:,} occurrence records worldwide for the {creature_common}, and {loc:,} records "
        f"inside a search box around {island_name} spanning latitude {b['min_lat']} to {b['max_lat']} and "
        f"longitude {b['min_lon']} to {b['max_lon']} (±{b['half_width_deg']}° around the pin). "
        f"Record counts reflect what has been published to GBIF, not true abundance."
    )
