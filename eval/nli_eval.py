"""Measure what an entailment check adds to the grounding validator (preregistration 3, item 5.4).

    python -m eval.nli_eval --run eval/results/v3/qwen25-3b-full.json --questions eval/v3/test.jsonl \
        --out eval/results/v3/nli.json [--label]

Takes every fact sentence of the model's first attempt that cites evidence, and records:
  validator   whether the word and number validator accepted it
  nli         probability that the cited evidence entails it (cross-encoder/nli-deberta-v3-xsmall, Apache 2.0)
  labeller    a second opinion from a different local model (Phi 3.5 mini, MIT) asked whether the evidence supports it
There is no human label here. Agreement is between three automatic judges, and says so in the output.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NLI_DIR = Path("/tmp/claude-0/models/nli")
LABELLER = "Phi-3.5-mini-instruct-Q4_K_M.gguf"
THRESHOLD = 0.5


def gather(run: dict, qs: dict[str, dict], retriever) -> list[dict]:
    rows = []
    for rec in run["records"]:
        q = qs.get(rec["id"])
        if not q or not rec.get("llm_called") or "error" in rec:
            continue
        res = retriever.search(q["island"], q["question"], q.get("creature"))
        ev = {e.id: e for e in res.evidence}
        bad = {i["text"] for i in rec.get("raw_issues", [])}
        for n, s in enumerate(rec.get("raw_sentences", [])):
            cites = [c for c in s["cites"] if c in ev]
            if s["kind"] != "fact" or not cites:
                continue
            rows.append({"q": rec["id"], "n": n, "sentence": s["text"], "cites": cites,
                         "premise": " ".join(ev[c].text for c in cites), "validator_ok": s["text"] not in bad})
    return rows


def kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--label", action="store_true", help="also ask the second labeller (slow on CPU)")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    from app.chat.nli import Entailment
    from app.config import Settings
    from app.data.islands import IslandStore
    from app.data.sources import SourceStore
    from app.retrieval.factory import build_retriever

    st = Settings(anthropic_api_key=None, telemetry=False, source_ttl_days=36500,
                  cache_dir=Path(tempfile.mkdtemp(prefix="ie-nli-")), retrieval_mode="hybrid")
    islands = IslandStore.load(st.islands_dir)
    retriever = build_retriever(st, islands, SourceStore(st, islands, http=object()))
    qs = {json.loads(line)["id"]: json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines() if line.strip()}
    run = json.loads(args.run.read_text(encoding="utf-8"))
    rows = gather(run, qs, retriever)
    if args.limit:
        rows = rows[: args.limit]

    nli = Entailment(NLI_DIR)
    t0 = time.perf_counter()
    for r in rows:
        r["nli"] = round(nli.score(r["premise"], r["sentence"])["entailment"], 4)
    per_ms = 1000 * (time.perf_counter() - t0) / max(1, len(rows))

    if args.label:
        from eval.v3.llm_util import ask, load

        llm = load(LABELLER, 3072)
        schema = {"type": "object", "properties": {"supported": {"type": "boolean"}}, "required": ["supported"]}
        system = "You check claims against evidence. Answer supported=true only if every number, name and claim in the sentence is stated in the evidence."
        for r in rows:
            user = f"Evidence:\n{r['premise'][:2400]}\n\nSentence: {r['sentence']}\nIs the sentence fully supported by the evidence?"
            try:
                r["labeller_ok"] = bool(ask(llm, system, user, schema, 30)["supported"])
            except Exception:  # noqa: BLE001
                r["labeller_ok"] = None

    val = [r["validator_ok"] for r in rows]
    ent = [r["nli"] >= THRESHOLD for r in rows]
    out = {
        "judges": "all automatic; no human label", "threshold": THRESHOLD, "sentences": len(rows),
        "validator_rejected": val.count(False), "nli_not_entailed": ent.count(False),
        "validator_vs_nli": {"agree": sum(a == b for a, b in zip(val, ent, strict=True)), "kappa": round(kappa(val, ent), 3),
                             "validator_ok_nli_no": sum(a and not b for a, b in zip(val, ent, strict=True)),
                             "validator_no_nli_ok": sum((not a) and b for a, b in zip(val, ent, strict=True))},
        "nli_ms_per_sentence": round(per_ms, 1),
    }
    lab = [r for r in rows if r.get("labeller_ok") is not None]
    if lab:
        L = [r["labeller_ok"] for r in lab]
        V = [r["validator_ok"] for r in lab]
        E = [r["nli"] >= THRESHOLD for r in lab]
        out["labelled"] = len(lab)
        out["labeller_unsupported"] = L.count(False)
        out["labeller_vs_validator"] = {"agree": sum(a == b for a, b in zip(L, V, strict=True)), "kappa": round(kappa(L, V), 3)}
        out["labeller_vs_nli"] = {"agree": sum(a == b for a, b in zip(L, E, strict=True)), "kappa": round(kappa(L, E), 3)}
        both = [not (v and e) for v, e in zip(V, E, strict=True)]
        out["labeller_flagged_by_validator"] = sum((not l_) and (not v) for l_, v in zip(L, V, strict=True))
        out["labeller_flagged_by_nli"] = sum((not l_) and (not e) for l_, e in zip(L, E, strict=True))
        out["labeller_flagged_by_either"] = sum((not l_) and b for l_, b in zip(L, both, strict=True))
        out["accepted_by_both_but_labeller_unsupported"] = sum((not l_) and not b for l_, b in zip(L, both, strict=True))
    args.out.write_text(json.dumps({"summary": out, "rows": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
