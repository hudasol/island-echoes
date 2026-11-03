# Changelog

## 1.2.0 (3 November 2026)

Moved published numbers (all regenerated from stored runs by code):

- RESULTS.md, "retrieval only, quotes the top sources": unsupported content 3% (1/29) becomes 0% (0/29). The earlier figure was computed
  against a developer's live local cache of NASA POWER and GBIF responses; the report now reads only the committed snapshots, so
  the number can be reproduced from a fresh clone and in continuous integration.

- Library: 469 facts become 474. Five facts from a French National Assembly report (2016) were added to Clipperton, with page
  quotations in the evidence notes: the 1858 act of possession, the arbitration dates, area, a distance and the conflicting
  dates of the first landing. One new conflict is logged. Fact embeddings were rebuilt.
- RESULTS.md, retrieval table: the headline hybrid hit@5 on the 58 held out questions is unchanged at 0.90; hybrid hit@3 moves from
  0.81 to 0.79 and some interval ends move by 0.01 after the library grew. The stored sealed runs used the 469 fact library and keep it.

Added:

- Arabic interface with right to left layout; interface text is translated, facts and citations keep their source language.
- Shareable field report page and image card for each creature; one page educator sheet per island.
- Public read only API under `/api/v1` with an OpenAPI description (`docs/openapi.json`).
- Offline shell, lazy loaded globe bundle, and a Lighthouse mobile budget in CI.
- Sealed synthetic evaluation (150 questions) with a preregistration, a development set, a second model labeller, 1.5B, 3B and 7B runs, and closed book and always refuse baselines.
- Behind settings, off by default because the preregistered rules were not met: a source sentence fallback for rejected sentences, a deterministic climate route (with a fix for questions about places outside the library), and an optional entailment check.
- Scheduled uptime and freshness checks (`.github/workflows/ops.yml`), `docs/OPERATIONS.md`, generated provenance tables in `docs/DATA.md`, `docs/KNOWN_ISSUES.md` and `docs/NASA_PROPOSAL.md`.

## 1.1.0

- Day and night layer on the globe from the real sun position, with a readout of the sub solar point. The globe bundle is built from source.
- Start view listing the seven sites with official IUCN codes, fact counts and data dates.
- Operations and evaluation page with data composition, retrieval results with intervals and paired tests, end to end baselines and traffic.
- `/api/overview` and `/api/evaluation`.
- Official IUCN Red List category from GBIF for each creature, with a link.
- End to end baselines: always refuse, model alone, retrieval and model without the validator, and the full pipeline on one model. Retrieval floors: random, file order and word overlap.
- Self hosted Newsreader and IBM Plex fonts.
- Routes split into modules; mypy clean; API keys held as `SecretStr`; coverage gate at 90 percent; container build in CI.
- Dockerfile, compose file, `pyproject.toml` and a cross platform task runner.

## 1.0.0

- Seven islands, eight creatures, 469 sourced facts.
- Library search without a model, NASA POWER sensors, GBIF records.
- Optional chat through swappable providers with a grounding validator.
- Evaluation harness with frozen, development and held out sets.
