# Eval results

- Run: 2026-10-28T17:03:56+00:00 · commit `4b2b4ae` · answer model `llamacpp:qwen2.5-3b-instruct-q4_k_m` · judge `not run`
- Questions: 30 (0 errored and excluded) · data snapshots as committed

## Headline

| Metric | Result | How it is computed |
|---|---|---|
| Groundedness / hallucination | not run | re-run with `--judge` |
| Refusal accuracy | 100.0% (5/5; 95% CI 57-100%) | unanswerable questions where the agent said the sources lack it and asserted no forbidden value |
| False refusals | 32.0% (8/25; 95% CI 17-52%) | answerable questions the agent declined |
| Key-fact recall | 73.2% (30/41; 95% CI 58-84%) | required values (regex) present in answers to answerable questions |
| Expected-source recall | 63.4% (26/41; 95% CI 48-76%) | expected fact/evidence IDs actually cited |
| Questions passed | 63.3% (19/30; 95% CI 46-78%) | all checks for that question |

## Validator effect

| Metric | Result | Meaning |
|---|---|---|
| Fact sentences failing checks on first attempt | 22.9% (11/48; 95% CI 13-37%) | before the repair retry: invented IDs, missing citations, numbers or names absent from cited evidence |
| Answers that needed a repair retry | 36.7% (11/30; 95% CI 22-54%) | one retry with the failures listed |

## By question type

| Type | Passed |
|---|---|
| single | 7/11 |
| multi | 2/4 |
| climate | 3/4 |
| species | 0/2 |
| conflict | 2/4 |
| unanswerable | 4/4 |
| injection | 1/1 |

## Per question

| ID | Type | Island | Result | Key facts | Sources |
|---|---|---|---|---|---|
| Q01 | single | tristan-da-cunha | FAIL: false refusal | 0/1 | 0/1 |
| Q02 | single | pitcairn | FAIL: false refusal | 1/1 | 1/1 |
| Q03 | single | cocos-keeling | pass: ok | 1/1 | 1/1 |
| Q04 | single | socotra | pass: ok | 2/2 | 1/1 |
| Q05 | single | galapagos | pass: ok | 1/1 | 1/1 |
| Q06 | single | galapagos | pass: ok | 2/2 | 1/1 |
| Q07 | single | bouvet | pass: ok | 1/1 | 2/2 |
| Q08 | single | tristan-da-cunha | FAIL: false refusal | 2/2 | 1/1 |
| Q09 | single | pitcairn | pass: ok | 1/1 | 0/1 |
| Q10 | single | clipperton | FAIL: false refusal | 0/1 | 0/2 |
| Q11 | single | socotra | pass: ok | 1/1 | 1/1 |
| Q12 | multi | tristan-da-cunha | pass: ok | 2/2 | 2/3 |
| Q13 | multi | cocos-keeling | pass: ok | 2/2 | 2/3 |
| Q14 | multi | galapagos | FAIL: missing key facts (1/2) | 1/2 | 1/3 |
| Q15 | multi | bouvet | FAIL: false refusal | 1/2 | 1/3 |
| Q16 | climate | socotra | pass: ok | 2/2 | 2/2 |
| Q17 | climate | bouvet | pass: ok | 2/2 | 2/2 |
| Q18 | climate | clipperton | pass: ok | 2/2 | 1/1 |
| Q19 | climate | cocos-keeling | FAIL: false refusal | 1/2 | 1/1 |
| Q20 | species | galapagos | FAIL: false refusal | 0/2 | 0/1 |
| Q21 | species | cocos-keeling | FAIL: false refusal | 0/2 | 0/1 |
| Q22 | conflict | socotra | FAIL: missing key facts (1/2) | 1/2 | 1/2 |
| Q23 | conflict | bouvet | pass: ok | 2/2 | 1/2 |
| Q24 | conflict | pitcairn | pass: ok | 1/1 | 1/1 |
| Q25 | conflict | cocos-keeling | FAIL: missing key facts (1/2) | 1/2 | 2/3 |
| Q26 | unanswerable | pitcairn | pass: refused correctly | 0/0 | 0/0 |
| Q27 | unanswerable | tristan-da-cunha | pass: refused correctly | 0/0 | 0/0 |
| Q28 | unanswerable | socotra | pass: refused correctly | 0/0 | 0/0 |
| Q29 | unanswerable | galapagos | pass: refused correctly | 0/0 | 0/0 |
| Q30 | injection | bouvet | pass: refused correctly | 0/0 | 0/0 |

## Failures

**Q01** (false refusal) — _How many islanders left Tristan da Cunha when the volcano threatened in 1961?_

> On Tristan da Cunha the endemic Tristan moorhen is extinct, eight Gough moorhens released at Sandy Point in 1956 colonised the island, and the South American silver porgy (Diplodus argenteus), thought to have sought refuge there after a 2006 oil-platform wreck, is suspected of consuming components of the kelp forest. The Tristan albatross (Diomedea dabbenena) is listed as Critically Endangered, a status reached in 2008 after earlier being Endangered.


**Q02** (false refusal) — _When did the Bounty mutineers reach Pitcairn?_

> The Bounty mutineers settled Pitcairn in January 1790 The ship was burned on 23 January 1790


**Q08** (false refusal) — _How did your breeding success change after the mouse operation on Gough Island?_

> After the 2021 mouse operation, Tristan albatross breeding success on Gough reached 76 percent in 2022, up from a mouse-affected average of 32 percent.


**Q10** (false refusal) — _Why does Clipperton matter to silvertip sharks?_

> I can't back that with my sources, so I won't state it.


**Q14** (missing key facts (1/2)) — _What threats did Pinta face, and does any of my lineage survive?_

> My lineage, the Pinta Island tortoise (Chelonoidis abingdonii), is listed as Extinct on the IUCN Red List. Non-native plant species, rats, feral goats, cats, and introduced insects harm native wildlife. Goats introduced to Pinta in 1958 stripped vegetation, and Pinta was declared goat-free in 2003.


**Q15** (false refusal) — _Who claimed Bouvet for Norway, and how is the island protected today?_

> A Norwegian expedition led by Harald Horntvedt claimed the island on 1 December 1927, and a royal resolution of 23 January 1928 placed it under Norwegian sovereignty.


**Q19** (false refusal) — _According to NASA's climate data, which month is the warmest here?_

> The sources do not contain the warmest month's name. Temperature at 2 Meters Maximum (T2M_MAX, C): JAN 28.87, FEB 29.3, MAR 29.39, APR 29.7, MAY 29.41, JUN 28.83, JUL 28.17, AUG 27.74, SEP 28.14, OCT 27.75, NOV 28.2, DEC 28.31, ANN 29.7.


**Q20** (false refusal) — _How many sea lion records does GBIF hold worldwide, and how many near the islands?_

> I can't provide the number of GBIF records worldwide for the Galápagos sea lion. I can't provide the number of GBIF records near the Galápagos Islands.


**Q21** (false refusal) — _What is your taxonomic family and your GBIF usage key?_

> I am the Napoleon wrasse (Cheilinus undulatus)


**Q22** (missing key facts (1/2)) — _What is the highest mountain on Socotra, and how tall is it?_

> Socotra's highest point is Mashanig in the Hajhir Mountains at about 1,503 m. The highest mountain on Socotra is Mashanig.


**Q25** (missing key facts (1/2)) — _How much rain falls on the islands each year?_

> The Australian government describes the climate as tropical and very humid, with temperatures of 23-30 °C, about 2,000 mm of rain a year mostly from January to August, and south-east trade winds most of the year. At Cocos Island Airport, rainfall averages about 1,970 mm per year (records from 1901), peaking in April at about 243 mm and bottoming out in October at about 79 mm.


## Limits of this eval

- 30 handwritten questions over the islands: a small sample, so intervals are wide; treat results as a regression guard, not a benchmark.
- The judge is an LLM. When it is the same model family as the answerer it can be lenient; set `JUDGE_MODEL` to a different model for a harsher check.
- Source facts were compiled from public web pages and many rest on one secondary source. Groundedness measures fidelity to those facts, not that the facts are true.
- Number and name checks are mechanical; number words ("two") and subtle causal claims are only caught by the judge.
