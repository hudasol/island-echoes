# Roadmap

Last reviewed 3 November 2026.

## Shipped in 1.2.0

| Area | Change |
|---|---|
| Evaluation | A preregistered sealed set of 150 synthetic questions with a development set, a second model labeller, Wilson intervals and exact paired tests; 1.5B, 3B and 7B models; closed book and always refuse baselines. |
| Pipeline | A source sentence fallback and a deterministic climate route, both off by default because they did not meet their preregistered rules; an optional entailment check, off by default. |
| Data | Provenance tables generated into `DATA.md`; five Clipperton facts from a primary report; a freshness check. |
| Product | Arabic interface, educator sheets, shareable field reports, public read only API, offline shell, lazy globe bundle, Lighthouse budget in CI. |
| Operations | Scheduled uptime and freshness checks, documented in [OPERATIONS.md](OPERATIONS.md). |

## Shipped in 1.1.0

| Area | Change |
|---|---|
| Baselines | Always refuse, model alone, retrieval and model without the validator, and the full pipeline, scored on the same frozen questions. Retrieval floors: random, file order, word overlap. Latency benchmark in `scripts/bench.py`. |
| Data | Official IUCN Red List category per creature, read from GBIF and shown with a link. |
| Packaging | Dockerfile, compose file, `pyproject.toml`, cross platform task runner. |
| Quality | Coverage gate at 90 percent, mypy on `app/`, secrets held as `SecretStr`, routes split into modules. |
| Documentation | README, architecture, API, data, evaluation, contributing, security and changelog documents, issue and pull request templates. |
| Front end | Start view, day and night layer from the sun position, operations page, self hosted fonts, globe bundle built from source. |
| Accessibility | `scripts/a11y.py` runs axe-core on five states at desktop and phone widths and writes [ACCESSIBILITY.md](ACCESSIBILITY.md). |

## Next

| Item | What it needs |
|---|---|
| Real questions | Collected with consent and labelled by two human readers, to replace the synthetic sealed set. |
| Climate route | Re run the keep rule for the climate route on a fresh question set, now that the unknown place defect is fixed. |
| More islands | New islands and creatures, each fact backed by a source fetched at the time; the interface, tests and evaluation sets assume seven islands. |
| Climate change indicators | NOAA OISST and a NASA POWER trend with its interval, labelled observational and not attribution. Not started. |
| Educator PDFs | A script that writes the educator sheets to PDF; the sheets print to PDF from the browser today. |
| Judge run | Run `eval/judge.py` with a model large enough to grade answers. |
| Typing | Bring `eval/` and `scripts/` under mypy. |
