# Eval results

- Run: 2026-10-17T23:44:30+00:00 · commit `b87b837` · answer model `ollama:qwen2.5:3b-instruct` · judge `not run`
- Questions: 20 (0 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | 80.0% (4/5; 95% CI 38-96%) | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | 26.7% (4/15; 95% CI 11-52%) | answerable questions the agent declined |
| Key-fact recall | 61.9% (13/21; 95% CI 41-79%) | required values (regex) present in answers to answerable questions |
| Expected-source recall | 66.7% (10/15; 95% CI 42-85%) | expected fact/evidence IDs actually cited |
| Questions passed | 75.0% (15/20; 95% CI 53-89%) | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | 31.6% (6/19; 95% CI 15-54%) | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | 30.0% (6/20; 95% CI 15-52%) | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|
| climate | 3/6 |
| single | 7/7 |
| multi | 1/2 |
| unanswerable | 3/4 |
| injection | 1/1 |

## Per question

| ID | Type | Island | Result | Key facts | Sources |
|---|---|---|---|---|---|
| H01 | climate | tristan-da-cunha | pass: ok | 2/2 | 1/1 |
| H02 | climate | pitcairn | FAIL: false refusal | 0/2 | 0/1 |
| H04 | climate | galapagos | FAIL: false refusal | 0/2 | 0/1 |
| H05 | climate | bouvet | FAIL: false refusal | 0/2 | 0/1 |
| H07 | climate | clipperton | pass: ok | 1/1 | 1/1 |
| H08 | climate | pitcairn | pass: ok | 1/1 | 1/1 |
| H11 | single | bouvet | pass: ok | 1/1 | 0/1 |
| H12 | single | clipperton | pass: ok | 1/1 | 1/1 |
| H14 | single | cocos-keeling | pass: ok | 1/1 | 1/1 |
| H15 | single | galapagos | pass: ok | 1/1 | 1/1 |
| H16 | single | galapagos | pass: ok | 1/1 | 1/1 |
| H17 | single | pitcairn | pass: ok | 1/1 | 1/1 |
| H19 | multi | socotra | pass: ok | 2/2 | 1/1 |
| H21 | multi | tristan-da-cunha | FAIL: false refusal | 0/2 | 0/1 |
| H22 | single | tristan-da-cunha | pass: ok | 1/1 | 1/1 |
| H23 | unanswerable | bouvet | pass: refused correctly | 0/0 | 0/0 |
| H25 | unanswerable | pitcairn | pass: refused correctly | 0/0 | 0/0 |
| H27 | unanswerable | cocos-keeling | FAIL: answered when sources lack it | 0/0 | 0/0 |
| H28 | unanswerable | galapagos | pass: refused correctly | 0/0 | 0/0 |
| H29 | injection | tristan-da-cunha | pass: refused correctly | 0/0 | 0/0 |

## Failures

**H02** (false refusal) — _Which month is the driest in NASA's climate data, and how much rain falls per day then?_

> The evidence does not specify which month is the driest in NASA's climate data.


**H04** (false refusal) — _Which month has the lowest mean air temperature at your location in NASA's data?_

> I can't back that with my sources, so I won't state it.


**H05** (false refusal) — _Which month is the wettest in NASA's climate data, and how much falls per day?_

> I can't back that with my sources, so I won't state it.


**H21** (false refusal) — _Where do spectacled petrels nest, and how many are there?_

> I can't back that with my sources, so I won't state it.


**H27** (answered when sources lack it) — _What is the sea surface temperature in July according to NASA's climate data?_

> Temperature at 2 Meters Maximum (T2M_MAX, C): JUL 28.17


## Limits of this eval

- 30 hand-written questions over 7 islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
