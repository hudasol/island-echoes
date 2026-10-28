from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .chat.service import ChatService
from .config import Settings, get_settings
from .data.islands import IslandStore
from .data.sources import SourceStore
from .deps import Deps
from .llm import build_llm
from .narration import load_saved
from .ratelimit import RateLimiter
from .retrieval.factory import build_retriever
from .routes import chat, islands, library, meta
from .telemetry import Telemetry

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


def create_app(settings: Settings | None = None, service: ChatService | None = None) -> FastAPI:
    settings = settings or get_settings()
    island_store = IslandStore.load(settings.islands_dir)
    sources = SourceStore(settings, island_store)
    if service is None:
        service = ChatService(island_store, build_retriever(settings, island_store, sources), build_llm(settings))
    deps = Deps(
        settings=settings,
        islands=island_store,
        sources=sources,
        service=service,
        telemetry=Telemetry(settings.telemetry_path, settings.telemetry, settings.log_questions),
        limiter=RateLimiter(settings.chat_rate_per_min, settings.chat_daily_cap),
        read_limiter=RateLimiter(settings.read_rate_per_min, 10**9,
                                 minute_message="Too many lookups in a minute. Wait a moment and try again."),
        saved_narrations=load_saved(settings.narrations_path),
    )

    app = FastAPI(title="Island Echoes", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
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

    for module in (meta, islands, library, chat):
        app.include_router(module.router(deps))

    if settings.web_dir.exists():
        @app.get("/sw.js", include_in_schema=False)
        def service_worker():
            return FileResponse(settings.web_dir / "sw.js", media_type="application/javascript",
                                headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    return app


app = create_app() if __name__ != "__main__" else None  # uvicorn app.main:app
