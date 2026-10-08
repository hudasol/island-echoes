from __future__ import annotations

import json
from pathlib import Path

from .models import Evidence, Fact, Island


class IslandStore:
    """Loads the curated island fact files and exposes facts as citable evidence."""

    def __init__(self, islands: dict[str, Island]):
        self.islands = islands
        self._facts: dict[str, Fact] = {}
        for isl in islands.values():
            for f in isl.facts:
                if f.id in self._facts:
                    raise ValueError(f"duplicate fact id {f.id}")
                self._facts[f.id] = f

    @classmethod
    def load(cls, directory: Path) -> IslandStore:
        islands: dict[str, Island] = {}
        for path in sorted(Path(directory).glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            isl = Island.model_validate(
                {
                    **{k: v for k, v in raw.items() if k != "pin"},
                    "pin": raw["pin"],
                }
            )
            if isl.slug in islands:
                raise ValueError(f"duplicate island {isl.slug}")
            islands[isl.slug] = isl
        if not islands:
            raise FileNotFoundError(f"no island files in {directory}")
        return cls(islands)

    def get(self, slug: str) -> Island:
        try:
            return self.islands[slug]
        except KeyError:
            raise KeyError(f"unknown island {slug!r}") from None

    def fact(self, fact_id: str) -> Fact:
        return self._facts[fact_id]

    def all_facts(self) -> list[Fact]:
        return list(self._facts.values())

    def island_of_fact(self, fact_id: str) -> Island:
        prefix = fact_id.split("-")[0]
        for isl in self.islands.values():
            if isl.prefix == prefix:
                return isl
        raise KeyError(fact_id)

    @staticmethod
    def fact_to_evidence(island: Island, fact: Fact) -> Evidence:
        return Evidence(
            id=fact.id,
            kind="fact",
            island=island.slug,
            subject=fact.subject,
            category=fact.category,
            title=f"{island.name} · {fact.category.replace('_', ' ')}",
            text=fact.statement,
            source_url=fact.source_url,
            source_title=fact.source_title,
            publisher=fact.publisher,
            as_of=fact.retrieved,
            confidence=fact.confidence,
        )
