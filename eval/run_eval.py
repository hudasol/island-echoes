"""Run the 30-question eval against the real pipeline and report groundedness / hallucination.

    python -m eval.run_eval --judge                # answer with the Anthropic API, then judge (needs ANTHROPIC_API_KEY)
    python -m eval.run_eval --from-run eval/results/latest.json   # re-score a saved run, no API calls
    python -m eval.run_eval --ids Q01,Q26          # subset
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.chat.llm import AnthropicAnswerLLM, LLMError  # noqa: E402
from app.chat.service import ChatService  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402
from app.data.retrieval import Retriever  # noqa: E402
from app.data.sources import SourceStore  # noqa: E402

from . import metrics  # noqa: E402
from .judge import AnthropicJudge  # noqa: E402

QUESTIONS = Path(__file__).with_name("questions.jsonl")
RESULTS = Path(__file__).with_name("results")


def load_questions(ids: set[str] | None = None) -> list[dict]:
    qs = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [q for q in qs if not ids or q["id"] in ids]


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def answer_one(service: ChatService, q: dict) -> dict:
    last: Exception | None = None
    for _attempt in range(2):
        t0 = time.time()
        try:
            r = service.respond(q["island"], q["question"], q.get("creature"))
            return {
                "id": q["id"],
                "answered": r.answered,
                "sentences": [{"text": s.text, "kind": s.kind, "cites": s.cites} for s in r.sentences],
                "missing": r.missing,
                "cited_ids": r.cited_ids,
                "retrieved_ids": [e.id for e in r.retrieved],
                "raw_sentences": r.raw_sentences,
                "raw_issues": r.raw_issues,
                "rejected": r.rejected,
                "repaired": r.repaired,
                "llm_called": r.llm_called,
                "seconds": round(time.time() - t0, 2),
            }
        except LLMError as exc:
            last = exc
            time.sleep(2)
    return {"id": q["id"], "error": str(last)}


def judge_one(judge: AnthropicJudge, service: ChatService, q: dict, rec: dict) -> dict:
    ev = {e.id: e.text for e in service.retriever.search(q["island"], q["question"], q.get("creature")).evidence}
    cited = {i: ev[i] for s in rec["sentences"] for i in s["cites"] if i in ev}
    last: Exception | None = None
    for _ in range(2):
        try:
            return judge.grade(q["question"], rec["sentences"], cited)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2)
    return {"error": str(last), "verdicts": {}}


def render_markdown(meta: dict, summary: dict, scores: list[metrics.QuestionScore], questions: dict[str, dict], recs: dict[str, dict]) -> str:
    def row(label: str, key: str, note: str = "") -> str:
        v = summary[key]
        return f"| {label} | {metrics.pct(v['k'], v['n'])} | {note} |"

    judged = summary["judged_questions"] > 0
    lines = [
        "# Eval results",
        "",
        f"- Run: {meta['timestamp']} · commit `{meta['commit']}` · answer model `{meta['answer_model']}` · judge `{meta['judge_model'] or 'not run'}`",
        f"- Questions: {summary['questions']} ({meta['errored']} errored and excluded) · data snapshots as committed",
        "",
        "## Headline",
        "",
        "| Metric | Result | How it is computed |",
        "|---|---|---|",
    ]
    if judged:
        lines += [
            row("Groundedness", "groundedness", "fact sentences the judge found fully supported by their cited evidence"),
            row("Hallucination rate", "hallucination_rate", "fact sentences judged unsupported or contradicted by their cited evidence"),
            row("Partially supported", "partially_supported", "right claim, but a detail is not in the cited evidence"),
            row("Answers containing a hallucination", "answers_with_hallucination", "answers with an unsupported fact sentence, plus unanswerable questions answered anyway"),
        ]
    else:
        lines.append("| Groundedness / hallucination | not run | re-run with `--judge` |")
    lines += [
        row("Refusal accuracy", "refusal_accuracy", "unanswerable questions where the agent said the sources lack it and asserted no forbidden value"),
        row("False refusals", "false_refusals", "answerable questions the agent declined"),
        row("Key-fact recall", "key_fact_recall", "required values (regex) present in answers to answerable questions"),
        row("Expected-source recall", "expected_source_recall", "expected fact/evidence IDs actually cited"),
        *([row("Conflicts reported", "conflicts_reported", "judge: both values given and sources said to differ (conflict questions)")] if judged else []),
        row("Questions passed", "questions_passed", "all checks for that question"),
        "",
        "## Validator effect",
        "",
        "| Metric | Result | Meaning |",
        "|---|---|---|",
        row("Fact sentences failing checks on first attempt", "validator_first_pass_failures", "before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence"),
        row("Answers that needed a repair retry", "repaired_answers", "one retry with the failures listed"),
        "",
        "## By question type",
        "",
        "| Type | Passed |",
        "|---|---|",
    ]
    for t in dict.fromkeys(s.type for s in scores):
        ts = [s for s in scores if s.type == t]
        lines.append(f"| {t} | {sum(1 for s in ts if s.passed)}/{len(ts)} |")
    lines += ["", "## Per question", "", "| ID | Type | Island | Result | Key facts | Sources |", "|---|---|---|---|---|---|"]
    for s in scores:
        q = questions[s.id]
        lines.append(
            f"| {s.id} | {s.type} | {q['island']} | {'pass' if s.passed else 'FAIL'}: {s.detail} | "
            f"{s.key_hits}/{s.key_total} | {s.expected_hit}/{s.expected_total} |"
        )
    fails = [s for s in scores if not s.passed]
    if fails:
        lines += ["", "## Failures", ""]
        for s in fails:
            q, rec = questions[s.id], recs[s.id]
            lines += [f"**{s.id}** ({s.detail}) — _{q['question']}_", "", "> " + (metrics.answer_text(rec) or "(no answer)").replace("\n", " "), ""]
            reasons = rec.get("judge", {}).get("reasons", {})
            for i, why in reasons.items():
                v = rec["judge"]["verdicts"].get(i)
                if v in ("unsupported", "contradicted", "partially_supported"):
                    lines.append(f"- sentence {i}: {v} — {why}")
            lines.append("")
    lines += [
        "## Limits of this eval",
        "",
        "- 30 hand-written questions over 7 islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.",
        "- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.",
        "- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.",
        "- Number and name checks are mechanical; number words (\"two\") and subtle causal claims are only caught by the judge.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true", help="grade fact sentences with the LLM judge")
    ap.add_argument("--from-run", type=Path, help="re-score a saved run JSON without calling the API for answers")
    ap.add_argument("--ids", help="comma-separated question IDs")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, default=RESULTS / "latest")
    args = ap.parse_args(argv)

    settings = get_settings()
    ids = set(args.ids.split(",")) if args.ids else None
    questions = {q["id"]: q for q in load_questions(ids)}
    islands = IslandStore.load(settings.islands_dir)
    retriever = Retriever(islands, SourceStore(settings, islands))

    if args.from_run:
        saved = json.loads(args.from_run.read_text(encoding="utf-8"))
        recs = {r["id"]: r for r in saved["records"] if r["id"] in questions}
        meta = saved["meta"]
        service = ChatService(islands, retriever, None)
    else:
        if not settings.anthropic_api_key:
            print("ANTHROPIC_API_KEY is not set (put it in .env). Use --from-run to re-score a saved run.", file=sys.stderr)
            return 2
        llm = AnthropicAnswerLLM(settings.anthropic_api_key, settings.anthropic_model)
        service = ChatService(islands, retriever, llm)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(lambda q: answer_one(service, q), questions.values()))
        recs = {r["id"]: r for r in results}
        meta = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "commit": git_sha(),
            "answer_model": settings.anthropic_model,
            "judge_model": None,
        }

    if args.judge:
        if not settings.anthropic_api_key:
            print("--judge needs ANTHROPIC_API_KEY.", file=sys.stderr)
            return 2
        judge = AnthropicJudge(settings.anthropic_api_key, settings.judge_model)
        todo = [(q, recs[q["id"]]) for q in questions.values() if "error" not in recs.get(q["id"], {"error": 1})]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for (_q, rec), j in zip(todo, pool.map(lambda t: judge_one(judge, service, *t), todo), strict=True):
                rec["judge"] = j
        meta["judge_model"] = settings.judge_model

    errored = [i for i, r in recs.items() if "error" in r]
    meta["errored"] = len(errored)
    good = {i: r for i, r in recs.items() if "error" not in r}
    scores = [metrics.score_question(questions[i], good[i]) for i in questions if i in good]
    conflict = {
        s.id: (
            None
            if not questions[s.id].get("expects_conflict") or not good[s.id].get("judge")
            else good[s.id]["judge"].get("states_conflict") == "yes"
        )
        for s in scores
    }
    summary = metrics.summarise(scores, conflict)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_json = args.out.with_suffix(".json")
    out_md = args.out.with_suffix(".md")
    out_json.write_text(json.dumps({"meta": meta, "summary": summary, "records": list(recs.values())}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = render_markdown(meta, summary, scores, questions, good)
    out_md.write_text(md, encoding="utf-8")
    print(md)
    if errored:
        print(f"ERRORED (excluded): {', '.join(errored)}", file=sys.stderr)
    return 1 if errored else 0


if __name__ == "__main__":
    raise SystemExit(main())
