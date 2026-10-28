# Roadmap

Last reviewed 28 October 2026.

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
| Data report | A script that prints source and confidence composition into `docs/DATA.md`, and primary sources to replace Wikipedia only facts where one exists. |
| Second annotator | A second person labelling gold fact IDs for the retrieval set, to report agreement. |
| Judge run | Run `eval/judge.py` with a model large enough to grade answers. |
| Larger local model | Repeat the baselines on a 7B model to see whether the validator's false refusals shrink. |
