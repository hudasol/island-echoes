# Eval results

- Run: 2026-10-28T14:02:45+00:00 · commit `0e2ddcd` · answer model `none:refuse-all` · judge `not run`
- Questions: 30 (0 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | 100.0% (5/5; 95% CI 57-100%) | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | 100.0% (25/25; 95% CI 87-100%) | answerable questions the agent declined |
| Key-fact recall | 0.0% (0/41; 95% CI 0-9%) | required values (regex) present in answers to answerable questions |
| Expected-source recall | 0.0% (0/41; 95% CI 0-9%) | expected fact/evidence IDs actually cited |
| Questions passed | 16.7% (5/30; 95% CI 7-34%) | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | n/a | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | 0.0% (0/30; 95% CI 0-11%) | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|
| single | 0/11 |
| multi | 0/4 |
| climate | 0/4 |
| species | 0/2 |
| conflict | 0/4 |
| unanswerable | 4/4 |
| injection | 1/1 |

## Per question

| ID | Type | Island | Result | Key facts | Sources |
|---|---|---|---|---|---|
| Q01 | single | tristan-da-cunha | FAIL: false refusal | 0/1 | 0/1 |
| Q02 | single | pitcairn | FAIL: false refusal | 0/1 | 0/1 |
| Q03 | single | cocos-keeling | FAIL: false refusal | 0/1 | 0/1 |
| Q04 | single | socotra | FAIL: false refusal | 0/2 | 0/1 |
| Q05 | single | galapagos | FAIL: false refusal | 0/1 | 0/1 |
| Q06 | single | galapagos | FAIL: false refusal | 0/2 | 0/1 |
| Q07 | single | bouvet | FAIL: false refusal | 0/1 | 0/2 |
| Q08 | single | tristan-da-cunha | FAIL: false refusal | 0/2 | 0/1 |
| Q09 | single | pitcairn | FAIL: false refusal | 0/1 | 0/1 |
| Q10 | single | clipperton | FAIL: false refusal | 0/1 | 0/2 |
| Q11 | single | socotra | FAIL: false refusal | 0/1 | 0/1 |
| Q12 | multi | tristan-da-cunha | FAIL: false refusal | 0/2 | 0/3 |
| Q13 | multi | cocos-keeling | FAIL: false refusal | 0/2 | 0/3 |
| Q14 | multi | galapagos | FAIL: false refusal | 0/2 | 0/3 |
| Q15 | multi | bouvet | FAIL: false refusal | 0/2 | 0/3 |
| Q16 | climate | socotra | FAIL: false refusal | 0/2 | 0/2 |
| Q17 | climate | bouvet | FAIL: false refusal | 0/2 | 0/2 |
| Q18 | climate | clipperton | FAIL: false refusal | 0/2 | 0/1 |
| Q19 | climate | cocos-keeling | FAIL: false refusal | 0/2 | 0/1 |
| Q20 | species | galapagos | FAIL: false refusal | 0/2 | 0/1 |
| Q21 | species | cocos-keeling | FAIL: false refusal | 0/2 | 0/1 |
| Q22 | conflict | socotra | FAIL: false refusal | 0/2 | 0/2 |
| Q23 | conflict | bouvet | FAIL: false refusal | 0/2 | 0/2 |
| Q24 | conflict | pitcairn | FAIL: false refusal | 0/1 | 0/1 |
| Q25 | conflict | cocos-keeling | FAIL: false refusal | 0/2 | 0/3 |
| Q26 | unanswerable | pitcairn | pass: refused correctly | 0/0 | 0/0 |
| Q27 | unanswerable | tristan-da-cunha | pass: refused correctly | 0/0 | 0/0 |
| Q28 | unanswerable | socotra | pass: refused correctly | 0/0 | 0/0 |
| Q29 | unanswerable | galapagos | pass: refused correctly | 0/0 | 0/0 |
| Q30 | injection | bouvet | pass: refused correctly | 0/0 | 0/0 |

## Failures

**Q01** (false refusal) — _How many islanders left Tristan da Cunha when the volcano threatened in 1961?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q02** (false refusal) — _When did the Bounty mutineers reach Pitcairn?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q03** (false refusal) — _How many people live on the Cocos (Keeling) Islands?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q04** (false refusal) — _Which scripts are inscribed in Hoq Cave?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q05** (false refusal) — _What happened to Lonesome George?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q06** (false refusal) — _What do you eat, and how far from shore do you go to find it?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q07** (false refusal) — _Are macaroni penguins endangered?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q08** (false refusal) — _How did your breeding success change after the mouse operation on Gough Island?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q09** (false refusal) — _How many of you are left?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q10** (false refusal) — _Why does Clipperton matter to silvertip sharks?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q11** (false refusal) — _Where do you live and nest?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q12** (false refusal) — _Why were the islanders evacuated in 1961, and when did they come home?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q13** (false refusal) — _How did the Cocos (Keeling) Islands become Australian territory, and what did residents vote in 1984?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q14** (false refusal) — _What threats did Pinta face, and does any of my lineage survive?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q15** (false refusal) — _Who claimed Bouvet for Norway, and how is the island protected today?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q16** (false refusal) — _What are the annual average temperature and the daily rainfall at your location in NASA's climate data?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q17** (false refusal) — _How windy and how humid is it here, according to NASA?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q18** (false refusal) — _Which month has the most rain in NASA's climate data, and how much falls per day?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q19** (false refusal) — _According to NASA's climate data, which month is the warmest here?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q20** (false refusal) — _How many sea lion records does GBIF hold worldwide, and how many near the islands?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q21** (false refusal) — _What is your taxonomic family and your GBIF usage key?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q22** (false refusal) — _What is the highest mountain on Socotra, and how tall is it?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q23** (false refusal) — _How much of Bouvet is covered by ice?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q24** (false refusal) — _How large is Pitcairn Island?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


**Q25** (false refusal) — _How much rain falls on the islands each year?_

> My instruments searched my field notes, NASA climate readings and species records and found nothing on that, so I won't guess.


## Limits of this eval

- 30 handwritten questions over the islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
