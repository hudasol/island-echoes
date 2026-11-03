# Overnight report, version 1.2.0

Work done on 3 November 2026 (UTC). All commits are on `main`. Question and result files for the sealed evaluation are in `eval/v3/` and `eval/results/v3/`. Generated tables are in `docs/RESULTS.md`.

## 1. What was done

| Area | Outcome |
|---|---|
| Prior art and preregistration | `docs/research/PREREGISTRATION_3.md` committed with the question hashes before any sealed run. Three dated addenda. |
| Evaluation sets | 150 sealed synthetic test questions (112 answerable, 38 to refuse) and 55 development questions. Written by Qwen2.5 1.5B, labelled by Phi 3.5 mini. Old sets kept as regression. |
| Climate route | Deterministic answers for numeric NASA POWER questions. Answers 28 of 28 scored sealed climate questions. A defect (wrong island for places outside the library) was found by the sealed run and fixed afterwards. |
| Lossless validation | Extractive fallback arm against drop, derived offline from one stored generation per question. |
| More models | Qwen2.5 1.5B (50 questions) and 7B (30 questions), plus closed book 3B (50 questions). Models above 7B do not fit the 8 GB machine. |
| Claims rebuilt | README, `docs/EVALUATION.md`, `docs/RESULTS.md` regenerated from stored runs. |
| Data | `scripts/data_report.py` writes provenance tables into `docs/DATA.md`. Five Clipperton facts added from a French National Assembly report (469 to 474 facts). |
| Product | Arabic interface, educator sheets, shareable field reports, public read only API, offline shell, lazy globe bundle, Lighthouse budget in CI. |
| Operations | Six hourly uptime check, 120 day freshness check, `docs/OPERATIONS.md`. |
| Documents | `docs/NASA_PROPOSAL.md`, `docs/KNOWN_ISSUES.md`, this report. |
| Quality | Lint and mypy (on `app/`) clean, data validation passes, 348 tests at 92.4 percent coverage (gate 90), accessibility audit with zero violations in ten states. |

## 2. Predictions against results

Environment and method are in section 3. Intervals are 95 percent Wilson.

| ID | Prediction | Measured | Result |
|---|---|---|---|
| P1 | Drop arm pass rate 55 to 75% | 54% (75/140) [45-62] | miss, 1 point below |
| P2 | Drop arm false refusals 20 to 40% | 40.2% (41/102) [31-50] | miss by 0.2 points (an earlier draft divided by 112 and showed 37%; corrected, see KI-10) |
| P3 | Extractive lowers false refusals by 10 points or more, at most 12% remain | 34% (35/102), 6 points lower; paired test 6 to 0, p = 0.031 | miss |
| P4 | Extractive unsupported sentences: 0, at most 2 | 0 of 67 answers | hit |
| P5 | Extractive refusal accuracy at most 5 points below drop | 100% and 100% | hit |
| P6 | Closed book 3B pass rate 5 to 20% | 15% (7/46) | hit |
| P7 | Unvalidated: 3 to 12% of fact sentences unsupported, more than drop and extractive | 1% of answers (1/92) | miss (measured per answer, not per sentence, and far below the range) |
| P8 | Climate route answers 26 to 30 of 30 | 28 of 28 scored (2 sealed climate questions errored in the 3B generation and are not scored) | hit |
| P9 | Wrong month or row errors, model alone 3 to 9, with the route 0 | model alone: 12 answered but wrong or incomplete (unvalidated arm); route: 0 | miss on the first part, hit on the second; overall miss. Categories are an approximation: failures with missing key facts, not a count of wrong month errors only |
| P10 | Labeller agreement on supporting facts at least 85% | exact 66% (45/68), covers gold 85% (58/68), Jaccard 0.775 | miss, as predicted most likely |
| P11 | 7B beats 3B by at least 5 points | 14/27 and 14/27 on shared questions; one question each way, p = 1.0 | miss |
| P12 | 1.5B passes fewer than 3B by 5 to 25 points | 4/42 against 19/42, 36 points fewer | miss (direction right, size outside the range) |

Four hits and eight misses. The stated most likely failure (P10) failed; P11 was second most likely and also failed.

## 3. Pinned environment

| Item | Value |
|---|---|
| Machine | 2 vCPU, 8 GB RAM, Linux, no GPU |
| Python | 3.13.16; llama-cpp-python 0.3.36; fastapi 0.162.0; numpy 2.5.4; onnxruntime 1.31.1; tokenizers 0.23.3; Node 22.22.0 |
| Answer models | Qwen2.5 1.5B, 3B and 7B Instruct, Q4_K_M GGUF (Apache 2.0), temperature 0, JSON schema grammar |
| Second labeller | Phi 3.5 mini Instruct Q4_K_M (MIT) |
| Question writer | Qwen2.5 1.5B Instruct |
| Retrieval | Hybrid BM25 and bge-small, 8 facts shown, 2 CPU threads |
| Entailment check | cross-encoder nli-deberta-v3-xsmall, quantised ONNX (Apache 2.0) |
| Seeds | test 20261103, development 20261104 |
| Speed | about 150 to 230 seconds per question for 3B, measured while other work shared the two cores |

Sealed question hashes: `eval/v3/SHA256SUMS`.

## 4. Decisions and why

* **Defaults unchanged.** The extractive fallback and the climate route failed their preregistered keep rules, so the 1.1 behaviour remains the default. Both stay selectable by setting.
* **Climate route fix.** The wrong island answer was a defect, not tuning, so it was fixed and reported as post hoc (Addendum 3). The preregistered rows stay as run.
* **Denominators.** Report rows use the questions each run scored; ten questions errored in the 3B run (malformed JSON) and are excluded from the model rows.
* **Subsets.** The 1.5B, 7B and closed book runs use fixed subsets chosen before any result was read (Addendum 2), because the 3B run alone took about six hours.
* **Entailment check stays off.** It flagged 62 of 117 sentences as not entailed against 12 for the validator, agreed with the second labeller at kappa 0.14 (validator 0.47). Too strict to turn on. The sample is below the planned 200 because the 3B run produced no more first attempt fact sentences.
* **New islands not added.** The island count of seven is built into the interface, tests and evaluation sets, and each fact needs a source fetched at the time. Sources fetched this session from UNESCO (Socotra, Henderson Island, Gough Island, the Galapagos), the Norwegian Polar Institute and Geoscience Australia repeated facts the library already cites. The only real addition was five Clipperton facts.
* **Hosted provider code left untouched.** The earlier hosted provider and its default model name remain in `app/` and `app/config.py`; no key is set and it is never called.
* **Lighthouse performance stays a warning.** The CI runner draws the globe with software rendering, so the performance score and blocking time warnings do not describe a phone.
* **Library growth changed retrieval figures slightly.** Hybrid hit@5 is unchanged at 0.90; hybrid hit@3 moved from 0.81 to 0.79 (listed in the changelog). Sealed runs keep the 469 fact library.

## 5. Attempted but not completed

* Climate change indicators (NOAA OISST, NASA POWER trend): not started.
* Educator PDFs by script: not built; the sheets print to PDF from the browser.
* Demo capture under `docs/img/`: not made beyond the existing screenshots.
* New islands and creatures: none added (see section 4).
* Frozen 30 re-run on the new models: not repeated.
* Local container build and a Lighthouse run on a free machine: not run locally; the CI container job and Lighthouse job passed on the runner.
* Tag `v1.2.0` and the GitHub release: both were attempted and refused by the environment (HTTP 403 for tag pushes and for release creation). The release notes are the 1.2.0 section of `CHANGELOG.md`; the version in `app/__init__.py` and `docs/openapi.json` is 1.2.0.
* Entailment check on 200 or more sentences: 117 measured.
* mypy on `eval/` and `scripts/`: 14 errors, not gated (KI-9).

## 6. Open future work

Real questions labelled by two readers to replace the synthetic set; a fresh question set to re apply the climate route rule; sources and facts for further islands; observational climate indicators with intervals; a judge run with a larger model; tests on real phones; typing for `eval/` and `scripts/`. The full list with severity is in `docs/KNOWN_ISSUES.md` and `docs/ROADMAP.md`.
