from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CreatureType = Literal["bird", "marine", "reptile", "mammal"]
Confidence = Literal["high", "medium", "low"]
Category = Literal[
    "location",
    "climate",
    "terrain",
    "geology",
    "history",
    "people_governance",
    "ecology",
    "threats",
    "conservation",
    "creature",
]


class Fact(BaseModel):
    id: str
    category: Category
    subject: str = "island"  # "island" or a creature slug
    statement: str
    source_url: str
    source_title: str
    publisher: str
    retrieved: str
    evidence_note: str
    confidence: Confidence


class Creature(BaseModel):
    slug: str
    common_name: str
    scientific_name: str
    creature_type: CreatureType
    iucn_status: str
    gbif_search_name: str
    gbif_usage_key: int | None = None
    status_note: str = ""


class Pin(BaseModel):
    lat: float
    lon: float
    note: str


class Island(BaseModel):
    slug: str
    name: str
    alt_names: list[str] = Field(default_factory=list)
    pin: Pin
    territory: str
    creatures: list[Creature]
    facts: list[Fact]
    sources: list[dict]
    gaps: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)

    @property
    def prefix(self) -> str:
        return self.facts[0].id.split("-")[0]

    def creature(self, slug: str | None) -> Creature:
        if slug is None:
            return self.creatures[0]
        for c in self.creatures:
            if c.slug == slug:
                return c
        raise KeyError(f"{self.slug} has no creature {slug!r}")


class Evidence(BaseModel):
    """One citable unit shown to the model. The id is what the model cites."""

    id: str
    kind: Literal["fact", "power", "gbif"]
    island: str
    subject: str = "island"
    category: str
    title: str
    text: str
    source_url: str
    source_title: str
    publisher: str
    as_of: str
    confidence: Confidence = "high"
