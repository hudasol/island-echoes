"""Paired comparison of two stored runs over the same questions, plus a breakdown of validator failures.

    python -m eval.compare eval/results/a.json eval/results/b.json

Two runs on the same questions are paired data, so a difference in false refusals or passes is tested
with an exact McNemar test on the questions where the runs disagree. Interval overlap alone is too blunt
for 25 questions.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval import metrics  # noqa: E402
from eval.run_eval import DEV_QUESTIONS, QUESTIONS, load_questions  # noqa: E402


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, p)


ISSUE_KINDS = [
    ("no citation", r"has no citation"),
    ("cited an ID that was not retrieved", r"not retrieved"),
    ("number not in cited evidence", r"numbers not in cited"),
    ("name not in cited evidence", r"^name not in cited"),
    ("voice sentence carried digits or names", r"voice sentence contains"),
    ("voice sentence too long", r"voice sentence longer"),
    ("voice sentence cited a source", r"voice sentence must not cite"),
]


def issue_breakdown(run: dict) -> Counter:
    """Count first-attempt validator issues by kind (one sentence can have several)."""
    out: Counter = Counter()
    for r in run["records"]:
        for i in r.get("raw_issues", []):
            for issue in i["issues"]:
                kind = next((k for k, pat in ISSUE_KINDS if re.search(pat, issue)), "other")
                out[kind] += 1
    return out


def per_question(run: dict, questions: dict[str, dict]) -> dict[str, metrics.QuestionScore]:
    return {
        r["id"]: metrics.score_question(questions[r["id"]], r)
        for r in run["records"]
        if "error" not in r and r["id"] in questions
    }


def compare(a: dict, b: dict, questions: dict[str, dict]) -> str:
    sa, sb = per_question(a, questions), per_question(b, questions)
    common = sorted(set(sa) & set(sb))
    answerable = [i for i in common if not questions[i]["should_refuse"]]
    la, lb = a["meta"].get("label", "A"), b["meta"].get("label", "B")
    lines = [f"Paired comparison on {len(common)} questions answered without error in both runs ({la} against {lb}).", ""]
    lines += ["| Measure | " + la + " | " + lb + " | changed for the better / worse | exact McNemar p |", "|---|---|---|---|---|"]

    def row(name: str, ids: list[str], good) -> None:
        ka = sum(1 for i in ids if good(sa[i]))
        kb = sum(1 for i in ids if good(sb[i]))
        better = sum(1 for i in ids if good(sb[i]) and not good(sa[i]))
        worse = sum(1 for i in ids if good(sa[i]) and not good(sb[i]))
        lines.append(f"| {name} | {ka}/{len(ids)} | {kb}/{len(ids)} | {better} / {worse} | {mcnemar_exact(better, worse):.3f} |")

    row("answerable questions answered (not falsely refused)", answerable, lambda s: s.detail != "false refusal")
    row("questions passed", common, lambda s: s.passed)
    refuse = [i for i in common if questions[i]["should_refuse"]]
    row("unanswerable questions refused correctly", refuse, lambda s: s.passed)
    lines += ["", "First-attempt validator issues by kind (a sentence can have more than one):", ""]
    ba, bb = issue_breakdown(a), issue_breakdown(b)
    lines += ["| Issue | " + la + " | " + lb + " |", "|---|---|---|"]
    for k in [k for k, _ in ISSUE_KINDS] + ["other"]:
        if ba[k] or bb[k]:
            lines.append(f"| {k} | {ba[k]} | {bb[k]} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    a, b = (json.loads(Path(p).read_text(encoding="utf-8")) for p in argv)
    path = DEV_QUESTIONS if a["meta"].get("questions_file") == DEV_QUESTIONS.name else QUESTIONS
    questions = {q["id"]: q for q in load_questions(path=path)}
    print(compare(a, b, questions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
