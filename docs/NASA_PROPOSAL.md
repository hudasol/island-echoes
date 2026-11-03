# Proposal: Island Echoes as a cited, offline capable learning and field reference built on NASA open data

Island Echoes is an independent open source project. It is not a NASA product, and nothing here implies endorsement or sponsorship by NASA or any NASA centre. It uses NASA open data under the terms those services publish.

## 1. Purpose

Learners and field staff increasingly ask language models about places they cannot visit. General models answer fluently without sources, and for remote islands the gaps are large. Island Echoes tests a narrower design: every statement must point to a source a reader can open, a question the sources do not cover must be declined, and the whole system must run on modest hardware without a paid service. NASA POWER climatology and NASA GIBS imagery supply the environmental context, and GBIF supplies species records.

## 2. What exists today (version 1.2)

| Item | Value |
|---|---|
| Islands, creatures | 7 islands, 8 creatures (endangered or extinct) |
| Library | 474 sourced facts from 93 web hosts and 99 publishers; each has a link, publisher, retrieval date and confidence label |
| NASA data used | POWER 2001 to 2020 monthly climatology per island grid cell; GIBS imagery layers on the globe |
| Interface | 3D globe, library search without a model, optional cited chat, Arabic and English with right to left layout, offline shell |
| Educator and sharing | One page educator sheet per island, a shareable field report page and image card per creature, public read only API |
| Quality gates | 348 automated tests with a 90 percent coverage gate, accessibility checks with zero violations in each scripted state, data validation, container build |

The library page, the API and the field report show the same cited facts.

## 3. Evidence, with its limits

All figures come from stored runs in `eval/results/` and are regenerated into `docs/RESULTS.md`. The preregistration was committed before any system ran on the sealed questions.

* Retrieval on 58 held out paraphrased questions: the correct fact is in the top five for 90 percent with hybrid retrieval (95 percent interval 81 to 97).
* A sealed set of 150 questions (synthetic, written by a local model, with constructed answers) was run on a 3 billion parameter model on two CPU cores. With the validator, 54 percent of 140 scored questions passed and 40 percent of answerable questions were declined; without the validator, 65 percent passed and 10 percent were declined. The validator trades helpfulness for fewer unsupported statements and the trade is large on this model.
* Two measures designed to reduce the cost, a source sentence fallback and a deterministic climate route, did not meet their preregistered rules and are off by default. The climate route answered all 28 scored climate questions correctly but also answered four questions about places not in the library from another island's table; this was fixed afterwards and is reported as post hoc.
* Eight of twelve preregistered predictions were wrong. They are listed in `docs/OVERNIGHT_REPORT.md`.

Limits stated plainly: questions are synthetic and the second labeller is a model, so the results overstate performance on real questions; the models tested are small; no study with learners or field staff has been done; the library covers seven islands.

## 4. Proposed pilot

Four to six weeks with one educator group and, if available, one field or monitoring team.

1. Replace synthetic questions with real ones collected with consent, and label a sample with two human readers.
2. Extend the library to further islands, adding a fact only when a source fetched at the time supports it, with the same schema.
3. Add NASA POWER and sea surface temperature trends as observational context, labelled as observation and not attribution of cause.
4. Measure time to a correct cited answer, refusals that users judge wrong, and use offline.

Outputs: a pilot report with intervals, the questions and labels, and an updated library. Cost: free tools and openly licensed models only.

## 5. Risks

| Risk | Handling |
|---|---|
| Unsupported statements | Validator checks citations, numbers and names; measured, not eliminated |
| Over refusal | Measured on every run; source sentence fallback available |
| Stale or weak sources | Retrieval dates, confidence labels, a freshness check that fails after 120 days |
| Misreading data as local weather | Every climate value is described as a grid cell of about 55 by 70 km |

## 6. Acknowledgements

We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), operated by NASA/GSFC/Earth Science Data and Information System (ESDIS). These data were obtained from the NASA Langley Research Center (LaRC) POWER Project, funded through the NASA Earth Science/Applied Science Program. Species records come from GBIF.org. Newsreader and IBM Plex are used under the SIL Open Font License. The code is released under the MIT licence.
