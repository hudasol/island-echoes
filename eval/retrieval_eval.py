"""Retrieval eval: how well do bm25, dense and hybrid rank the gold facts?

    python -m eval.retrieval_eval [--modes bm25,dense,hybrid] [--out eval/results/retrieval.json]

Sets (all with gold fact ids):
  heldout - eval/retrieval_gold.jsonl, written after the keyword retriever was tuned, paraphrased on purpose
  dev     - the fact-id questions of eval/questions.jsonl (the keyword retriever was developed against these)
Gold ids are single-annotator. Live NASA POWER / GBIF items are routed by intent, not ranked, so they
are not part of this ranking eval.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402
from app.data.retrieval import Retriever  # noqa: E402
from app.data.sources import SourceStore  # noqa: E402
from app.retrieval.dense import DenseIndex, fact_texts  # noqa: E402

KS = (1, 3, 5, 12)


def load_sets() -> dict[str, list[dict]]:
    held = [json.loads(line) for line in (ROOT / "eval" / "retrieval_gold.jsonl").read_text().splitlines() if line.strip()]
    dev = []
    for line in (ROOT / "eval" / "questions.jsonl").read_text().splitlines():
        q = json.loads(line)
        gold = [i for i in q["expected_ids"] if not i.startswith(("POWER-", "GBIF-"))]
        if gold and not q["should_refuse"]:
            dev.append({"id": q["id"], "island": q["island"], "creature": q.get("creature"),
                        "question": q["question"], "gold": gold, "split": "dev"})
    return {"heldout": held, "dev": dev}


def ndcg(ranked: list[str], gold: set[str], k: int) -> float:
    dcg = sum(1 / math.log2(r + 1) for r, i in enumerate(ranked[:k], 1) if i in gold)
    ideal = sum(1 / math.log2(r + 1) for r in range(1, min(len(gold), k) + 1))
    return dcg / ideal if ideal else 0.0


def score_question(ranked: list[str], gold: set[str]) -> dict:
    first = next((r for r, i in enumerate(ranked, 1) if i in gold), None)
    out = {"mrr": 1 / first if first else 0.0, "ndcg5": ndcg(ranked, gold, 5)}
    for k in KS:
        top = set(ranked[:k])
        out[f"hit@{k}"] = float(bool(top & gold))
        out[f"recall@{k}"] = len(top & gold) / len(gold)
    return out


def bootstrap_ci(vals: list[float], n: int = 2000, seed: int = 7) -> tuple[float, float]:
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(vals, k=len(vals))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def summarize(per_q: list[dict]) -> dict:
    out = {"n": len(per_q)}
    for m in per_q[0]:
        vals = [q[m] for q in per_q]
        lo, hi = bootstrap_ci(vals)
        out[m] = {"mean": round(statistics.fmean(vals), 4), "ci95": [round(lo, 4), round(hi, 4)]}
    return out


def build_retriever(modes: list[str]) -> Retriever:
    s = get_settings()
    store = IslandStore.load(s.islands_dir)
    sources = SourceStore(s, store)
    dense = DenseIndex.load(s.embeddings_path, fact_texts(store)) if any(m != "bm25" for m in modes) else None
    return Retriever(store, sources, dense=dense, mode="hybrid" if dense else "bm25")


def run(modes: list[str]) -> dict:
    retr = build_retriever(modes)
    sets = load_sets()
    result: dict = {"modes": modes, "sets": {}}
    for name, qs in sets.items():
        result["sets"][name] = {}
        for mode in modes:
            per_q, detail = [], []
            for q in qs:
                ranked, _ = retr.rank(q["island"], q["question"], q.get("creature"), mode=mode)
                ids = [e.id for e in ranked]
                sc = score_question(ids, set(q["gold"]))
                per_q.append(sc)
                detail.append({"id": q["id"], "gold": q["gold"], "top5": ids[:5], "hit@5": sc["hit@5"]})
            result["sets"][name][mode] = {"summary": summarize(per_q), "questions": detail}
    return result


def _cell(m: dict) -> str:
    return f"{m['mean']:.2f} [{m['ci95'][0]:.2f}-{m['ci95'][1]:.2f}]"


def to_markdown(res: dict) -> str:
    lines = []
    for name, by_mode in res["sets"].items():
        n = next(iter(by_mode.values()))["summary"]["n"]
        lines += [f"**{name}** (n={n})", "", "| mode | hit@1 | hit@3 | hit@5 | recall@12 | MRR | nDCG@5 |", "|---|---|---|---|---|---|---|"]
        for mode, d in by_mode.items():
            s = d["summary"]
            cells = [_cell(s[m]) for m in ("hit@1", "hit@3", "hit@5", "recall@12", "mrr", "ndcg5")]
            lines.append(f"| {mode} | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="bm25,dense,hybrid")
    ap.add_argument("--out", default=str(ROOT / "eval" / "results" / "retrieval.json"))
    a = ap.parse_args()
    res = run(a.modes.split(","))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(to_markdown(res))


if __name__ == "__main__":
    main()
