.PHONY: run install test eval eval-offline eval-retrieval eval-baseline embeddings stats report snapshot validate lint

PY ?= python3
VENV := .venv
BIN := $(VENV)/bin

$(BIN)/uvicorn: requirements-dev.txt requirements.txt
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -q -r requirements-dev.txt
	@touch $(BIN)/uvicorn

install: $(BIN)/uvicorn

# One command to run everything locally: make run  ->  http://localhost:8000
run: install
	@test -f .env || cp .env.example .env
	$(BIN)/uvicorn app.main:app --reload --port 8000

test: install
	$(BIN)/pytest -q

validate: install
	$(BIN)/python scripts/validate_data.py

lint: install
	$(BIN)/ruff check .

snapshot: install
	$(BIN)/python scripts/snapshot_sources.py

# Full eval with the Anthropic API and an LLM judge (needs ANTHROPIC_API_KEY; the free paths are below)
eval: install
	$(BIN)/python -m eval.run_eval --judge

# Deterministic checks only on recorded answers (no API calls)
eval-offline: install
	$(BIN)/python -m eval.run_eval --from-run eval/results/latest.json

# ---- LLM layer (no paid key needed) ----
# Rebuild fact embeddings after editing data/islands (needs: pip install -r requirements-ml.txt)
embeddings:
	$(BIN)/pip install -q -r requirements-ml.txt
	$(BIN)/python -m scripts.build_embeddings

# Compare keyword, dense and hybrid retrieval on the gold sets
eval-retrieval: install
	$(BIN)/pip install -q -r requirements-ml.txt
	$(BIN)/python -m eval.retrieval_eval

# End-to-end eval with no model at all (the floor any model must beat)
eval-baseline: install
	$(BIN)/python -m eval.run_eval --provider extractive --retrieval bm25

# Usage statistics from the telemetry database; rebuild docs/RESULTS.md from stored eval runs
stats: install
	$(BIN)/python -m scripts.stats
report: install
	$(BIN)/python -m eval.report
