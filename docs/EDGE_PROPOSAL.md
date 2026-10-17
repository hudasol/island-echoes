# Proposal: auditable, citation grounded answers over remote environmental data

## 1. The problem

Field teams, analysts and decision makers increasingly ask language models about places they cannot easily
visit: remote islands, offshore installations, protected reserves. General chat models answer fluently and
without traceable sources, and in this setting a confident invented figure is worse than no answer. Three
requirements follow. Every factual statement must point to a source a reviewer can open. A question the sources do
not cover must be declined rather than guessed. The system must run where connectivity is poor or absent, on
hardware the organisation controls, and it must leave a record that an overseer can audit.

## 2. What exists today

Island Echoes is a working, open source prototype that meets these requirements on a small public domain: seven
remote islands, 469 facts each linked to a public source, NASA POWER climatology and GBIF species records. It is
deliberately modest in scope so that every number in it can be checked.

| Layer | What it does | Status |
|---|---|---|
| Sources | Fact files with source URL, publisher, retrieval date and a confidence label; satellite climate and species snapshots committed for offline use | Built |
| Retrieval | Keyword (BM25), dense (bge-small, runs on CPU) or a fusion of both, scoped to one site | Built, measured |
| Answer model | One interface over a baseline that uses no model, a local model (Ollama, llama.cpp), hosted open models and a commercial API | Built |
| Grounding validator | Every fact sentence must cite retrieved evidence; numbers and names must appear in the cited text; failures are repaired once, then dropped | Built, measured |
| Telemetry | One row per request: stage latencies, model, tokens, validator outcome; question text is not stored by default | Built |
| Evaluation | Gold retrieval sets, a 30 question end to end set, a separate development set, stored runs with commit and data hash, a preregistration | Built |

The whole pipeline runs offline on a laptop CPU with a 3 billion parameter open model. No paid service is needed.

## 3. Measured results

All numbers are from `docs/RESULTS.md`; brackets are 95% intervals. The question sets are small, so the
intervals are wide, and the 30 question set has been used for development, so its numbers are regression checks
rather than held out benchmarks.

| Measure | Result |
|---|---|
| Retrieval, 58 held out questions: a correct fact in the top 5 | keyword 0.81 [0.71-0.91]; hybrid 0.90 [0.81-0.97] |
| End to end, 30 questions, local 3B model, keyword retrieval: passed | 23/30, 77% [59-88] |
| Same, hybrid retrieval: passed | 20/30, 67% [49-81] |
| Unanswerable or injection questions correctly declined | 5/5 in both runs [57-100] |
| Answerable questions declined | 4/25 keyword, 16% [6-35]; 5/25 hybrid, 20% [9-39] |
| Model's fact sentences rejected on the first attempt by the validator | 3/36, 8% [3-22] keyword; 5/34, 15% [6-30] hybrid |
| Baseline with no model (quotes the top sources) | 15/30 passed; declines 1/5 unanswerable questions |

What these show. A 3 billion parameter model running offline on a laptop CPU answered roughly three quarters of the
questions with every factual sentence cited and checked, and declined every question the sources do not cover,
which the baseline without a model cannot do. The difference between keyword and hybrid retrieval is not
significant (paired test, p = 0.375 on passes). The validator rejected between 8 and 15% of the model's first
attempts before anything was shown.

What they do not show. A prompt change that lowered refusals (5 to 3 of 25, p = 0.688) was reverted because a
manual reading found one more contradicted sentence among the changed answers. The errors that remain quote a
number that is in the cited table but belongs to another month or row, which the mechanical validator cannot see.
Timings were taken on a heavily loaded laptop and are not a performance claim.

## 4. What is not yet proven

- **Semantic faithfulness.** The validator checks citations, numbers and names mechanically. A wrong claim built
  from correct words passes. No judge model or human rating has been run on the local model's answers.
- **Scale.** 469 facts over seven sites. Retrieval quality and latency on tens of thousands of documents are
  untested.
- **Users.** No study with analysts or field staff has been done; usefulness is assumed, not measured.
- **Independent labels.** Gold answers were written by one person.
- **Larger local models.** Only a 3 billion parameter model was run, on CPU. Larger open models on suitable
  hardware may answer more often; this has not been measured.

## 5. Risks

| Risk | Mitigation in place | Remaining exposure |
|---|---|---|
| Model states an unsupported figure | Validator drops it before display; telemetry counts every rejection | A figure from the wrong row of a cited table passes; a manual reading found such sentences in both runs checked |
| Too many refusals make the tool unhelpful | Measured per run; changes tested on a separate development set first | 16 to 20% of answerable questions declined |
| Source facts are wrong or outdated | Source link, retrieval date and confidence on every fact; link checks weekly | Facts resting on a single secondary source |
| Prompt injection through the question | Questions and evidence are treated as data; injection cases are in the eval | Small test set |
| Latency on modest hardware | Retrieval in milliseconds; model time dominates and is reported | Tens of seconds per answer on a laptop CPU |

## 6. Roadmap

**Stage 1, eight weeks: harden on a partner dataset.** Ingest one real environmental or site dataset chosen with
the partner, with its own document identifiers. Recruit a second annotator for gold answers. Add an entailment
check (a small local natural language inference model) beside the mechanical validator. Exit criterion: on a held
out set written by the partner, hallucination proxy and false refusal rate each reported with intervals narrower
than 15 points.

**Stage 2, twelve weeks: oversight and deployment.** Run on partner hardware with a larger open model. Persistent
telemetry store and a reviewer view that shows, for any answer, the evidence, the rejected sentences and the
reasons. A short study with five to ten analysts on real questions. Exit criterion: reviewers can trace every
displayed claim to a source in under one minute, measured in the study.

**Stage 3, twelve weeks: scale and integration.** Extend to many sites and live data feeds, with freshness checks
and change logs. Integrate with the partner's existing systems through the existing HTTP API. Exit criterion:
agreed latency and accuracy targets met on the partner's held out set at the partner's data volume.

## 7. The ask

A pilot of Stage 1 with one team, consisting of:

1. one environmental or site dataset the partner is able to share for the pilot, with a named data owner;
2. a domain expert for about two days to write and label 100 held out questions;
3. access to one workstation with a recent GPU, or an equivalent on premises virtual machine, for model
   comparisons;
4. a review meeting at the end of the eight weeks to decide on Stage 2 against the exit criterion above.

No endorsement by any organisation is claimed or implied. The prototype and all results are public at
https://github.com/hudasol/island-echoes.
