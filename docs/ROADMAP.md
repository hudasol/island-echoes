# Roadmap and known limitations

Last reviewed 28 October 2026. This file lists what the project cannot yet do, how each gap will be closed, and how we will know it is closed. Items are ordered by how much they affect a reader who is judging the product.

State of the project at the start of this review: 263 tests passing, lint and data validation clean, seven islands, 469 sourced facts, a library search with no model, an optional grounded chat, and an evaluation harness with 30 frozen, 25 development and 30 held out questions.

## Gaps found

| ID | Area | Limitation (evidence) | Planned fix | Done when |
|---|---|---|---|---|
| L1 | Baselines | Only one system without retrieval logic (quote the top sources) and one model configuration are compared. There is no closed book model, no model without the validator, and no weak retrieval floor, so the value of retrieval and of the validator is not measured. | Add baselines to the evaluation: random retrieval, title keyword retrieval, a closed book model, and retrieval with a model but the validator off. Score every system with the same scorer. Add a latency benchmark. | `docs/EVALUATION.md` has one table with all systems on the same questions, and every row can be reproduced by a documented command. |
| L2 | Data | Conservation statuses are second hand and the panel says the IUCN Red List could not be fetched. | Read the IUCN category from the GBIF species endpoint (it carries the Red List category and taxon ID), store it in the snapshot and show it with its source. | All eight creatures show an official category with a link, and a test fails if it disagrees with the fact files. |
| L3 | Product | The live site shows no chat, because no answer provider is set on Render. | Default `render.yaml` to the no model provider so chat is present at no cost, and state plainly what it does. | `/api/health` on a fresh deploy reports `chat_enabled: true`. |
| L4 | Packaging | No container image, no `pyproject.toml`, and the Makefile assumes a POSIX shell. | Add a Dockerfile, a compose file with an optional local model profile, project metadata and a cross platform task runner. | `docker compose up` serves the app, and every command in the README runs on Windows and Linux. |
| L5 | Tests | No coverage figure. Narration, several routes and the telemetry summary have thin or no tests. | Measure coverage, add tests for the gaps, gate CI at the measured floor. | CI fails when coverage drops below the floor. |
| L6 | Types | No static type check. | Add mypy for `app/` and fix what it finds. | CI runs mypy clean. |
| L7 | Code | The Anthropic key is a plain string, and `app/data/retrieval.py` and `app/retrieval/` import each other. | Use `SecretStr`, and move the shared types so imports run one way. | No key appears in `repr(settings)`, and an import test passes. |
| L8 | Documentation | Process records (preregistrations, session logs) sit beside product documents, and the README mixes product text with research notes. | Move process records to `docs/research/`, shorten the README to what a user needs, and add architecture, API, data, evaluation, contributing, security and changelog documents plus issue and pull request templates. | A new reader can run the app, find the API and understand the data from the README in under five minutes. |
| L9 | Accessibility | The axe audit was run once and is not stored. | Add a script that runs axe against the app and stores the report. | `docs/ACCESSIBILITY.md` carries the output of a command anyone can rerun. |
| L10 | Front end | The side panel is empty until an island is chosen. | Replace it with a short start view that says what the app is and how to use it. | The start view renders on desktop and phone, with a test. |
| L11 | Data | 37% of facts cite Wikipedia and 52% are labelled medium confidence. | Report these numbers from a script, keep High reserved for primary sources, and replace Wikipedia only facts with primary sources where one exists. | `docs/DATA.md` shows the counts, produced by `scripts/data_report.py`. |

## Not closable from this repository

- A second person to label gold fact IDs. The retrieval gold set has one annotator.
- A judge model run. It needs a model with enough memory; the harness exists (`eval/judge.py`).
- Earlier commits carry assistant co author trailers. Removing them means rewriting published history, which this project does not do.
- Render settings. They are changed in the Render dashboard.

## Order of work

1. Documentation structure and packaging (L8, L4), so later changes land in a clean layout.
2. Baselines and benchmark (L1), the largest gap in evidence.
3. Official conservation status (L2).
4. Tests, types and code cleanup (L5, L6, L7).
5. Deployment default, start view, accessibility report, data report (L3, L10, L9, L11).
6. Final pass: regenerate results, check that every number in the README appears in the generated documents, and rerun the full suite.

## Status

Updated as each item lands.

| ID | Status |
|---|---|
| L1 to L11 | Open |
