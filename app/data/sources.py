"""Live/cached access to NASA POWER and GBIF, and conversion into citable evidence.

Resolution order for each island: fresh cache -> fresh committed snapshot -> live fetch (written to
cache) -> stale cache/snapshot if the network fails. Committed snapshots make the app and the eval
reproducible and let the server start with no outbound calls.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

from ..config import GBIF_BOX_DEG, Settings
from . import gbif as gbif_mod
from . import power as power_mod
from .islands import IslandStore
from .models import Evidence, Island

log = logging.getLogger("island_echoes.data")
RUNTIME_TIMEOUT = 10.0
BACKOFF_SECONDS = 600


class SourceUnavailable(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def comparable(kind: str, doc: dict) -> dict:
    """The numbers a reader would notice changing, flattened to {name: value}."""
    out: dict = {}
    if kind == "power":
        for param, series in doc.get("raw", {}).get("properties", {}).get("parameter", {}).items():
            out[f"{param}.ANN"] = series.get("ANN")
    else:
        for slug, c in doc.get("creatures", {}).items():
            out[f"{slug}.global_count"] = c.get("global_count")
            out[f"{slug}.local_count"] = c.get("local_count")
            for k, v in (c.get("local_breakdown") or {}).items():
                out[f"{slug}.local.{k}"] = v
    return out


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


class SourceStore:
    def __init__(self, settings: Settings, islands: IslandStore, http: httpx.Client | None = None):
        self.s = settings
        self.islands = islands
        self._http = http
        self._backoff: dict[tuple[str, str], float] = {}

    # ---- file plumbing -------------------------------------------------
    def _paths(self, kind: str, slug: str) -> tuple[Path, Path]:
        return (
            self.s.cache_dir / kind / f"{slug}.json",
            self.s.snapshots_dir / kind / f"{slug}.json",
        )

    def _fresh(self, doc: dict | None) -> bool:
        if not doc or "fetched_at" not in doc:
            return False
        try:
            t = datetime.fromisoformat(doc["fetched_at"])
        except ValueError:
            return False
        return _now() - t < timedelta(days=self.s.source_ttl_days)

    def _client(self) -> httpx.Client:
        return self._http or httpx.Client(timeout=RUNTIME_TIMEOUT)

    def _resolve(self, kind: str, island: Island, fetch) -> dict:
        cache_p, snap_p = self._paths(kind, island.slug)
        cache, snap = _read(cache_p), _read(snap_p)
        for doc in (cache, snap):
            if self._fresh(doc):
                return doc  # type: ignore[return-value]
        key = (kind, island.slug)
        if time.monotonic() >= self._backoff.get(key, 0):
            client = self._client()
            try:
                doc = fetch(island, client)
                _write(cache_p, doc)
                self._record_changes(kind, island, cache or snap, doc)
                return doc
            except (httpx.HTTPError, ValueError, KeyError):
                self._backoff[key] = time.monotonic() + BACKOFF_SECONDS
            finally:
                if self._http is None:
                    client.close()
        stale = cache or snap
        if stale:
            return stale
        raise SourceUnavailable(f"{kind} data for {island.slug} is unavailable")

    def _record_changes(self, kind: str, island: Island, old: dict | None, new: dict) -> None:
        """Note every value that moved when live data replaces older data, so evidence text never changes silently."""
        if not old:
            return
        before, after = comparable(kind, old), comparable(kind, new)
        diff = {k: [before.get(k), after.get(k)] for k in after if before.get(k) != after.get(k)}
        if not diff:
            return
        entry = {"at": _now().isoformat(timespec="seconds"), "kind": kind, "island": island.slug,
                 "previous_as_of": str(old.get("fetched_at", ""))[:10], "changes": diff}
        log.info("data change %s %s: %s", kind, island.slug, diff)
        try:
            path = self.s.cache_dir / "changes.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def recent_changes(self, limit: int = 50) -> list[dict]:
        try:
            lines = (self.s.cache_dir / "changes.jsonl").read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        return [json.loads(x) for x in lines[-limit:]][::-1]

    # ---- fetchers (also used by scripts/snapshot_sources.py) -----------
    def fetch_power_doc(self, island: Island, client: httpx.Client) -> dict:
        raw = power_mod.fetch_climatology(island.pin.lat, island.pin.lon, client=client)
        return {"fetched_at": _now().isoformat(timespec="seconds"), "raw": raw}

    def fetch_gbif_doc(self, island: Island, client: httpx.Client) -> dict:
        box = GBIF_BOX_DEG[island.slug]
        creatures = {
            c.slug: gbif_mod.fetch_creature(
                c.gbif_search_name, island.pin.lat, island.pin.lon, box, client=client
            )
            for c in island.creatures
        }
        return {"fetched_at": _now().isoformat(timespec="seconds"), "creatures": creatures}

    def refresh_snapshot(self, kind: str, island: Island, client: httpx.Client) -> dict:
        fetch = self.fetch_power_doc if kind == "power" else self.fetch_gbif_doc
        doc = fetch(island, client)
        _write(self._paths(kind, island.slug)[1], doc)
        return doc

    # ---- evidence builders --------------------------------------------
    def power_evidence(self, island: Island, topics: list[str] | None = None) -> list[Evidence]:
        doc = self._resolve("power", island, self.fetch_power_doc)
        raw = doc["raw"]
        url = (
            f"{power_mod.POWER_URL}?"
            + urlencode(
                {
                    "parameters": ",".join(power_mod.PARAMETERS),
                    "community": "RE",
                    "longitude": f"{island.pin.lon:.4f}",
                    "latitude": f"{island.pin.lat:.4f}",
                    "format": "JSON",
                },
                safe=",",
            )
        )
        out = []
        for topic in topics or list(power_mod.TOPICS):
            out.append(
                Evidence(
                    id=f"POWER-{island.prefix}-{topic}",
                    kind="power",
                    island=island.slug,
                    category="climate",
                    title=f"{island.name} · NASA POWER {topic.lower()} climatology",
                    text=power_mod.topic_text(raw, topic, island.pin.lat, island.pin.lon),
                    source_url=url,
                    source_title="NASA POWER climatology API",
                    publisher="NASA POWER Project",
                    as_of=doc["fetched_at"][:10],
                )
            )
        return out

    def power_summary(self, island: Island) -> dict:
        """Annual value and 12 monthly values per sensor, straight from the POWER climatology."""
        doc = self._resolve("power", island, self.fetch_power_doc)
        raw = doc["raw"]
        table, meta = raw["properties"]["parameter"], raw.get("parameters", {})
        spec = [
            ("temp", "Air temperature", "T2M", "TEMP"),
            ("rain", "Rainfall", "PRECTOTCORR", "PRECIP"),
            ("wind", "Wind speed", "WS10M", "WIND"),
            ("humidity", "Humidity", "RH2M", "HUMID"),
        ]

        def clean(v):
            return None if v is None or v == power_mod.FILL_VALUE else v

        items = []
        for key, label, param, topic in spec:
            series = table.get(param)
            if not series:
                continue
            unit = meta.get(param, {}).get("units", "")
            items.append(
                {
                    "key": key,
                    "label": label,
                    "unit": "°C" if unit == "C" else unit,
                    "value": clean(series.get("ANN")),
                    "monthly": [clean(series.get(m)) for m in power_mod.MONTHS],
                    "evidence_id": f"POWER-{island.prefix}-{topic}",
                }
            )
        cell = raw.get("geometry", {}).get("coordinates", [island.pin.lon, island.pin.lat])
        return {
            "island": island.slug,
            "as_of": doc["fetched_at"][:10],
            "period": raw.get("header", {}).get("range", ""),
            "cell_lat": cell[1],
            "cell_lon": cell[0],
            "items": items,
        }

    def gbif_evidence(self, island: Island, creature_slug: str | None) -> list[Evidence]:
        creature = island.creature(creature_slug)
        doc = self._resolve("gbif", island, self.fetch_gbif_doc)
        data = doc["creatures"].get(creature.slug)
        if not data:
            return []
        m = data["match"]
        match_url = f"{gbif_mod.GBIF}/species/match?name={quote(creature.gbif_search_name)}"
        occ_url = (
            f"{gbif_mod.GBIF}/occurrence/search?taxonKey={m.get('usageKey')}&limit=0"
            if m.get("usageKey")
            else match_url
        )
        base = f"GBIF-{island.prefix}-{creature.slug}"
        return [
            Evidence(
                id=f"{base}-SPECIES",
                kind="gbif",
                island=island.slug,
                subject=creature.slug,
                category="creature",
                title=f"GBIF taxonomy · {creature.common_name}",
                text=gbif_mod.species_text(creature.common_name, data),
                source_url=match_url,
                source_title="GBIF species match",
                publisher="GBIF",
                as_of=doc["fetched_at"][:10],
            ),
            Evidence(
                id=f"{base}-OCC",
                kind="gbif",
                island=island.slug,
                subject=creature.slug,
                category="creature",
                title=f"GBIF records · {creature.common_name}",
                text=gbif_mod.occurrence_text(creature.common_name, island.name, data),
                source_url=occ_url,
                source_title="GBIF occurrence search",
                publisher="GBIF",
                as_of=doc["fetched_at"][:10],
            ),
        ]
