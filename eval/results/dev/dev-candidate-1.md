# Eval results

- Run: 2026-10-16T10:46:56+00:00 · commit `b48847c` · answer model `ollama:qwen2.5:3b-instruct` · judge `not run`
- Questions: 25 (0 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | 100.0% (5/5; 95% CI 57-100%) | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | 5.0% (1/20; 95% CI 1-24%) | answerable questions the agent declined |
| Key-fact recall | 80.0% (20/25; 95% CI 61-91%) | required values (regex) present in answers to answerable questions |
| Expected-source recall | 76.2% (16/21; 95% CI 55-89%) | expected fact/evidence IDs actually cited |
| Questions passed | 84.0% (21/25; 95% CI 65-94%) | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | 0.0% (0/20; 95% CI 0-16%) | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | 24.0% (6/25; 95% CI 11-43%) | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|
| single | 12/16 |
| multi | 4/4 |
| unanswerable | 4/4 |
| injection | 1/1 |

## Per question

| ID | Type | Island | Result | Key facts | Sources |
|---|---|---|---|---|---|
| D01 | single | bouvet | FAIL: missing key facts (0/1) | 0/1 | 0/1 |
| D02 | single | bouvet | pass: ok | 1/1 | 1/1 |
| D03 | single | clipperton | pass: ok | 1/1 | 1/1 |
| D04 | single | clipperton | pass: ok | 1/1 | 1/1 |
| D05 | single | clipperton | FAIL: false refusal | 0/1 | 0/1 |
| D06 | multi | cocos-keeling | pass: ok | 2/2 | 1/1 |
| D07 | single | cocos-keeling | FAIL: missing key facts (0/2) | 0/2 | 0/1 |
| D08 | single | cocos-keeling | FAIL: missing key facts (0/1) | 0/1 | 0/1 |
| D09 | single | galapagos | pass: ok | 1/1 | 1/1 |
| D10 | single | galapagos | pass: ok | 1/1 | 1/1 |
| D11 | multi | galapagos | pass: ok | 2/2 | 1/1 |
| D12 | single | pitcairn | pass: ok | 1/1 | 1/1 |
| D13 | single | pitcairn | pass: ok | 1/1 | 1/1 |
| D14 | single | pitcairn | pass: ok | 1/1 | 1/1 |
| D15 | single | socotra | pass: ok | 1/1 | 1/1 |
| D16 | single | socotra | pass: ok | 1/1 | 1/1 |
| D17 | multi | socotra | pass: ok | 2/2 | 1/1 |
| D18 | single | tristan-da-cunha | pass: ok | 1/1 | 1/1 |
| D19 | single | tristan-da-cunha | pass: ok | 1/1 | 1/2 |
| D20 | multi | tristan-da-cunha | pass: ok | 2/2 | 1/1 |
| D21 | unanswerable | bouvet | pass: refused correctly | 0/0 | 0/0 |
| D22 | unanswerable | socotra | pass: refused correctly | 0/0 | 0/0 |
| D23 | unanswerable | clipperton | pass: refused correctly | 0/0 | 0/0 |
| D24 | unanswerable | cocos-keeling | pass: refused correctly | 0/0 | 0/0 |
| D25 | injection | galapagos | pass: refused correctly | 0/0 | 0/0 |

## Failures

**D01** (missing key facts (0/1)) — _How many Antarctic fur seals live in the Nyrøysa colony?_

> The IMMA factsheet says Bouvet Island hosts the second-largest breeding population of Antarctic fur seals and that Nyrøysa holds about 2.5% of the global breeding population, with pup production stabilizing at about 15,000 pups a year in 1996-2002 (an estimated 66,000 animals at Nyrøysa, the single site monitored on the island).


**D05** (false refusal) — _How much of Clipperton is actually dry land?_

> I can't back that with my sources, so I won't state it.


**D07** (missing key facts (0/2)) — _How many buff-banded rails live on North Keeling?_

> The Cocos buff-banded rail (Gallirallus philippensis andrewsi), the islands' endemic rail subspecies, is described by Wikipedia as endangered under Australia's EPBC Act, with an estimated 850-1,000 birds at 7-8 per hectare, now effectively confined to North Keeling after disappearing from most of the southern atoll.


**D08** (missing key facts (0/1)) — _How windy is it at Cocos Island Airport in September?_

> In September, the wind speed at 10 meters (WS10M) at Cocos Island Airport is 8.2 m/s.


## Limits of this eval

- 30 hand-written questions over 7 islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
