# Eval results

- Run: 2026-10-18T00:14:43+00:00 · commit `c5caef1` · answer model `ollama:qwen2.5:3b-instruct` · judge `not run`
- Questions: 30 (0 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | 100.0% (5/5; 95% CI 57-100%) | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | 24.0% (6/25; 95% CI 11-43%) | answerable questions the agent declined |
| Key-fact recall | 65.9% (27/41; 95% CI 51-78%) | required values (regex) present in answers to answerable questions |
| Expected-source recall | 51.2% (21/41; 95% CI 36-66%) | expected fact/evidence IDs actually cited |
| Questions passed | 66.7% (20/30; 95% CI 49-81%) | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | 20.0% (7/35; 95% CI 10-36%) | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | 23.3% (7/30; 95% CI 12-41%) | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|
| single | 9/11 |
| multi | 1/4 |
| climate | 2/4 |
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
| Q09 | single | pitcairn | FAIL: false refusal | 0/1 | 0/1 |
| Q10 | single | clipperton | FAIL: missing key facts (0/1) | 0/1 | 0/2 |
| Q11 | single | socotra | pass: ok | 1/1 | 1/1 |
| Q12 | multi | tristan-da-cunha | pass: ok | 2/2 | 2/3 |
| Q13 | multi | cocos-keeling | FAIL: false refusal | 0/2 | 0/3 |
| Q14 | multi | galapagos | FAIL: false refusal | 1/2 | 1/3 |
| Q15 | multi | bouvet | FAIL: false refusal | 0/2 | 0/3 |
| Q16 | climate | socotra | pass: ok | 2/2 | 2/2 |
| Q17 | climate | bouvet | pass: ok | 2/2 | 2/2 |
| Q18 | climate | clipperton | FAIL: false refusal | 0/2 | 0/1 |
| Q19 | climate | cocos-keeling | FAIL: missing key facts (1/2) | 1/2 | 1/1 |
| Q20 | species | galapagos | pass: ok | 2/2 | 1/1 |
| Q21 | species | cocos-keeling | pass: ok | 2/2 | 1/1 |
| Q22 | conflict | socotra | FAIL: false refusal | 0/2 | 0/2 |
| Q23 | conflict | bouvet | FAIL: missing key facts (1/2) | 1/2 | 0/2 |
| Q24 | conflict | pitcairn | pass: ok | 1/1 | 1/1 |
| Q25 | conflict | cocos-keeling | FAIL: missing key facts (1/2) | 1/2 | 1/3 |
| Q26 | unanswerable | pitcairn | pass: refused correctly | 0/0 | 0/0 |
| Q27 | unanswerable | tristan-da-cunha | pass: refused correctly | 0/0 | 0/0 |
| Q28 | unanswerable | socotra | pass: refused correctly | 0/0 | 0/0 |
| Q29 | unanswerable | galapagos | pass: refused correctly | 0/0 | 0/0 |
| Q30 | injection | bouvet | pass: refused correctly | 0/0 | 0/0 |

## Failures

**Q09** (false refusal) — _How many of you are left?_

> I can't back that with my sources, so I won't state it.


**Q10** (missing key facts (0/1)) — _Why does Clipperton matter to silvertip sharks?_

> The silvertip shark (Carcharhinus albimarginatus) is listed as Vulnerable and is a qualifying species for the Clipperton shark and ray area.


**Q13** (false refusal) — _How did the Cocos (Keeling) Islands become Australian territory, and what did residents vote in 1984?_

> I can't back that with my sources, so I won't state it.


**Q14** (false refusal) — _What threats did Pinta face, and does any of my lineage survive?_

> No living or captive Pinta Island tortoises have been recorded. The Pinta Island tortoise is listed as Extinct on the IUCN Red List. Wikipedia reports that goats introduced to Pinta in 1958 stripped vegetation. The mangrove finch, with no recent records on Fernandina, is listed as Critically Endangered. The Galápagos penguin, with about 90% of the birds living on Fernandina and the west coast of Isabela, is listed as Endangered.


**Q15** (false refusal) — _Who claimed Bouvet for Norway, and how is the island protected today?_

> I can't back that with my sources, so I won't state it.


**Q18** (false refusal) — _Which month has the most rain in NASA's climate data, and how much falls per day?_

> I can't back that with my sources, so I won't state it.


**Q19** (missing key facts (1/2)) — _According to NASA's climate data, which month is the warmest here?_

> Temperature at 2 Meters Maximum (T2M_MAX, C): JAN 28.87, FEB 29.3, MAR 29.39, APR 29.7, MAY 29.41, JUN 28.83, JUL 28.17, AUG 27.74, SEP 28.14, OCT 27.75, NOV 28.2, DEC 28.31, ANN 29.7.


**Q22** (false refusal) — _What is the highest mountain on Socotra, and how tall is it?_

> I can't back that with my sources, so I won't state it.


**Q23** (missing key facts (1/2)) — _How much of Bouvet is covered by ice?_

> About 93% of Bouvetøya is permanent ice; ice-free ground includes the Nyrøysa platform (about 700 m long and 25-40 m high) and 150-350 m cliffs, with only non-vascular vegetation on coastal cliffs, capes, boulder beaches, nunatak ridges and the summit plateau.


**Q25** (missing key facts (1/2)) — _How much rain falls on the islands each year?_

> The annual rainfall at Cocos Island Airport is about 1,970 mm per year.


## Limits of this eval

- 30 hand-written questions over 7 islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
