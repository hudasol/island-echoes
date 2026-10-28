from __future__ import annotations

import json
import time

from fastapi import APIRouter, HTTPException, Query, Request

from .. import __version__
from ..deps import Deps
from ..overview import build_overview


def router(d: Deps) -> APIRouter:
    r = APIRouter()

    def model_name() -> str | None:
        llm = d.service.llm
        return f"{llm.provider}:{llm.model}" if llm is not None else None

    @r.get("/api/health")
    def health():
        return {
            "status": "ok",
            "version": __version__,
            "chat_enabled": d.service.llm is not None,
            "islands": len(d.islands.islands),
            "retrieval_mode": getattr(d.retriever, "mode", "bm25"),
            "llm": model_name(),
            "uptime_s": round(time.time() - d.started),
        }

    @r.get("/api/stats")
    def stats(request: Request, days: float = Query(7, gt=0, le=365)):
        """Aggregate usage and quality numbers. No question text is ever returned unless LOG_QUESTIONS is on."""
        d.read_limiter.check(d.caller(request))
        out = d.telemetry.summary(days)
        out["retrieval_mode"] = getattr(d.retriever, "mode", "bm25")
        out["llm"] = model_name()
        return out

    @r.get("/api/data-changes")
    def data_changes():
        """Values that changed when live NASA POWER or GBIF data replaced older data on this server."""
        return {"changes": d.sources.recent_changes()}

    overview_cache: dict = {}

    @r.get("/api/overview")
    def overview():
        """What the data set holds per island, and how old the external data is."""
        if not overview_cache:
            overview_cache.update(build_overview(d.settings, d.islands))
        return overview_cache

    @r.get("/api/evaluation")
    def evaluation():
        """Stored evaluation numbers: retrieval on the gold sets and the end to end baselines."""
        path = d.settings.evaluation_path
        if not path.exists():
            raise HTTPException(404, "No evaluation summary is installed.")
        return json.loads(path.read_text(encoding="utf-8"))

    return r
