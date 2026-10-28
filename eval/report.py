"""Render every stored eval run into one comparison (docs/RESULTS.md).

    python -m eval.report            # writes docs/RESULTS.md and prints it

Reads eval/results/*.json (generation runs from eval.run_eval), eval/results/retrieval.json, development-set
runs in eval/results/dev/ and, if present, the hand-written analysis in eval/results/NOTES.md.
Only runs that exist are reported; nothing is filled in.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402
from app.data.sources import SourceStore  # noqa: E402
from eval import baselines, metrics  # noqa: E402
from eval.retrieval_eval import to_markdown as retrieval_md  # noqa: E402

RESULTS = ROOT / "eval" / "results"


def load_runs(folder: Path = RESULTS) -> list[dict]:
    runs = []
    for p in sorted(folder.glob("*.json")):
        if p.name == "retrieval.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if "meta" in d and "summary" in d:
            d["_file"] = p.name
            runs.append(d)
    return runs


def _pct(v: dict) -> str:
    return metrics.pct(v["k"], v["n"]) if v["n"] else "n/a"


def _short(v: dict) -> str:
    if not v["n"]:
        return "n/a"
    lo, hi = metrics.wilson(v["k"], v["n"])
    return f"{100 * v['k'] / v['n']:.0f}% ({v['k']}/{v['n']}) [{100 * lo:.0f}-{100 * hi:.0f}]"


def latency(run: dict) -> str:
    secs = sorted(r["seconds"] for r in run["records"] if "seconds" in r and r.get("llm_called"))
    if not secs:
        return "n/a"
    p = lambda q: secs[min(len(secs) - 1, int(q * len(secs)))]  # noqa: E731
    return f"{p(0.5):.0f} / {p(0.95):.0f} s"


def tokens(run: dict) -> str:
    recs = [r for r in run["records"] if r.get("llm_called")]
    if not recs:
        return "n/a"
    return f"{sum(r.get('tokens_in', 0) for r in recs) // len(recs)} / {sum(r.get('tokens_out', 0) for r in recs) // len(recs)}"


def generation_table(runs: list[dict], with_check: bool = False) -> str:
    head = ("| run | model | retrieval (k) |" + (" table check |" if with_check else "") + " passed | key-fact recall | source recall | false refusals | refusal accuracy "
            "| first-attempt failures | repaired | errored | median / p95 time | tokens in / out per call |")
    lines = [head, "|" + "---|" * (14 if with_check else 13)]
    for r in runs:
        m, s = r["meta"], r["summary"]
        lines.append(
            f"| {m.get('label', r['_file'])} | {m.get('answer_model')} | {m.get('retrieval_mode', 'bm25')} ({m.get('retrieval_k', 12)}) "
            + (f"| {'on' if m.get('table_check') else 'off'} " if with_check else "")
            + f"| {_short(s['questions_passed'])} | {_short(s['key_fact_recall'])} | {_short(s['expected_source_recall'])} "
            f"| {_short(s['false_refusals'])} | {_short(s['refusal_accuracy'])} | {_short(s['validator_first_pass_failures'])} "
            f"| {_short(s['repaired_answers'])} | {m.get('errored', 0)} | {latency(r)} | {tokens(r)} |"
        )
    return "\n".join(lines)


def issue_table(runs: list[dict]) -> str:
    from eval.compare import ISSUE_KINDS, issue_breakdown

    counts = {r["meta"].get("label", r["_file"]): issue_breakdown(r) for r in runs}
    kinds = [k for k, _ in ISSUE_KINDS] + ["other"]
    lines = ["| issue | " + " | ".join(counts) + " |", "|---|" + "---|" * len(counts)]
    for k in kinds:
        if any(c[k] for c in counts.values()):
            lines.append(f"| {k} | " + " | ".join(str(c[k]) for c in counts.values()) + " |")
    return "\n".join(lines)


# Stored runs shown beside the baselines for reference. They were served by Ollama in an earlier session, so they
# are not a matched comparison with the baseline runs, which all use one serving stack.
REFERENCE_RUNS = ("extractive-top-evidence-bm25.json", "qwen25-3b-ollama-bm25.json")


def _pool_inputs() -> tuple[dict, dict]:
    """The sources each island may be quoted from, read from the committed snapshots only (never the network)."""
    settings = Settings(anthropic_api_key=None, telemetry=False, source_ttl_days=36500)
    islands = IslandStore.load(settings.islands_dir)
    return baselines.build_pools(islands, SourceStore(settings, islands, http=object())), {}


def baseline_table(runs: list[dict], pools: dict) -> str:
    from eval.run_eval import RESULTS as _R  # noqa: F401  (keeps the questions path in one place)
    from eval.run_eval import load_questions

    head = ("| system | model | retrieval | passed | false refusals | refusal accuracy | key-fact recall "
            "| answers with a number or name found in no source | median / p95 time |")
    lines = [head, "|" + "---|" * 9]
    cache: dict[str, dict] = {}
    for r in runs:
        m, s = r["meta"], r["summary"]
        qfile = m.get("questions_file", "questions.jsonl")
        if qfile not in cache:
            cache[qfile] = {q["id"]: q for q in load_questions(None, ROOT / "eval" / qfile)}
        out = baselines.outside_sources_summary(r, cache[qfile], pools)
        a = out["answers"]
        outside = _short(a) if a["n"] else "n/a (no answers)"
        system = m.get("system", "full")
        label = {"full": "retrieval + model + validator", "unvalidated": "retrieval + model, no validator",
                 "closed-book": "model alone, no sources", "refuse-all": "always refuse"}.get(system, system)
        if m.get("provider") == "extractive":
            label = "retrieval only, quotes the top sources"
        lines.append(
            f"| {label} | {m.get('answer_model')} | {m.get('retrieval_mode', 'none')} ({m.get('retrieval_k', 12)}) "
            f"| {_short(s['questions_passed'])} | {_short(s['false_refusals'])} | {_short(s['refusal_accuracy'])} "
            f"| {_short(s['key_fact_recall'])} | {outside} | {latency(r)} |"
        )
    return "\n".join(lines)


def build() -> str:
    runs = load_runs()
    parts = ["# Results", "", "Generated by `python -m eval.report` from the files in `eval/results/`. Brackets are 95% intervals.", ""]
    ret = RESULTS / "retrieval.json"
    if ret.exists():
        parts += ["## Retrieval (does the right fact reach the model?)", "", retrieval_md(json.loads(ret.read_text(encoding="utf-8"))), ""]
    if runs:
        parts += [
            "## Generation (30 questions, end to end)",
            "",
            generation_table(runs),
            "",
            "Reading the columns: *passed* needs every check for a question; *first-attempt failures* is the share of the model's "
            "fact sentences the validator rejected before the repair retry (a mechanical proxy for hallucination: invented IDs, "
            "numbers or names that are not in the cited text). No judge model was run, so semantic faithfulness beyond those "
            "checks is not measured here.",
            "",
            "First-attempt validator issues by kind, summed over each run (a sentence can have more than one issue):",
            "",
            issue_table(runs),
            "",
        ]
    else:
        parts += ["No generation runs stored yet."]
    base = load_runs(RESULTS / "baselines")
    if base:
        refs = [r for r in load_runs() if r["_file"] in REFERENCE_RUNS]
        pools, _ = _pool_inputs()
        order = {"refuse-all": 0, "closed-book": 1, "unvalidated": 3, "full": 4}
        base.sort(key=lambda r: (order.get(r["meta"].get("system", "full"), 9), r["_file"]))
        parts += [
            "## Baselines (frozen 30 questions)",
            "",
            "Every system answers the same 30 questions and is scored by the same code. Rows in the first table were run in one "
            "session with one serving stack (llama.cpp, Qwen2.5-3B-Instruct 4-bit, temperature 0), so they differ only in the "
            "component named in the first column. *Answers with a number or name found in no source* checks every fact sentence "
            "against all the facts, NASA POWER and GBIF text of its island, with no use of citations. It is a lower bound on "
            "unsupported content: a sentence made only of words from the sources can still be wrong, and a model "
            "that quotes a true fact missing from the sources is counted too.",
            "",
            baseline_table(base, pools),
            "",
            "Reference rows from an earlier session (Ollama serving), included for context only; they are not matched with the table above:",
            "",
            baseline_table(refs, pools),
            "",
        ]
    dev = load_runs(RESULTS / "dev")
    if dev:
        parts += [
            "## Development set (tuned against: not a held out result)",
            "",
            "Runs on `eval/dev_questions.jsonl` (20 answerable questions and 5 refusal guards), used to choose changes. "
            "These numbers were optimised against and say little about unseen questions.",
            "",
            generation_table(dev),
            "",
        ]
    held = load_runs(RESULTS / "heldout")
    if held:
        parts += [
            "## Held out set (`eval/questions_heldout.jsonl`)",
            "",
            "30 questions written before any model output was seen: 20 for tuning (dev) and 10 sealed, each sealed "
            "configuration run once. Dev rows were tuned against; sealed rows are held out. The frozen 30 row with the "
            "check on is in the generation table above and is a regression check, because those questions were used "
            "for earlier diagnosis.",
            "",
        ]
        for split, title in (("dev", "Dev (20, tuned against)"), ("sealed", "Sealed (10, held out)")):
            rows = [r for r in held if r["meta"].get("split") == split]
            if rows:
                parts += [f"**{title}**", "", generation_table(rows, with_check=True), ""]
    notes = RESULTS / "NOTES.md"
    if notes.exists():
        parts += [notes.read_text(encoding="utf-8").strip(), ""]
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    md = build()
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "RESULTS.md").write_text(md, encoding="utf-8")
    print(md)
