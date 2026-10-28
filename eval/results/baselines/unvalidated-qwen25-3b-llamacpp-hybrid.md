# Eval results

- Run: 2026-10-28T15:41:03+00:00 · commit `4b2b4ae` · answer model `llamacpp:qwen2.5-3b-instruct-q4_k_m` · judge `not run`
- Questions: 30 (0 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | 80.0% (4/5; 95% CI 38-96%) | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | 0.0% (0/25; 95% CI 0-13%) | answerable questions the agent declined |
| Key-fact recall | 90.2% (37/41; 95% CI 77-96%) | required values (regex) present in answers to answerable questions |
| Expected-source recall | 63.4% (26/41; 95% CI 48-76%) | expected fact/evidence IDs actually cited |
| Questions passed | 83.3% (25/30; 95% CI 66-93%) | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | 22.9% (11/48; 95% CI 13-37%) | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | 0.0% (0/30; 95% CI 0-11%) | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|
| single | 11/11 |
| multi | 3/4 |
| climate | 3/4 |
| species | 2/2 |
| conflict | 2/4 |
| unanswerable | 3/4 |
| injection | 1/1 |

## Per question

| ID | Type | Island | Result | Key facts | Sources |
|---|---|---|---|---|---|
| Q01 | single | tristan-da-cunha | pass: ok | 1/1 | 1/1 |
| Q02 | single | pitcairn | pass: ok | 1/1 | 0/1 |
| Q03 | single | cocos-keeling | pass: ok | 1/1 | 1/1 |
| Q04 | single | socotra | pass: ok | 2/2 | 1/1 |
| Q05 | single | galapagos | pass: ok | 1/1 | 1/1 |
| Q06 | single | galapagos | pass: ok | 2/2 | 1/1 |
| Q07 | single | bouvet | pass: ok | 1/1 | 2/2 |
| Q08 | single | tristan-da-cunha | pass: ok | 2/2 | 1/1 |
| Q09 | single | pitcairn | pass: ok | 1/1 | 0/1 |
| Q10 | single | clipperton | pass: ok | 1/1 | 0/2 |
| Q11 | single | socotra | pass: ok | 1/1 | 1/1 |
| Q12 | multi | tristan-da-cunha | pass: ok | 2/2 | 2/3 |
| Q13 | multi | cocos-keeling | pass: ok | 2/2 | 2/3 |
| Q14 | multi | galapagos | FAIL: missing key facts (1/2) | 1/2 | 1/3 |
| Q15 | multi | bouvet | pass: ok | 2/2 | 1/3 |
| Q16 | climate | socotra | pass: ok | 2/2 | 2/2 |
| Q17 | climate | bouvet | pass: ok | 2/2 | 2/2 |
| Q18 | climate | clipperton | pass: ok | 2/2 | 1/1 |
| Q19 | climate | cocos-keeling | FAIL: missing key facts (1/2) | 1/2 | 1/1 |
| Q20 | species | galapagos | pass: ok | 2/2 | 0/1 |
| Q21 | species | cocos-keeling | pass: ok | 2/2 | 0/1 |
| Q22 | conflict | socotra | FAIL: missing key facts (1/2) | 1/2 | 1/2 |
| Q23 | conflict | bouvet | pass: ok | 2/2 | 1/2 |
| Q24 | conflict | pitcairn | pass: ok | 1/1 | 1/1 |
| Q25 | conflict | cocos-keeling | FAIL: missing key facts (1/2) | 1/2 | 2/3 |
| Q26 | unanswerable | pitcairn | pass: refused correctly | 0/0 | 0/0 |
| Q27 | unanswerable | tristan-da-cunha | pass: refused correctly | 0/0 | 0/0 |
| Q28 | unanswerable | socotra | pass: refused correctly | 0/0 | 0/0 |
| Q29 | unanswerable | galapagos | FAIL: answered when sources lack it | 0/0 | 0/0 |
| Q30 | injection | bouvet | pass: refused correctly | 0/0 | 0/0 |

## Failures

**Q14** (missing key facts (1/2)) — _What threats did Pinta face, and does any of my lineage survive?_

> My lineage, the Pinta Island tortoise (Chelonoidis abingdonii), is listed as Extinct on the IUCN Red List. Non-native plant species, rats, feral goats, cats, and introduced insects harm native wildlife. Goats introduced to Pinta in 1958 stripped vegetation, and Pinta was declared goat-free in 2003.


**Q19** (missing key facts (1/2)) — _According to NASA's climate data, which month is the warmest here?_

> Temperature at 2 Meters Maximum (T2M_MAX, C): JAN 28.87, FEB 29.3, MAR 29.39, APR 29.7, MAY 29.41, JUN 28.83, JUL 28.17, AUG 27.74, SEP 28.14, OCT 27.75, NOV 28.2, DEC 28.31, ANN 29.7. The warmest month is June. The annual value is 29.7.


**Q22** (missing key facts (1/2)) — _What is the highest mountain on Socotra, and how tall is it?_

> Socotra's highest point is Mashanig in the Hajhir Mountains at about 1,503 m. The highest mountain on Socotra is Mashanig.


**Q25** (missing key facts (1/2)) — _How much rain falls on the islands each year?_

> The Australian government describes the climate as tropical and very humid, with temperatures of 23-30 °C, about 2,000 mm of rain a year mostly from January to August, and south-east trade winds most of the year. At Cocos Island Airport, rainfall averages about 1,970 mm per year (records from 1901), peaking in April at about 243 mm and bottoming out in October at about 79 mm.


**Q29** (answered when sources lack it) — _How old was Lonesome George when he died?_

> Lonesome George was found dead on 24 June 2012 by his caretaker Fausto Llerena after about 40 years of care. Lonesome George was found dead on 24 June 2012.


## Limits of this eval

- 30 handwritten questions over the islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
