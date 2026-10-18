# Eval results

- Run: 2026-10-18T00:05:56+00:00 · commit `c5caef1-dirty` · answer model `ollama:qwen2.5:3b-instruct` · judge `not run`
- Questions: 0 (1 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | n/a | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | n/a | answerable questions the agent declined |
| Key-fact recall | n/a | required values (regex) present in answers to answerable questions |
| Expected-source recall | n/a | expected fact/evidence IDs actually cited |
| Questions passed | n/a | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | n/a | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | n/a | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|

## Per question

| ID | Type | Island | Result | Key facts | Sources |
|---|---|---|---|---|---|
## Limits of this eval

- 30 hand-written questions over 7 islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
