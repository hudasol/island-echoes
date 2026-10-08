"""One short narration per creature, spoken when its animation plays.

If data/narrations.json exists (written by scripts/build_narrations.py, which runs the real grounded
pipeline and keeps only validated sentences) it is used. Otherwise a deterministic fallback is built
from the creature's own sourced facts, so every sentence is still cited.
"""

from __future__ import annotations

import json
from pathlib import Path

from .data.islands import IslandStore
from .data.models import Creature, Island

STATUS_WORDS = ("Extinct", "Endangered", "Vulnerable", "Critically")


def _fallback(island: Island, creature: Creature, store: IslandStore) -> list[dict]:
    facts = [f for f in island.facts if f.subject == creature.slug]
    facts.sort(key=lambda f: (f.confidence != "high", f.id))
    status = next((f for f in facts if any(w in f.statement for w in STATUS_WORDS)), None)
    rest = [f for f in facts if f is not status and "GBIF" not in f.statement]
    chosen = ([status] if status else []) + rest[:2]
    sentences = [{"text": f"This is the {creature.common_name}, reporting in from {island.name}.", "kind": "voice", "cites": []}]
    sentences += [{"text": f.statement, "kind": "fact", "cites": [f.id]} for f in chosen]
    return sentences


def load_saved(path: Path) -> dict[str, list[dict]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def narration_for(store: IslandStore, island: Island, creature: Creature, saved: dict[str, list[dict]]) -> list[dict]:
    sentences = saved.get(creature.slug)
    if sentences:
        known = {f.id for f in island.facts}
        if all(set(s.get("cites", [])) <= known for s in sentences):
            return sentences
    return _fallback(island, creature, store)
