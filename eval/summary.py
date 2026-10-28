"""Compact evaluation numbers for the operations page, written to data/evaluation.json.

    python -m eval.summary          regenerate data/evaluation.json from eval/results

The page reads only this file, so what it shows is exactly what the stored runs contain.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.retrieval_eval import PAIRS, paired_hit5

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"
OUT = ROOT / "data" / "evaluation.json"

SYSTEM_LABEL = {
    "refuse-all": "Always refuse",
    "closed-book": "Model alone, no sources",
    "unvalidated": "Retrieval and model, no validator",
    "full": "Retrieval, model and validator",
}
SYSTEM_ORDER = list(SYSTEM_LABEL)
METRICS = ("hit@1", "hit@5", "mrr", "ndcg5")


def retrieval() -> dict:
    res = json.loads((RESULTS / "retrieval.json").read_text(encoding="utf-8"))
    out: dict = {}
    for name, by_mode in res["sets"].items():
        rows = []
        for mode, d in by_mode.items():
            s = d["summary"]
            rows.append({"mode": mode, **{m: {"mean": s[m]["mean"], "ci": s[m]["ci95"]} for m in METRICS}})
        entry: dict = {"n": next(iter(by_mode.values()))["summary"]["n"], "modes": rows}
        if name == "heldout":
            entry["paired"] = [x for x in (paired_hit5(by_mode, a, b) for a, b in PAIRS) if x]
        out[name] = entry
    return out


def baselines() -> list[dict]:
    rows = []
    for path in sorted((RESULTS / "baselines").glob("*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        meta, s = run["meta"], run["summary"]
        system = meta.get("system", "full")
        rows.append({
            "system": system,
            "label": SYSTEM_LABEL.get(system, system),
            "model": meta.get("answer_model"),
            "retrieval": meta.get("retrieval_mode") if system in ("full", "unvalidated") else None,
            "questions": s["questions"],
            "passed": s["questions_passed"],
            "false_refusals": s["false_refusals"],
            "refusal_accuracy": s["refusal_accuracy"],
            "key_fact_recall": s["key_fact_recall"],
            "commit": str(meta.get("commit", ""))[:7],
        })
    rows.sort(key=lambda r: SYSTEM_ORDER.index(r["system"]) if r["system"] in SYSTEM_ORDER else 99)
    return rows


def build() -> dict:
    return {"retrieval": retrieval(), "baselines": baselines()}


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
