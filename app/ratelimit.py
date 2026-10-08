"""Small in-memory limiter so a public deployment cannot drain the API key."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, per_minute: int, daily_cap: int, clock=time.monotonic, wall=time.time):
        self.per_minute, self.daily_cap = per_minute, daily_cap
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._clock, self._wall = clock, wall
        self._day = int(wall() // 86400)
        self._today = 0

    def check(self, key: str) -> None:
        day = int(self._wall() // 86400)
        if day != self._day:
            self._day, self._today = day, 0
        if self._today >= self.daily_cap:
            raise HTTPException(429, "The daily chat budget for this demo is used up. Try again tomorrow.")
        now = self._clock()
        q = self._hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            raise HTTPException(429, "Too many questions in a minute. Give the instruments a moment.")
        q.append(now)
        self._today += 1


def client_key(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
