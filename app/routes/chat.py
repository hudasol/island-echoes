from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..chat.service import ChatUnavailable
from ..deps import Deps
from ..llm import LLMError
from ..presenters import chat_response
from ..schemas import ChatRequest, ChatResponse


def router(d: Deps) -> APIRouter:
    r = APIRouter()

    @r.post("/api/chat", response_model=ChatResponse)
    def chat(req: ChatRequest, request: Request):
        isl = d.island(req.island)
        try:
            isl.creature(req.creature)
        except KeyError:
            raise HTTPException(404, f"Unknown creature {req.creature!r}") from None
        d.limiter.check(d.caller(request))
        history = [("User" if t.role == "user" else "Agent", t.text) for t in req.history]
        t0 = time.perf_counter()
        try:
            result = d.service.respond(req.island, req.message, req.creature, history)
        except ChatUnavailable:
            return JSONResponse(
                status_code=503,
                content={"detail": "Chat is not configured on this server (no LLM_PROVIDER set)."},
            )
        except LLMError as exc:
            d.telemetry.record("chat", req.message, island=req.island, creature=req.creature, status="error",
                               error=str(exc)[:120], total_ms=(time.perf_counter() - t0) * 1000,
                               provider=getattr(d.service.llm, "provider", None), model=getattr(d.service.llm, "model", None))
            return JSONResponse(status_code=502, content={"detail": str(exc) or "The language model is unavailable right now."})
        fact_kept = sum(1 for x in result.sentences if x.kind == "fact")
        d.telemetry.record(
            "chat", req.message, island=result.island, creature=result.creature,
            status="ok" if result.llm_called else "refused_no_evidence",
            retrieval_mode=result.retrieval_mode, n_evidence=len(result.retrieved), answered=result.answered,
            provider=result.provider or None, model=result.model or None,
            tokens_in=result.tokens_in, tokens_out=result.tokens_out, retrieval_ms=result.retrieval_ms,
            llm_ms=result.llm_ms if result.llm_called else None, total_ms=(time.perf_counter() - t0) * 1000,
            fact_kept=fact_kept, fact_dropped=len(result.rejected), raw_flagged=len(result.raw_issues),
            repaired=result.repaired,
        )
        return chat_response(result)

    return r
