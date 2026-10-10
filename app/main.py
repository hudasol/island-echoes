from __future__ import annotations

import logging
import math
import time

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .chat.service import ChatResult, ChatService, ChatUnavailable
from .config import Settings, get_settings
from .data.islands import IslandStore
from .data.models import Category, Evidence, Island
from .data.sources import SourceStore, SourceUnavailable
from .llm import LLMError, build_llm
from .narration import load_saved, narration_for
from .ratelimit import RateLimiter, client_key
from .retrieval.factory import build_retriever
from .schemas import (
    ChatRequest,
    ChatResponse,
    CreatureOut,
    Dropped,
    EvidenceOut,
    FactOut,
    GroundingOut,
    IslandDetail,
    IslandSummary,
    LibraryOut,
    NarrationOut,
    SensorsOut,
    SentenceOut,
)
from .telemetry import Telemetry

CATEGORIES = set(Category.__args__)
log = logging.getLogger("island_echoes.access")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)
    log.propagate = False

# Scripts only from this origin; NASA GIBS tiles are the one external resource. Styles allow inline because
# the globe library sets style attributes on its canvas and labels.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https://gibs.earthdata.nasa.gov; connect-src 'self' https://gibs.earthdata.nasa.gov; "
    "worker-src 'self' blob:; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


def _summary(isl: Island) -> dict:
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


def _evidence_out(e: Evidence, cited: bool) -> EvidenceOut:
    return EvidenceOut(**e.model_dump(include=set(EvidenceOut.model_fields) - {"cited"}), cited=cited)


def _chat_response(r: ChatResult) -> ChatResponse:
    cited = set(r.cited_ids)
    ordered = sorted(r.retrieved, key=lambda e: (e.id not in cited, r.cited_ids.index(e.id) if e.id in cited else 0))
    return ChatResponse(
        island=r.island,
        creature=r.creature,
        answered=r.answered,
        sentences=[SentenceOut(text=s.text, kind=s.kind, cites=s.cites) for s in r.sentences],  # type: ignore[arg-type]
        missing=r.missing,
        evidence=[_evidence_out(e, e.id in cited) for e in ordered],
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


def create_app(settings: Settings | None = None, service: ChatService | None = None) -> FastAPI:
    settings = settings or get_settings()
    islands = IslandStore.load(settings.islands_dir)
    sources = SourceStore(settings, islands)
    if service is None:
        llm = build_llm(settings)
        service = ChatService(islands, build_retriever(settings, islands, sources), llm)
    retriever = service.retriever
    telemetry = Telemetry(settings.telemetry_path, settings.telemetry, settings.log_questions)
    app_started = time.time()
    limiter = RateLimiter(settings.chat_rate_per_min, settings.chat_daily_cap)
    read_limiter = RateLimiter(settings.read_rate_per_min, 10**9, minute_message="Too many lookups in a minute. Wait a moment and try again.")

    def caller(request: Request) -> str:
        return client_key(request, settings.trusted_proxy_hops)
    saved_narrations = load_saved(settings.narrations_path)

    app = FastAPI(title="Island Echoes", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.service = service

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        started = time.perf_counter()
        resp = await call_next(request)
        h = resp.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Content-Security-Policy", CSP)
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        h.setdefault("X-Frame-Options", "DENY")
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            h.setdefault("Strict-Transport-Security", "max-age=31536000")
        if request.url.path.startswith("/api/"):
            # method, path and status only: query strings hold what people asked, so they are not logged
            log.info("%s %s %s %.0fms", request.method, request.url.path, resp.status_code, (time.perf_counter() - started) * 1000)
        return resp

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "chat_enabled": service.llm is not None,
            "islands": len(islands.islands),
            "retrieval_mode": getattr(retriever, "mode", "bm25"),
            "llm": f"{service.llm.provider}:{service.llm.model}" if service.llm is not None else None,
            "uptime_s": round(time.time() - app_started),
        }

    @app.get("/api/stats")
    def stats(request: Request, days: float = Query(7, gt=0, le=365)):
        """Aggregate usage and quality numbers. No question text is ever returned unless LOG_QUESTIONS is on."""
        read_limiter.check(caller(request))
        out = telemetry.summary(days)
        out["retrieval_mode"] = getattr(retriever, "mode", "bm25")
        out["llm"] = f"{service.llm.provider}:{service.llm.model}" if service.llm is not None else None
        return out

    @app.get("/api/data-changes")
    def data_changes():
        """Values that changed when live NASA POWER or GBIF data replaced older data on this server."""
        return {"changes": sources.recent_changes()}

    @app.get("/api/islands", response_model=list[IslandSummary])
    def list_islands():
        return [IslandSummary(**_summary(i)) for i in islands.islands.values()]

    def _island(slug: str) -> Island:
        try:
            return islands.get(slug)
        except KeyError:
            raise HTTPException(404, f"Unknown island {slug!r}") from None

    @app.get("/api/islands/{slug}", response_model=IslandDetail)
    def island_detail(slug: str):
        isl = _island(slug)
        facts = [FactOut(**f.model_dump(include=set(FactOut.model_fields))) for f in isl.facts]
        return IslandDetail(**_summary(isl), facts=facts)

    @app.get("/api/islands/{slug}/sensors", response_model=SensorsOut)
    def sensors(slug: str, request: Request, creature: str | None = None):
        read_limiter.check(caller(request))
        isl = _island(slug)
        try:
            c = isl.creature(creature)
        except KeyError:
            raise HTTPException(404, f"Unknown creature {creature!r}") from None
        try:
            return SensorsOut(**sources.power_summary(isl), warning=location_warning(isl, c))
        except SourceUnavailable:
            raise HTTPException(503, "NASA POWER data is unavailable right now.") from None

    @app.get("/api/islands/{slug}/narration", response_model=NarrationOut)
    def narration(slug: str, creature: str | None = None):
        isl = _island(slug)
        try:
            c = isl.creature(creature)
        except KeyError:
            raise HTTPException(404, f"Unknown creature {creature!r}") from None
        sentences = narration_for(islands, isl, c, saved_narrations)
        ids = [i for s in sentences for i in s["cites"]]
        ev = [islands.fact_to_evidence(isl, islands.fact(i)) for i in dict.fromkeys(ids)]
        return NarrationOut(
            island=isl.slug,
            creature=c.slug,
            creature_type=c.creature_type,
            sentences=[SentenceOut(**s) for s in sentences],
            evidence=[_evidence_out(e, True) for e in ev],
        )

    @app.get("/api/library/search", response_model=LibraryOut)
    def library_search(request: Request, island: str, q: str = Query("", max_length=200), category: str | None = None,
                       creature: str | None = None, limit: int = Query(40, ge=1, le=100)):
        read_limiter.check(caller(request))
        isl = _island(island)
        if category and category not in CATEGORIES:
            raise HTTPException(422, f"Unknown category {category!r}")
        try:
            isl.creature(creature)
        except KeyError:
            raise HTTPException(404, f"Unknown creature {creature!r}") from None
        t0 = time.perf_counter()
        res = retriever.library(isl.slug, q, category, creature, limit)
        ms = (time.perf_counter() - t0) * 1000
        telemetry.record("library", q, island=isl.slug, creature=creature, quality=res.quality, n_evidence=res.total,
                         answered=res.quality in ("strong", "partial") if q.strip() else None,
                         retrieval_mode="bm25", total_ms=ms, retrieval_ms=ms)
        return LibraryOut(
            island=isl.slug, query=q, category=category, total=res.total, counts=res.counts,
            results=[_evidence_out(e, True) for e in res.results], notes=res.notes,
            quality=res.quality, partial_ids=sorted(res.partial_ids),
        )

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(req: ChatRequest, request: Request):
        isl = _island(req.island)
        try:
            isl.creature(req.creature)
        except KeyError:
            raise HTTPException(404, f"Unknown creature {req.creature!r}") from None
        limiter.check(caller(request))
        history = [("User" if t.role == "user" else "Agent", t.text) for t in req.history]
        t0 = time.perf_counter()
        try:
            result = service.respond(req.island, req.message, req.creature, history)
        except ChatUnavailable:
            return JSONResponse(
                status_code=503,
                content={"detail": "Chat is not configured on this server (no LLM_PROVIDER set)."},
            )
        except LLMError as exc:
            telemetry.record("chat", req.message, island=req.island, creature=req.creature, status="error",
                             error=str(exc)[:120], total_ms=(time.perf_counter() - t0) * 1000,
                             provider=getattr(service.llm, "provider", None), model=getattr(service.llm, "model", None))
            return JSONResponse(status_code=502, content={"detail": str(exc) or "The language model is unavailable right now."})
        fact_kept = sum(1 for x in result.sentences if x.kind == "fact")
        telemetry.record(
            "chat", req.message, island=result.island, creature=result.creature,
            status="ok" if result.llm_called else "refused_no_evidence",
            retrieval_mode=result.retrieval_mode, n_evidence=len(result.retrieved), answered=result.answered,
            provider=result.provider or None, model=result.model or None,
            tokens_in=result.tokens_in, tokens_out=result.tokens_out, retrieval_ms=result.retrieval_ms,
            llm_ms=result.llm_ms if result.llm_called else None, total_ms=(time.perf_counter() - t0) * 1000,
            fact_kept=fact_kept, fact_dropped=len(result.rejected), raw_flagged=len(result.raw_issues),
            repaired=result.repaired,
        )
        return _chat_response(result)

    if settings.web_dir.exists():
        @app.get("/sw.js", include_in_schema=False)
        def service_worker():
            return FileResponse(settings.web_dir / "sw.js", media_type="application/javascript",
                                headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    return app


app = create_app() if __name__ != "__main__" else None  # uvicorn app.main:app
