.PHONY: run install test eval eval-offline snapshot validate lint

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

# Full eval: needs ANTHROPIC_API_KEY in .env (answers + LLM judge)
eval: install
	$(BIN)/python -m eval.run_eval --judge

# Deterministic checks only on recorded answers (no API calls)
eval-offline: install
	$(BIN)/python -m eval.run_eval --from-run eval/results/latest.json
