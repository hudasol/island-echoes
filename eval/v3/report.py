"""Tables for the sealed synthetic evaluation (preregistration 3), built from the stored runs in eval/results/v3/.

Every number is computed here from stored records and the question file; nothing is typed by hand.
All items are synthetic (see docs/research/PREREGISTRATION_3.md), and every table says so.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "eval" / "results" / "v3"
QUESTIONS = ROOT / "eval" / "v3" / "test.jsonl"

# (label, file, description) in display order
ARMS = [
    ("Always refuse", "refuse-all.json", "no model"),
    ("Model alone, no sources", "qwen25-3b-closed.json", "Qwen2.5 3B, closed book"),
    ("Retrieval and model, no validator", "arm-unvalidated.json", "Qwen2.5 3B"),
    ("Validator, rejected sentences dropped (1.1 behaviour)", "arm-drop.json", "Qwen2.5 3B"),
    ("Validator, rejected sentences replaced by the cited source sentence", "arm-extractive.json", "Qwen2.5 3B"),
    ("Dropped, with the climate route", "arm-drop-climate.json", "Qwen2.5 3B"),
    ("Replaced, with the climate route", "arm-extractive-climate.json", "Qwen2.5 3B"),
    ("Dropped, climate route with the unknown place fix (post hoc)", "arm-drop-climate-fixed.json", "Qwen2.5 3B"),
    ("Replaced, climate route with the unknown place fix (post hoc)", "arm-extractive-climate-fixed.json", "Qwen2.5 3B"),
]


def _load(name: str) -> dict | None:
    p = V3 / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _questions() -> dict[str, dict]:
    return {q["id"]: q for q in (json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip())}


def _scores(run: dict, qs: dict[str, dict]):
    from eval import metrics

    return {r["id"]: metrics.score_question(qs[r["id"]], r) for r in run["records"] if r["id"] in qs and "error" not in r}


def _pool():
    from app.config import Settings
    from app.data.islands import IslandStore
    from app.data.sources import SourceStore
    from eval import baselines

    st = Settings(anthropic_api_key=None, telemetry=False, source_ttl_days=36500, cache_dir=Path(tempfile.mkdtemp(prefix="ie-v3-")))
    islands = IslandStore.load(st.islands_dir)
    return baselines.build_pools(islands, SourceStore(st, islands, http=object()))


def section() -> str:
    runs = {name: _load(name) for _, name, _ in ARMS}
    have = [(label, name, desc) for label, name, desc in ARMS if runs[name]]
    if not have or not QUESTIONS.exists():
        return ""
    from eval import baselines
    from eval.compare import mcnemar_exact
    from eval.metrics import wilson

    qs = _questions()
    pools = _pool()
    n_ans = sum(not q["should_refuse"] for q in qs.values())
    n_ref = len(qs) - n_ans

    def ci(k: int, n: int) -> str:
        lo, hi = wilson(k, n)
        return f"{100 * k / n:.0f}% ({k}/{n}) [{100 * lo:.0f}-{100 * hi:.0f}]" if n else "n/a"

    out = [
        "## Sealed synthetic evaluation (150 questions, preregistration 3)", "",
        f"All {len(qs)} questions are **synthetic**: written by a local model from the fact files, with gold constructed from the same facts "
        f"({n_ans} answerable, {n_ref} that should be refused). Brackets are 95% Wilson intervals. Sources of the plan, the hashes and the "
        "predictions are in `docs/research/PREREGISTRATION_3.md`. These numbers are not comparable with the frozen 30, which were written by hand.", "",
        "Ten of the 150 questions errored in the 3B run because the model returned malformed JSON; they are excluded from the "
        "model rows (140 scored) and counted in the always refuse row (150). The \"claim outside the sources\" column is a mechanical check "
        "against the facts of the question's own island. In the climate route rows its four hits are checker limits, not "
        "invented numbers: three comparison answers quote the second island's table value, and one names a month that the "
        "table itself supplies. Each of these sentences is produced by the route directly from the stored POWER tables.", "",
        "| System | Passed | False refusals (of answerable) | Refusal accuracy (of should refuse) | Key fact recall | Answers with a claim outside the sources |",
        "|---|---|---|---|---|---|",
    ]
    per: dict[str, dict] = {}
    for label, name, _ in have:
        run = runs[name]
        sc = _scores(run, qs)
        per[name] = sc
        passed = sum(s.passed for s in sc.values())
        fr = sum(1 for s in sc.values() if not s.should_refuse and s.detail == "false refusal")
        ra = sum(1 for s in sc.values() if s.should_refuse and s.passed)
        kh = sum(s.key_hits for s in sc.values() if not s.should_refuse)
        kt = sum(s.key_total for s in sc.values() if not s.should_refuse)
        o = baselines.outside_sources_summary(run, qs, pools)["answers"]
        out.append(f"| {label} | {ci(passed, len(sc))} | {ci(fr, n_ans)} | {ci(ra, n_ref)} | {ci(kh, kt)} | {ci(o['k'], o['n'])} |")

    types = sorted({q["type"] for q in qs.values()})
    out += ["", "### Passes by question type", "", "| System | " + " | ".join(f"{t} ({sum(q['type'] == t for q in qs.values())})" for t in types) + " |", "|---|" + "---|" * len(types)]
    for label, name, _ in have:
        sc = per[name]
        out.append(f"| {label} | " + " | ".join(str(sum(1 for s in sc.values() if s.type == t and s.passed)) for t in types) + " |")

    def paired(a: str, b: str, only: str | None = None) -> tuple[int, int, float, int]:
        sa, sb = per.get(a), per.get(b)
        if not sa or not sb:
            return 0, 0, 1.0, 0
        ids = [i for i in sa if i in sb and (only is None or sa[i].type == only)]
        better = sum(1 for i in ids if sb[i].passed and not sa[i].passed)
        worse = sum(1 for i in ids if sa[i].passed and not sb[i].passed)
        return better, worse, mcnemar_exact(better, worse), len(ids)

    comps = [
        ("C1: replaced against dropped, all questions", "arm-drop.json", "arm-extractive.json", None),
        ("C2: climate route on against off (dropped), climate questions", "arm-drop.json", "arm-drop-climate.json", "climate"),
        ("C2: climate route on against off (dropped), all questions", "arm-drop.json", "arm-drop-climate.json", None),
        ("C3: no validator against dropped, all questions", "arm-unvalidated.json", "arm-drop.json", None),
    ]
    rows = []
    for name, a, b, only in comps:
        if a in per and b in per:
            better, worse, p, n = paired(a, b, only)
            rows.append(f"| {name} | {n} | {better} | {worse} | {p:.3f} |")
    if rows:
        out += ["", "### Paired comparisons (exact McNemar on passes; second system better / worse)", "",
                "| Comparison | Questions | Only second passes | Only first passes | p |", "|---|---|---|---|---|", *rows]
    return "\n".join(out) + "\n"
