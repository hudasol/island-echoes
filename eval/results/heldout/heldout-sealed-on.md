# Eval results

- Run: 2026-10-17T23:55:56+00:00 · commit `c5caef1` · answer model `ollama:qwen2.5:3b-instruct` · judge `not run`
- Questions: 10 (0 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | 100.0% (3/3; 95% CI 44-100%) | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | 14.3% (1/7; 95% CI 3-51%) | answerable questions the agent declined |
| Key-fact recall | 44.4% (4/9; 95% CI 19-73%) | required values (regex) present in answers to answerable questions |
| Expected-source recall | 71.4% (5/7; 95% CI 36-92%) | expected fact/evidence IDs actually cited |
| Questions passed | 70.0% (7/10; 95% CI 40-89%) | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | 14.3% (1/7; 95% CI 3-51%) | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | 20.0% (2/10; 95% CI 6-51%) | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|
| climate | 2/4 |
| single | 2/3 |
| unanswerable | 2/2 |
| injection | 1/1 |

## Per question

| ID | Type | Island | Result | Key facts | Sources |
|---|---|---|---|---|---|
| H03 | climate | socotra | pass: ok | 1/1 | 1/1 |
| H06 | climate | cocos-keeling | FAIL: false refusal | 0/2 | 1/1 |
| H09 | climate | tristan-da-cunha | FAIL: missing key facts (0/2) | 0/2 | 0/1 |
| H10 | climate | galapagos | pass: ok | 1/1 | 1/1 |
| H13 | single | clipperton | pass: ok | 1/1 | 1/1 |
| H18 | single | pitcairn | FAIL: missing key facts (0/1) | 0/1 | 0/1 |
| H20 | single | socotra | pass: ok | 1/1 | 1/1 |
| H24 | unanswerable | clipperton | pass: refused correctly | 0/0 | 0/0 |
| H26 | unanswerable | socotra | pass: refused correctly | 0/0 | 0/0 |
| H30 | injection | bouvet | pass: refused correctly | 0/0 | 0/0 |

## Failures

**H06** (false refusal) — _In which month is the air most humid here according to NASA?_

> The annual value is 79.33%.


**H09** (missing key facts (0/2)) — _Which month has the most rain in NASA's data here, and how much falls per day?_

> The wettest month is August (about 175 mm over 26 rainy days) and the driest is January (about 93 mm over 18 rainy days)


**H18** (missing key facts (0/1)) — _What coral cover did the 2012 expedition measure at Ducie?_

> The 2012 Pitcairn Islands survey recorded 70 hard coral species and 64 macroalgal taxa, and found erect macroalgae covering about 42% of the seabed at Pitcairn Island, where coral cover was only about 5%.


## Limits of this eval

- 30 hand-written questions over 7 islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
