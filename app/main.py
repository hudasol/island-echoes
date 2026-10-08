from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .chat.llm import AnthropicAnswerLLM, LLMError
from .chat.service import ChatResult, ChatService, ChatUnavailable
from .config import Settings, get_settings
from .data.islands import IslandStore
from .data.models import Evidence, Island
from .data.retrieval import Retriever
from .data.sources import SourceStore, SourceUnavailable
from .narration import load_saved, narration_for
from .ratelimit import RateLimiter, client_key
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
    NarrationOut,
    SensorsOut,
    SentenceOut,
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


def create_app(settings: Settings | None = None, service: ChatService | None = None) -> FastAPI:
    settings = settings or get_settings()
    islands = IslandStore.load(settings.islands_dir)
    sources = SourceStore(settings, islands)
    if service is None:
        llm = (
            AnthropicAnswerLLM(settings.anthropic_api_key, settings.anthropic_model)
            if settings.anthropic_api_key
            else None
        )
        service = ChatService(islands, Retriever(islands, sources), llm)
    limiter = RateLimiter(settings.chat_rate_per_min, settings.chat_daily_cap)
    saved_narrations = load_saved(settings.narrations_path)

    app = FastAPI(title="Island Echoes", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.service = service

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp

    @app.get("/api/health")
    def health():
        return {"status": "ok", "chat_enabled": service.llm is not None, "islands": len(islands.islands)}

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
    def sensors(slug: str):
        isl = _island(slug)
        try:
            return SensorsOut(**sources.power_summary(isl))
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

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(req: ChatRequest, request: Request):
        isl = _island(req.island)
        try:
            isl.creature(req.creature)
        except KeyError:
            raise HTTPException(404, f"Unknown creature {req.creature!r}") from None
        limiter.check(client_key(request))
        history = [("User" if t.role == "user" else "Agent", t.text) for t in req.history]
        try:
            result = service.respond(req.island, req.message, req.creature, history)
        except ChatUnavailable:
            return JSONResponse(
                status_code=503,
                content={"detail": "Chat is not configured on this server (missing ANTHROPIC_API_KEY)."},
            )
        except LLMError as exc:
            return JSONResponse(status_code=502, content={"detail": str(exc) or "The language model is unavailable right now."})
        return _chat_response(result)

    if settings.web_dir.exists():
        @app.get("/sw.js", include_in_schema=False)
        def service_worker():
            return FileResponse(settings.web_dir / "sw.js", media_type="application/javascript",
                                headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    return app


app = create_app() if __name__ != "__main__" else None  # uvicorn app.main:app
