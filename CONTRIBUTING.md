# Contributing

## Setup

```bash
git clone https://github.com/hudasol/island-echoes && cd island-echoes
python scripts/dev.py test        # creates .venv, installs dependencies, runs the suite
python scripts/dev.py run         # http://localhost:8000
```

`python scripts/dev.py --help` lists every task and works on Windows, macOS and Linux. `make` offers the same on systems that have it.

## Checks

CI runs, and a change should pass locally:

```bash
python scripts/dev.py check       # ruff, mypy, fact file validation, tests with coverage
cd web && npm ci && npm test      # sun position tests
```

Coverage is gated at 90 percent. The front end bundle in `web/vendor/` is built from `web/src/` with `npm run build` and committed; CI fails when the two differ.

## Adding or correcting facts

1. Edit the island file in `data/islands/`. Keep the ID sequence, give the statement one claim, link the page that supports it and say in `evidence_note` what on that page supports it.
2. Use the label High only for a primary source. A fact that rests on one encyclopedia or news page is Medium.
3. Record conflicts between sources as separate facts and list them under `conflicts`.
4. Run `python scripts/validate_data.py`, then `python scripts/dev.py report` if retrieval gold sets reference the file.

## Commits

One logical change per commit, with a message that says what changed and why. Commit to `main` in small steps; open a pull request for anything risky or large.
