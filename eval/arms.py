"""Derive validator arms from one stored run, so every arm shares the same model generations.

    python -m eval.arms RUN.json --arm extractive --questions eval/v3/test.jsonl --out RUN-extractive.json

The model is called at most twice per question (first attempt, then one repair if a check failed) whatever happens
afterwards. A stored `full` run keeps both attempts, so the arms that differ only in what is shown can be replayed:

    unvalidated   the first attempt as it is, nothing checked or removed
    drop          the repaired attempt with failing sentences removed (the pipeline of version 1.1)
    extractive    the repaired attempt with failing fact sentences replaced by their cited source sentence

The replay is checked against a live run of the same service in tests/test_arms.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.chat.finalise import finalise  # noqa: E402
from app.chat.grounding import CheckedSentence  # noqa: E402

ARMS = ("unvalidated", "drop", "extractive")


def _checked(items: list[dict]) -> list[CheckedSentence]:
    return [CheckedSentence(text=i["text"], kind=i["kind"], cites=list(i["cites"]), issues=list(i.get("issues", []))) for i in items]


def derive(rec: dict, arm: str, evidence: dict, ranked: list, question: str) -> dict:
    """A copy of one stored record as it would have been shown under `arm`."""
    if "error" in rec or not rec.get("llm_called"):
        return dict(rec)
    out = dict(rec)
    if arm == "unvalidated":
        sentences = [{"text": s["text"], "kind": s["kind"], "cites": s["cites"]} for s in rec["raw_sentences"] if s["text"].strip()]
        out.update(
            sentences=sentences,
            answered=bool(rec["first_answered"]) and any(s["kind"] == "fact" for s in sentences),
            cited_ids=list(dict.fromkeys(c for s in sentences for c in s["cites"])),
            rejected=[], repaired=False,
        )
        return out
    items = rec["second_sentences"] if rec.get("repaired") else [{**s, "issues": []} for s in rec["raw_sentences"]]
    fin = finalise(_checked(items), bool(rec["model_answered"]), evidence, ranked, question, "extractive" if arm == "extractive" else "drop")
    sentences = [{"text": c.text, "kind": c.kind, "cites": c.cites} for c in fin.kept]
    has_fact = any(s["kind"] == "fact" for s in sentences)
    answered = bool(rec["model_answered"]) and has_fact
    if not has_fact and not any(s["kind"] == "voice" for s in sentences):
        from app.chat.service import DROPPED_LINE

        sentences = [{"text": DROPPED_LINE, "kind": "voice", "cites": []}]
    out.update(sentences=sentences, answered=answered, rejected=fin.dropped, replaced=fin.replaced,
               cited_ids=list(dict.fromkeys(c for s in sentences for c in s["cites"])))
    return out


def overlay_climate(rec: dict, tool, island, question: str) -> dict:
    """Replace the record with the tool's answer when the tool routes the question; otherwise keep it."""
    hit = tool.answer(island, question)
    if hit is None:
        return rec
    return {**rec, "answered": True, "sentences": hit.sentences, "cited_ids": hit.evidence_ids, "llm_called": False, "rejected": [],
            "repaired": False, "notes": [*rec.get("notes", []), f"climate tool: {hit.route}"], "llm_ms": 0.0}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--arm", choices=ARMS, required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--retrieval", default="hybrid")
    ap.add_argument("--climate", action="store_true", help="overlay the deterministic climate tool on questions it routes")
    args = ap.parse_args(argv)

    from app.config import get_settings
    from app.data.islands import IslandStore
    from app.data.sources import SourceStore
    from app.retrieval.factory import build_retriever

    settings = get_settings().model_copy(update={"retrieval_mode": args.retrieval})
    islands = IslandStore.load(settings.islands_dir)
    retriever = build_retriever(settings, islands, SourceStore(settings, islands))
    qs = {json.loads(line)["id"]: json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines() if line.strip()}
    saved = json.loads(args.run.read_text(encoding="utf-8"))
    tool = None
    if args.climate:
        from app.data.climate_tool import ClimateTool

        tool = ClimateTool(islands, retriever.sources)
    records = []
    for rec in saved["records"]:
        q = qs[rec["id"]]
        res = retriever.search(q["island"], q["question"], q.get("creature"))
        out = derive(rec, args.arm, {e.id: e for e in res.evidence}, res.evidence, " ".join(q["question"].split()))
        if tool is not None:
            out = overlay_climate(out, tool, islands.get(q["island"]), " ".join(q["question"].split()))
        records.append(out)
    meta = {**saved["meta"], "arm": args.arm, "derived_from": args.run.name, "label": args.out.stem, "climate_tool_overlay": bool(tool)}
    args.out.write_text(json.dumps({"meta": meta, "records": records}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {args.out} ({len(records)} records, arm {args.arm})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
