"""Turn domain objects into the response models the API returns."""

from __future__ import annotations

import math

from .chat.service import ChatResult
from .data.models import Evidence, Island
from .schemas import ChatResponse, CreatureOut, Dropped, EvidenceOut, GroundingOut, SentenceOut


def summary(isl: Island) -> dict:
    return dict(
        slug=isl.slug,
        name=isl.name,
        alt_names=isl.alt_names,
        lat=isl.pin.lat,
        lon=isl.pin.lon,
        pin_note=isl.pin.note,
        territory=isl.territory,
        creatures=[CreatureOut(**c.model_dump(include=set(CreatureOut.model_fields))) for c in isl.creatures],
        fact_count=len(isl.facts),
        gaps=isl.gaps,
        conflicts=isl.conflicts,
    )


def evidence_out(e: Evidence, cited: bool) -> EvidenceOut:
    return EvidenceOut(**e.model_dump(include=set(EvidenceOut.model_fields) - {"cited"}), cited=cited)


def chat_response(r: ChatResult) -> ChatResponse:
    cited = set(r.cited_ids)
    ordered = sorted(r.retrieved, key=lambda e: (e.id not in cited, r.cited_ids.index(e.id) if e.id in cited else 0))
    return ChatResponse(
        island=r.island,
        creature=r.creature,
        answered=r.answered,
        sentences=[SentenceOut(text=s.text, kind=s.kind, cites=s.cites) for s in r.sentences],  # type: ignore[arg-type]
        missing=r.missing,
        evidence=[evidence_out(e, e.id in cited) for e in ordered],
        grounding=GroundingOut(
            retrieved=len(r.retrieved),
            cited=len(cited),
            repaired=r.repaired,
            llm_called=r.llm_called,
            dropped=[Dropped(**d) for d in r.rejected],
            notes=r.notes,
        ),
    )


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def location_warning(isl: Island, c) -> str:
    """Tell the reader when a creature lives somewhere other than the point the NASA POWER readings describe."""
    if c.home_lat is None or c.home_lon is None:
        return ""
    km = _km(isl.pin.lat, isl.pin.lon, c.home_lat, c.home_lon)
    if km < 25:
        return ""
    return (
        f"The {c.common_name} lived on {c.home_name}, about {km:.0f} km from the point these readings describe "
        f"({isl.pin.lat:.1f}, {isl.pin.lon:.1f}). Read them as regional context, not as conditions on {c.home_name}."
    )
