"""Objects the route modules share, built once in create_app."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from fastapi import HTTPException, Request

from .chat.service import ChatService
from .config import Settings
from .data.islands import IslandStore
from .data.models import Island
from .data.sources import SourceStore
from .ratelimit import RateLimiter, client_key
from .telemetry import Telemetry


@dataclass
class Deps:
    settings: Settings
    islands: IslandStore
    sources: SourceStore
    service: ChatService
    telemetry: Telemetry
    limiter: RateLimiter
    read_limiter: RateLimiter
    saved_narrations: dict
    started: float = field(default_factory=time.time)

    @property
    def retriever(self):
        return self.service.retriever

    def caller(self, request: Request) -> str:
        return client_key(request, self.settings.trusted_proxy_hops)

    def island(self, slug: str) -> Island:
        try:
            return self.islands.get(slug)
        except KeyError:
            raise HTTPException(404, f"Unknown island {slug!r}") from None
