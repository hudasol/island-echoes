"""Request telemetry in one SQLite file, so any tool can read it (sqlite3, pandas, DuckDB).

One row per library lookup or chat turn. Question text is NOT stored unless LOG_QUESTIONS=true; by
default only a short hash and the length are kept, which is enough to count repeats.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  route TEXT NOT NULL,            -- library | chat
  island TEXT,
  creature TEXT,
  status TEXT NOT NULL,           -- ok | error | refused_no_evidence
  retrieval_mode TEXT,
  quality TEXT,                   -- library: browse|strong|partial|none
  n_evidence INTEGER,
  answered INTEGER,               -- 1 if the user got an answer from sources
  provider TEXT,
  model TEXT,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  retrieval_ms REAL,
  llm_ms REAL,
  total_ms REAL,
  fact_kept INTEGER,              -- fact sentences that passed the grounding checks
  fact_dropped INTEGER,           -- fact sentences removed by the checks
  raw_flagged INTEGER,            -- sentences flagged on the model's first attempt
  repaired INTEGER,
  error TEXT,
  qhash TEXT,
  qlen INTEGER,
  question TEXT
);
CREATE INDEX IF NOT EXISTS events_ts ON events(ts);
"""

COLUMNS = (
    "ts route island creature status retrieval_mode quality n_evidence answered provider model tokens_in tokens_out "
    "retrieval_ms llm_ms total_ms fact_kept fact_dropped raw_flagged repaired error qhash qlen question"
).split()


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    k = (len(v) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 1)


def qhash(question: str) -> str:
    return hashlib.sha256(" ".join(question.lower().split()).encode()).hexdigest()[:12]


class Telemetry:
    def __init__(self, path: Path | str | None, enabled: bool = True, log_questions: bool = False):
        self.enabled = enabled and path is not None
        self.log_questions = log_questions
        self.path = str(path) if path else None
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self.started = time.time()
        if self.enabled:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA)
            row = self._conn.execute("SELECT MIN(ts) FROM events").fetchone()
            self.started = row[0] or self.started

    def record(self, route: str, question: str = "", **fields) -> None:
        if not self._conn:
            return
        row = {c: None for c in COLUMNS}
        row.update(ts=time.time(), route=route, status=fields.pop("status", "ok"))
        row["qhash"], row["qlen"] = (qhash(question), len(question)) if question else (None, None)
        if self.log_questions and question:
            row["question"] = question[:500]
        for k, v in fields.items():
            if k not in row:
                raise KeyError(k)
            row[k] = int(v) if isinstance(v, bool) else v
        try:
            with self._lock:
                self._conn.execute(
                    f"INSERT INTO events ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})",
                    [row[c] for c in COLUMNS],
                )
                self._conn.commit()
        except sqlite3.Error:  # telemetry must never break a request
            pass

    # ------------------------------------------------------------------
    def _rows(self, days: float) -> list[dict]:
        if not self._conn:
            return []
        since = time.time() - days * 86400
        with self._lock:
            cur = self._conn.execute("SELECT * FROM events WHERE ts >= ? ORDER BY ts", (since,))
            names = [d[0] for d in cur.description]
            return [dict(zip(names, r, strict=True)) for r in cur.fetchall()]

    def summary(self, days: float = 7) -> dict:
        rows = self._rows(days)
        out: dict = {
            "enabled": self.enabled,
            "window_days": days,
            "since": self.started if self.enabled else None,
            "events": len(rows),
        }
        if not rows:
            return out

        def ms(rs: list[dict], key: str) -> dict:
            vals = [r[key] for r in rs if r[key] is not None]
            return {"n": len(vals), "p50": percentile(vals, 0.5), "p95": percentile(vals, 0.95)}

        lib = [r for r in rows if r["route"] == "library" and r["status"] == "ok"]
        chat = [r for r in rows if r["route"] == "chat"]
        chat_ok = [r for r in chat if r["status"] != "error"]
        q = {k: sum(1 for r in lib if r["quality"] == k) for k in ("strong", "partial", "none", "browse")}
        searched = q["strong"] + q["partial"] + q["none"]
        out["library"] = {
            "lookups": len(lib),
            "searches": searched,
            "quality": q,
            "no_answer_rate": round(q["none"] / searched, 4) if searched else None,
            "latency_ms": ms(lib, "total_ms"),
        }
        kept = sum(r["fact_kept"] or 0 for r in chat_ok)
        dropped = sum(r["fact_dropped"] or 0 for r in chat_ok)
        llm_rows = [r for r in chat_ok if r["llm_ms"] is not None]
        out["chat"] = {
            "turns": len(chat),
            "errors": sum(1 for r in chat if r["status"] == "error"),
            "refused_no_evidence": sum(1 for r in chat if r["status"] == "refused_no_evidence"),
            "answered": sum(1 for r in chat_ok if r["answered"]),
            "answer_rate": round(sum(1 for r in chat_ok if r["answered"]) / len(chat_ok), 4) if chat_ok else None,
            "repair_rate": round(sum(1 for r in llm_rows if r["repaired"]) / len(llm_rows), 4) if llm_rows else None,
            "grounded_sentence_rate": round(kept / (kept + dropped), 4) if kept + dropped else None,
            "tokens_in": sum(r["tokens_in"] or 0 for r in chat),
            "tokens_out": sum(r["tokens_out"] or 0 for r in chat),
            "latency_ms": {"total": ms(chat_ok, "total_ms"), "retrieval": ms(chat_ok, "retrieval_ms"), "llm": ms(llm_rows, "llm_ms")},
            "by_model": _count(chat_ok, lambda r: f"{r['provider']}:{r['model']}" if r["provider"] else None),
        }
        out["by_island"] = _count(rows, lambda r: r["island"])
        out["by_retrieval_mode"] = _count(rows, lambda r: r["retrieval_mode"])
        out["by_day"] = _count(rows, lambda r: time.strftime("%Y-%m-%d", time.gmtime(r["ts"])))
        out["repeat_questions"] = sum(1 for _, c in _count(rows, lambda r: r["qhash"]).items() if c > 1)
        if self.log_questions:
            out["unanswered_questions"] = [
                {"island": r["island"], "question": r["question"]}
                for r in rows
                if r["question"] and (r["quality"] == "none" or (r["route"] == "chat" and r["status"] != "error" and not r["answered"]))
            ][-50:]
        return out


def _count(rows: list[dict], key) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        k = key(r)
        if k:
            out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
