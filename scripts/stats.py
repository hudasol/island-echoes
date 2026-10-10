"""Print usage and quality statistics from the telemetry database.

    python -m scripts.stats                 # last 7 days, readable
    python -m scripts.stats --days 30 --json
    python -m scripts.stats --csv events.csv   # raw events for pandas / DuckDB / a spreadsheet
    python -m scripts.stats --url https://island-echoes.onrender.com   # read a deployed server instead
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.telemetry import Telemetry  # noqa: E402


def fmt_pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render(s: dict) -> str:
    if not s.get("events"):
        return f"No events in the last {s.get('window_days', 7)} days."
    lib, chat = s["library"], s["chat"]
    ms = lambda d: "n/a" if not d or d["p50"] is None else f"p50 {d['p50']:.0f} ms, p95 {d['p95']:.0f} ms"  # noqa: E731
    lines = [
        f"Window: last {s['window_days']} days · {s['events']} events · retrieval {s.get('retrieval_mode')} · model {s.get('llm') or 'none'}",
        "",
        "LIBRARY",
        f"  lookups {lib['lookups']} · searches {lib['searches']} · no-answer rate {fmt_pct(lib['no_answer_rate'])}",
        f"  quality {lib['quality']}",
        f"  latency {ms(lib['latency_ms'])}",
        "",
        "CHAT",
        f"  turns {chat['turns']} · answered {chat['answered']} (rate {fmt_pct(chat['answer_rate'])}) · errors {chat['errors']} · refused (no evidence) {chat['refused_no_evidence']}",
        f"  grounded-sentence rate {fmt_pct(chat['grounded_sentence_rate'])} · repair rate {fmt_pct(chat['repair_rate'])}",
        f"  tokens in/out {chat['tokens_in']}/{chat['tokens_out']}",
        f"  latency total {ms(chat['latency_ms']['total'])}",
        f"          retrieval {ms(chat['latency_ms']['retrieval'])}",
        f"          model {ms(chat['latency_ms']['llm'])}",
        f"  models {chat['by_model']}",
        "",
        f"BY ISLAND  {s['by_island']}",
        f"BY DAY     {s['by_day']}",
    ]
    if s.get("unanswered_questions"):
        lines += ["", "UNANSWERED (library gaps worth filling)"] + [f"  [{u['island']}] {u['question']}" for u in s["unanswered_questions"][-15:]]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--csv", type=Path, help="export raw events to this CSV file")
    ap.add_argument("--db", type=Path)
    ap.add_argument("--url", help="read /api/stats from a running server")
    a = ap.parse_args()
    if a.url:
        import httpx

        s = httpx.get(a.url.rstrip("/") + "/api/stats", params={"days": a.days}, timeout=60).json()
    else:
        path = a.db or get_settings().telemetry_path
        if not Path(path).exists():
            print(f"No telemetry database at {path} yet. Use the app first.", file=sys.stderr)
            return 1
        if a.csv:
            con = sqlite3.connect(path)
            cur = con.execute("SELECT * FROM events ORDER BY ts")
            with a.csv.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([d[0] for d in cur.description])
                w.writerows(cur)
            print(f"wrote {a.csv}")
            return 0
        s = Telemetry(path).summary(a.days)
    print(json.dumps(s, indent=1) if a.json else render(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
