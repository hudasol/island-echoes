from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..data.sources import SourceUnavailable
from ..deps import Deps
from ..narration import narration_for
from ..presenters import evidence_out, location_warning, summary
from ..schemas import ConservationOut, FactOut, IslandDetail, IslandSummary, NarrationOut, SensorsOut, SentenceOut


def router(d: Deps) -> APIRouter:
    r = APIRouter()

    def creature_of(isl, slug):
        try:
            return isl.creature(slug)
        except KeyError:
            raise HTTPException(404, f"Unknown creature {slug!r}") from None

    @r.get("/api/islands", response_model=list[IslandSummary])
    def list_islands():
        return [IslandSummary(**summary(i)) for i in d.islands.islands.values()]

    @r.get("/api/islands/{slug}", response_model=IslandDetail)
    def island_detail(slug: str):
        isl = d.island(slug)
        facts = [FactOut(**f.model_dump(include=set(FactOut.model_fields))) for f in isl.facts]
        return IslandDetail(**summary(isl), facts=facts)

    @r.get("/api/islands/{slug}/sensors", response_model=SensorsOut)
    def sensors(slug: str, request: Request, creature: str | None = None):
        d.read_limiter.check(d.caller(request))
        isl = d.island(slug)
        c = creature_of(isl, creature)
        try:
            return SensorsOut(**d.sources.power_summary(isl), warning=location_warning(isl, c))
        except SourceUnavailable:
            raise HTTPException(503, "NASA POWER data is unavailable right now.") from None

    @r.get("/api/islands/{slug}/conservation", response_model=ConservationOut)
    def conservation(slug: str, request: Request, creature: str | None = None):
        """The IUCN Red List category that GBIF holds for the creature. 404 when GBIF has none."""
        d.read_limiter.check(d.caller(request))
        isl = d.island(slug)
        c = creature_of(isl, creature)
        try:
            found = d.sources.conservation(isl, c.slug)
        except SourceUnavailable:
            raise HTTPException(503, "GBIF data is unavailable right now.") from None
        if found is None:
            raise HTTPException(404, "GBIF holds no IUCN category for this creature.")
        return found

    @r.get("/api/islands/{slug}/narration", response_model=NarrationOut)
    def narration(slug: str, creature: str | None = None):
        isl = d.island(slug)
        c = creature_of(isl, creature)
        sentences = narration_for(d.islands, isl, c, d.saved_narrations)
        ids = [i for s in sentences for i in s["cites"]]
        ev = [d.islands.fact_to_evidence(isl, d.islands.fact(i)) for i in dict.fromkeys(ids)]
        return NarrationOut(
            island=isl.slug,
            creature=c.slug,
            creature_type=c.creature_type,
            sentences=[SentenceOut(**s) for s in sentences],
            evidence=[evidence_out(e, True) for e in ev],
        )

    return r
