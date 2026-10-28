"""Measure request latency of the library search and the no model chat, in process.

    python -m scripts.bench                 prints a table
    python -m scripts.bench --out FILE      also writes the numbers as JSON

It drives the real application through its HTTP interface (no network, no model) with the frozen evaluation
questions, so the numbers describe the retrieval and validation path rather than a language model. Rate limits
are switched off and telemetry is off. Run it on the machine you care about: the figures are for that machine.
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def questions() -> list[dict]:
    rows = [json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if r.get("island") and r.get("question")]


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))]


def timed(call, rounds: int) -> list[float]:
    out = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        r = call()
        out.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200, r.text[:200]
    return out


def summarise(name: str, ms: list[float]) -> dict:
    return {"endpoint": name, "n": len(ms), "median_ms": round(statistics.median(ms), 2),
            "p95_ms": round(percentile(ms, 95), 2), "max_ms": round(max(ms), 2)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=5, help="passes over the question set (default 5)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    logging.disable(logging.INFO)  # keep the per request access lines out of the table
    settings = Settings(anthropic_api_key=None, telemetry=False, llm_provider="extractive", source_ttl_days=36500,
                        read_rate_per_min=10**6, chat_rate_per_min=10**6)
    client = TestClient(create_app(settings))
    qs = questions()
    for q in qs[:3]:  # warm the indexes and caches so the first request is not counted
        client.get("/api/library/search", params={"island": q["island"], "q": q["question"]})

    results = [summarise("GET /api/islands", timed(lambda: client.get("/api/islands"), 50))]
    lib: list[float] = []
    chat: list[float] = []
    for _ in range(args.rounds):
        for q in qs:
            lib += timed(lambda q=q: client.get("/api/library/search", params={"island": q["island"], "q": q["question"]}), 1)
            chat += timed(lambda q=q: client.post("/api/chat", json={"island": q["island"], "message": q["question"],
                                                                      "creature": q.get("creature")}), 1)
    results += [summarise("GET /api/library/search", lib), summarise("POST /api/chat (no model)", chat)]

    print(f"{'endpoint':<28}{'n':>6}{'median ms':>12}{'p95 ms':>10}{'max ms':>10}")
    for r in results:
        print(f"{r['endpoint']:<28}{r['n']:>6}{r['median_ms']:>12}{r['p95_ms']:>10}{r['max_ms']:>10}")
    print(f"\n{platform.platform()}, Python {platform.python_version()}, {len(qs)} questions x {args.rounds} passes")
    if args.out:
        args.out.write_text(json.dumps({"platform": platform.platform(), "python": platform.python_version(),
                                        "results": results}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
