# Changelog

## 1.2.0 (in progress)

Moved published numbers (all regenerated from stored runs by code):

- RESULTS.md, "retrieval only, quotes the top sources": unsupported content 3% (1/29) becomes 0% (0/29). The earlier figure was computed
  against a developer's live local cache of NASA POWER and GBIF responses; the report now reads only the committed snapshots, so
  the number can be reproduced from a fresh clone and in continuous integration.

Added so far: Arabic interface, shareable field report, educator sheets, public read only API under `/api/v1`, offline
shell updates, climate tool and lossless validation fallback behind settings (off by default), scheduled uptime and freshness checks.

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
