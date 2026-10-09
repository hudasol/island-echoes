"""GBIF client: backbone species match and occurrence counts. Public API, no key."""

from __future__ import annotations

import time

import httpx

GBIF = "https://api.gbif.org/v1"

# record types GBIF reports (basisOfRecord), grouped for the evidence text
BASIS_GROUPS: dict[str, list[str]] = {
    "observations": ["HUMAN_OBSERVATION", "MACHINE_OBSERVATION", "OBSERVATION"],
    "specimens": ["PRESERVED_SPECIMEN", "FOSSIL_SPECIMEN", "MATERIAL_SAMPLE", "MATERIAL_CITATION"],
    "living_or_captive": ["LIVING_SPECIMEN"],
}


def _get(client: httpx.Client, url: str, params: dict, tries: int = 6) -> httpx.Response:
    """GET with backoff when GBIF answers 429 (it throttles bursts of count queries)."""
    for attempt in range(tries):
        r = client.get(url, params=params)
        if r.status_code != 429 or attempt == tries - 1:
            r.raise_for_status()
            return r
        time.sleep(min(float(r.headers.get("retry-after", 0) or 0) or 2 * (attempt + 1), 20))
    raise RuntimeError("unreachable")


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
        m = _get(client, f"{GBIF}/species/match", {"name": scientific_name})
        match = m.json()
        key = match.get("usageKey")
        out: dict = {"match": match, "global_count": None, "local_count": None, "local_breakdown": None}
        if key:
            g = _get(client, f"{GBIF}/occurrence/search", {"taxonKey": key, "limit": 0})
            out["global_count"] = g.json().get("count")
            loc = _get(
                client,
                f"{GBIF}/occurrence/search",
                {"taxonKey": key, "geometry": _box_wkt(lat, lon, box_deg), "limit": 0},
            )
            out["local_count"] = loc.json().get("count")
            # usable records only: georeferenced, no flagged coordinate problems, split by record type
            usable = {"taxonKey": key, "geometry": _box_wkt(lat, lon, box_deg), "hasCoordinate": "true",
                      "hasGeospatialIssue": "false", "limit": 0}
            breakdown = {}
            for label, kinds in BASIS_GROUPS.items():
                r = _get(client, f"{GBIF}/occurrence/search", {**usable, "basisOfRecord": kinds})
                breakdown[label] = r.json().get("count")
            u = _get(client, f"{GBIF}/occurrence/search", usable)
            breakdown["usable"] = u.json().get("count")
            out["local_breakdown"] = breakdown
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
    where = (
        f"a search box around {island_name} spanning latitude {b['min_lat']} to {b['max_lat']} and "
        f"longitude {b['min_lon']} to {b['max_lon']} (±{b['half_width_deg']}° around the pin)"
    )
    bd = data.get("local_breakdown")
    if not bd:
        return (
            f"GBIF holds {g:,} occurrence records worldwide for the {creature_common}, and {loc:,} records "
            f"inside {where}. These counts include every record type and coordinate quality. "
            f"Record counts reflect what has been published to GBIF, not true abundance."
        )
    other = max(bd["usable"] - bd["observations"] - bd["specimens"] - bd["living_or_captive"], 0)
    return (
        f"GBIF holds {g:,} occurrence records worldwide for the {creature_common}. Inside {where} it holds "
        f"{loc:,} records, of which {bd['usable']:,} have coordinates with no flagged problem: "
        f"{bd['observations']:,} observations, {bd['specimens']:,} preserved or fossil specimens, "
        f"{bd['living_or_captive']:,} living or captive animals and {other:,} of other or unstated type. "
        f"Record counts reflect what has been published to GBIF, not true abundance."
    )
