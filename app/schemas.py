from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["user", "agent"]
    text: str = Field(max_length=600)


class ChatRequest(BaseModel):
    island: str = Field(max_length=40)
    message: str = Field(min_length=1, max_length=500)
    creature: str | None = Field(default=None, max_length=60)
    history: list[Turn] = Field(default_factory=list, max_length=8)


class SentenceOut(BaseModel):
    text: str
    kind: Literal["fact", "voice"]
    cites: list[str]


class EvidenceOut(BaseModel):
    id: str
    kind: Literal["fact", "power", "gbif"]
    category: str = ""
    subject: str = "island"
    title: str
    text: str
    source_url: str
    source_title: str
    publisher: str
    as_of: str
    confidence: str
    cited: bool


class Dropped(BaseModel):
    text: str
    issues: list[str]


class GroundingOut(BaseModel):
    retrieved: int
    cited: int
    repaired: bool
    llm_called: bool
    dropped: list[Dropped]
    notes: list[str]


class ChatResponse(BaseModel):
    island: str
    creature: str
    answered: bool
    sentences: list[SentenceOut]
    missing: str
    evidence: list[EvidenceOut]
    grounding: GroundingOut


class CreatureOut(BaseModel):
    slug: str
    common_name: str
    scientific_name: str
    creature_type: str
    iucn_status: str
    status_note: str


class FactOut(BaseModel):
    id: str
    category: str
    subject: str
    statement: str
    publisher: str
    source_url: str
    confidence: str


class IslandSummary(BaseModel):
    slug: str
    name: str
    alt_names: list[str]
    lat: float
    lon: float
    pin_note: str
    territory: str
    creatures: list[CreatureOut]
    fact_count: int
    gaps: list[str]
    conflicts: list[str]


class IslandDetail(IslandSummary):
    facts: list[FactOut]


class SensorOut(BaseModel):
    key: str
    label: str
    unit: str
    value: float | None
    monthly: list[float | None]
    evidence_id: str


class SensorsOut(BaseModel):
    island: str
    as_of: str
    period: str
    cell_lat: float
    cell_lon: float
    items: list[SensorOut]
    warning: str = ""


class NarrationOut(BaseModel):
    island: str
    creature: str
    creature_type: str
    sentences: list[SentenceOut]
    evidence: list[EvidenceOut]


class LibraryOut(BaseModel):
    island: str
    query: str
    category: str | None
    total: int
    counts: dict[str, int]
    results: list[EvidenceOut]
    notes: list[str]
    quality: str = "browse"
    partial_ids: list[str] = []
