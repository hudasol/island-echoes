"""Small in-memory limiter so a public deployment cannot drain the API key."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, per_minute: int, daily_cap: int, clock=time.monotonic, wall=time.time,
                 minute_message: str = "Too many questions in a minute. Give the instruments a moment."):
        self.per_minute, self.daily_cap, self.minute_message = per_minute, daily_cap, minute_message
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
        if len(self._hits) > 10_000:  # forget keys that have gone quiet so memory stays bounded
            for k in [k for k, v in self._hits.items() if not v or now - v[-1] > 60]:
                del self._hits[k]
        q = self._hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            raise HTTPException(429, self.minute_message)
        q.append(now)
        self._today += 1


def client_key(request: Request, trusted_hops: int = 1) -> str:
    """The caller's address as seen by the nearest trusted proxy.

    Each proxy appends the address it received the request from, so only the right-most entries can be
    trusted; anything further left is supplied by the caller and can be forged to dodge the limit.
    With `trusted_hops` proxies in front of the app, the entry that many places from the right is the client.
    """
    fwd = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if fwd and trusted_hops > 0:
        return fwd[max(len(fwd) - trusted_hops, 0)]
    return request.client.host if request.client else "unknown"
