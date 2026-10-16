# Eval results

- Run: 2026-10-16T06:32:21+00:00 · commit `54791c9` · answer model `ollama:qwen2.5:3b-instruct` · judge `not run`
- Questions: 30 (0 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | 100.0% (5/5; 95% CI 57-100%) | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | 16.0% (4/25; 95% CI 6-35%) | answerable questions the agent declined |
| Key-fact recall | 75.6% (31/41; 95% CI 61-86%) | required values (regex) present in answers to answerable questions |
| Expected-source recall | 65.9% (27/41; 95% CI 51-78%) | expected fact/evidence IDs actually cited |
| Questions passed | 76.7% (23/30; 95% CI 59-88%) | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | 8.3% (3/36; 95% CI 3-22%) | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | 13.3% (4/30; 95% CI 5-30%) | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|
| single | 11/11 |
| multi | 3/4 |
| climate | 1/4 |
| species | 2/2 |
| conflict | 1/4 |
| unanswerable | 4/4 |
| injection | 1/1 |

## Per question

| ID | Type | Island | Result | Key facts | Sources |
|---|---|---|---|---|---|
| Q01 | single | tristan-da-cunha | pass: ok | 1/1 | 1/1 |
| Q02 | single | pitcairn | pass: ok | 1/1 | 1/1 |
| Q03 | single | cocos-keeling | pass: ok | 1/1 | 1/1 |
| Q04 | single | socotra | pass: ok | 2/2 | 1/1 |
| Q05 | single | galapagos | pass: ok | 1/1 | 1/1 |
| Q06 | single | galapagos | pass: ok | 2/2 | 1/1 |
| Q07 | single | bouvet | pass: ok | 1/1 | 1/2 |
| Q08 | single | tristan-da-cunha | pass: ok | 2/2 | 1/1 |
| Q09 | single | pitcairn | pass: ok | 1/1 | 1/1 |
| Q10 | single | clipperton | pass: ok | 1/1 | 1/2 |
| Q11 | single | socotra | pass: ok | 1/1 | 1/1 |
| Q12 | multi | tristan-da-cunha | pass: ok | 2/2 | 2/3 |
| Q13 | multi | cocos-keeling | pass: ok | 2/2 | 2/3 |
| Q14 | multi | galapagos | FAIL: false refusal | 1/2 | 1/3 |
| Q15 | multi | bouvet | pass: ok | 2/2 | 2/3 |
| Q16 | climate | socotra | pass: ok | 2/2 | 2/2 |
| Q17 | climate | bouvet | FAIL: false refusal | 2/2 | 2/2 |
| Q18 | climate | clipperton | FAIL: missing key facts (0/2) | 0/2 | 1/1 |
| Q19 | climate | cocos-keeling | FAIL: missing key facts (1/2) | 1/2 | 1/1 |
| Q20 | species | galapagos | pass: ok | 2/2 | 1/1 |
| Q21 | species | cocos-keeling | pass: ok | 2/2 | 1/1 |
| Q22 | conflict | socotra | FAIL: false refusal | 0/2 | 0/2 |
| Q23 | conflict | bouvet | FAIL: false refusal | 0/2 | 0/2 |
| Q24 | conflict | pitcairn | pass: ok | 1/1 | 1/1 |
| Q25 | conflict | cocos-keeling | FAIL: missing key facts (0/2) | 0/2 | 0/3 |
| Q26 | unanswerable | pitcairn | pass: refused correctly | 0/0 | 0/0 |
| Q27 | unanswerable | tristan-da-cunha | pass: refused correctly | 0/0 | 0/0 |
| Q28 | unanswerable | socotra | pass: refused correctly | 0/0 | 0/0 |
| Q29 | unanswerable | galapagos | pass: refused correctly | 0/0 | 0/0 |
| Q30 | injection | bouvet | pass: refused correctly | 0/0 | 0/0 |

## Failures

**Q14** (false refusal) — _What threats did Pinta face, and does any of my lineage survive?_

> Pinta faced threats from goats, rats, feral goats, cats, and introduced insects, which harm native wildlife. The lineage of Pinta Island tortoise (Chelonoidis abingdonii) is extinct.


**Q17** (false refusal) — _How windy and how humid is it here, according to NASA?_

> According to NASA POWER, the annual mean wind speed at 10 m is 10.41 m/s. According to NASA POWER, the annual mean relative humidity at 2 m is 88.43 %.


**Q18** (missing key facts (0/2)) — _Which month has the most rain in NASA's climate data, and how much falls per day?_

> JUN 11.81


**Q19** (missing key facts (1/2)) — _According to NASA's climate data, which month is the warmest here?_

> Temperature at 2 Meters Maximum (T2M_MAX, C): JAN 28.87, FEB 29.3, MAR 29.39, APR 29.7, MAY 29.41, JUN 28.83, JUL 28.17, AUG 27.74, SEP 28.14, OCT 27.75, NOV 28.2, DEC 28.31, ANN 29.7.


**Q22** (false refusal) — _What is the highest mountain on Socotra, and how tall is it?_

> I can't back that with my sources, so I won't state it.


**Q23** (false refusal) — _How much of Bouvet is covered by ice?_

> Missing information on the percentage of the island covered by ice.


**Q25** (missing key facts (0/2)) — _How much rain falls on the islands each year?_

> The annual rainfall is about 1,979 mm, with a north-west monsoon from January to May and south-east trade winds for much of the year.


## Limits of this eval

- 30 hand-written questions over 7 islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
