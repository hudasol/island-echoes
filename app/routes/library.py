from __future__ import annotations

import time
from typing import get_args

from fastapi import APIRouter, HTTPException, Query, Request

from ..data.models import Category
from ..deps import Deps
from ..presenters import evidence_out
from ..schemas import LibraryOut

CATEGORIES = set(get_args(Category))


def router(d: Deps) -> APIRouter:
    r = APIRouter()

    @r.get("/api/library/search", response_model=LibraryOut)
    def library_search(request: Request, island: str, q: str = Query("", max_length=200), category: str | None = None,
                       creature: str | None = None, limit: int = Query(40, ge=1, le=100)):
        d.read_limiter.check(d.caller(request))
        isl = d.island(island)
        if category and category not in CATEGORIES:
            raise HTTPException(422, f"Unknown category {category!r}")
        try:
            isl.creature(creature)
        except KeyError:
            raise HTTPException(404, f"Unknown creature {creature!r}") from None
        t0 = time.perf_counter()
        res = d.retriever.library(isl.slug, q, category, creature, limit)
        ms = (time.perf_counter() - t0) * 1000
        d.telemetry.record("library", q, island=isl.slug, creature=creature, quality=res.quality, n_evidence=res.total,
                           answered=res.quality in ("strong", "partial") if q.strip() else None,
                           retrieval_mode="bm25", total_ms=ms, retrieval_ms=ms)
        return LibraryOut(
            island=isl.slug, query=q, category=category, total=res.total, counts=res.counts,
            results=[evidence_out(e, True) for e in res.results], notes=res.notes,
            quality=res.quality, partial_ids=sorted(res.partial_ids),
        )

    return r
