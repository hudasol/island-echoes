"""Cross platform task runner, for machines without make (Windows PowerShell included).

    python scripts/dev.py run            start the app at http://localhost:8000
    python scripts/dev.py test           run the test suite
    python scripts/dev.py --help         list every task

It creates .venv on first use and installs requirements-dev.txt into it.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
BIN = VENV / ("Scripts" if os.name == "nt" else "bin")
PYTHON = BIN / ("python.exe" if os.name == "nt" else "python")
STAMP = VENV / ".installed"

ML = ["-m", "pip", "install", "-q", "-r", "requirements-ml.txt"]

# task name -> (description, list of commands; each command is a list of arguments for the venv python)
TASKS: dict[str, tuple[str, list[list[str]]]] = {
    "run": ("start the app with auto reload", [["-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"]]),
    "test": ("run the tests", [["-m", "pytest"]]),
    "coverage": ("run the tests and print line and branch coverage", [["-m", "pytest", "--cov", "--cov-report=term-missing"]]),
    "lint": ("ruff check", [["-m", "ruff", "check", "."]]),
    "types": ("mypy on app/", [["-m", "mypy"]]),
    "validate": ("check every fact file", [["scripts/validate_data.py"]]),
    "snapshot": ("refresh the NASA POWER and GBIF snapshots", [["scripts/snapshot_sources.py"]]),
    "embeddings": ("rebuild fact embeddings (installs the optional packages)", [ML, ["-m", "scripts.build_embeddings"]]),
    "eval-retrieval": ("compare keyword, dense and hybrid retrieval", [ML, ["-m", "eval.retrieval_eval"]]),
    "eval-offline": ("score the refuse-all baseline and the extractive system, no model", [["-m", "eval.run_eval", "--system", "refuse-all"]]),
    "bench": ("measure request latency of the library and chat endpoints", [["-m", "scripts.bench"]]),
    "report": ("regenerate docs/RESULTS.md and data/evaluation.json from the stored runs", [["-m", "eval.report"], ["-m", "eval.summary"]]),
    "stats": ("print usage statistics from the telemetry database", [["-m", "scripts.stats"]]),
    "check": ("lint, types, validate and test: what CI runs", [["-m", "ruff", "check", "."], ["-m", "mypy"], ["scripts/validate_data.py"], ["-m", "pytest"]]),
}


def ensure_env() -> None:
    if not PYTHON.exists():
        print("creating .venv ...", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV)
    if not STAMP.exists() or STAMP.stat().st_mtime < (ROOT / "requirements-dev.txt").stat().st_mtime:
        print("installing dependencies ...", flush=True)
        subprocess.run([str(PYTHON), "-m", "pip", "install", "-q", "-r", "requirements-dev.txt", "pytest-cov", "mypy"], cwd=ROOT, check=True)
        STAMP.touch()
    env_file, example = ROOT / ".env", ROOT / ".env.example"
    if not env_file.exists() and example.exists():
        env_file.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print("created .env from .env.example")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", choices=sorted(TASKS), help="; ".join(f"{k}: {v[0]}" for k, v in sorted(TASKS.items())))
    ap.add_argument("extra", nargs=argparse.REMAINDER, help="arguments passed to the last command of the task")
    args = ap.parse_args(argv)
    ensure_env()
    _, commands = TASKS[args.task]
    for i, cmd in enumerate(commands):
        full = [str(PYTHON), *cmd] + (args.extra if i == len(commands) - 1 else [])
        code = subprocess.run(full, cwd=ROOT).returncode
        if code:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
