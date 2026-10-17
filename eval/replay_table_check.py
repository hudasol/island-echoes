"""Apply the label aware number check (app/chat/tables.py) to fact sentences stored in earlier runs.

    python -m eval.replay_table_check            # writes eval/results/table_check_replay.md and prints it

No model is called. Each stored fact sentence (first attempts and shown answers) is checked against the text of the
evidence it cites. Every rejection is listed so it can be read against its evidence and classified by hand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.chat.tables import parse_rows, table_issues  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402
from app.data.sources import SourceStore  # noqa: E402

RUNS = [
    ("A", "eval/results/qwen25-3b-ollama-bm25.json", "eval/questions.jsonl"),
    ("B", "eval/results/qwen25-3b-ollama-hybrid.json", "eval/questions.jsonl"),
    ("C", "eval/results/qwen25-3b-ollama-hybrid-fixed.json", "eval/questions.jsonl"),
    ("D0", "eval/results/dev/dev-baseline.json", "eval/dev_questions.jsonl"),
    ("D1", "eval/results/dev/dev-candidate-1.json", "eval/dev_questions.jsonl"),
]


def evidence_texts(islands: IslandStore, sources: SourceStore, island: str) -> dict[str, str]:
    isl = islands.get(island)
    out = {f.id: f.statement for f in isl.facts}
    out.update({e.id: e.text for e in sources.power_evidence(isl)})
    for c in isl.creatures:
        out.update({e.id: e.text for e in sources.gbif_evidence(isl, c.slug)})
    return out


def replay() -> tuple[list[dict], dict[str, int]]:
    s = get_settings()
    islands = IslandStore.load(s.islands_dir)
    sources = SourceStore(s, islands, http=object())
    rejections, counts = [], {"sentences": 0, "with_table_evidence": 0}
    for run, path, qfile in RUNS:
        qs = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / qfile).read_text(encoding="utf-8").splitlines() if line.strip()}
        for rec in json.loads((ROOT / path).read_text(encoding="utf-8"))["records"]:
            if "error" in rec:
                continue
            ev = evidence_texts(islands, sources, qs[rec["id"]]["island"])
            seen = set()
            for stage, sents in (("first attempt", rec.get("raw_sentences", [])), ("shown", rec.get("sentences", []))):
                for sent in sents:
                    if sent["kind"] != "fact" or (sent["text"], stage) in seen:
                        continue
                    seen.add((sent["text"], stage))
                    cited = "\n".join(ev[c] for c in sent["cites"] if c in ev)
                    counts["sentences"] += 1
                    if parse_rows(cited):
                        counts["with_table_evidence"] += 1
                    for issue in table_issues(sent["text"], cited):
                        rejections.append({"run": run, "id": rec["id"], "stage": stage, "text": sent["text"], "issue": issue})
    return rejections, counts


def to_markdown(rejections: list[dict], counts: dict[str, int]) -> str:
    lines = [
        "# Replay of the label aware number check on stored runs",
        "",
        f"Fact sentences checked: {counts['sentences']} (first attempts and shown answers, runs A, B, C, D0, D1); "
        f"citing a NASA POWER table: {counts['with_table_evidence']}; rejected: {len(rejections)}.",
        "",
        "| Run | Question | Stage | Sentence | Issue |",
        "|---|---|---|---|---|",
    ]
    for r in rejections:
        lines.append(f"| {r['run']} | {r['id']} | {r['stage']} | {r['text'].replace('|', '/')} | {r['issue']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    rej, cnt = replay()
    md = to_markdown(rej, cnt)
    (ROOT / "eval" / "results" / "table_check_replay.md").write_text(md, encoding="utf-8")
    print(md)
