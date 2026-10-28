from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import UTC

from app.config import Settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402
from app.data.retrieval import Retriever  # noqa: E402
from app.data.sources import SourceStore  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


# Keep tests hermetic: a key or provider in the developer's shell or .env must not change what Settings() sees.
# An environment variable overrides .env in pydantic-settings, so an empty value masks both. This runs when
# conftest is imported, before test modules (and app.main, which reads settings at import) are collected.
PROVIDER_ENV = ("ANTHROPIC_API_KEY", "LLM_PROVIDER", "LLM_MODEL", "HF_TOKEN", "OPENAI_API_KEY", "OPENAI_BASE_URL")
for _name in PROVIDER_ENV:
    os.environ[_name] = ""


@pytest.fixture(scope="session")
def real_settings() -> Settings:
    # The committed snapshots must count as fresh whatever the date, or the suite starts failing 30 days after
    # they were taken. Staleness itself is tested on copies with aged timestamps (see tmp_settings).
    return Settings(anthropic_api_key=None, telemetry=False, source_ttl_days=36500)


@pytest.fixture(scope="session")
def store(real_settings) -> IslandStore:
    return IslandStore.load(real_settings.islands_dir)


@pytest.fixture()
def tmp_settings(tmp_path) -> Settings:
    """Settings whose snapshots/cache live in a temp dir (islands stay the real ones)."""
    snaps = tmp_path / "snapshots"
    shutil.copytree(ROOT / "data" / "snapshots", snaps)
    from datetime import datetime

    now = datetime.now(UTC).isoformat(timespec="seconds")
    for f in snaps.glob("*/*.json"):  # copies start fresh; tests that need old data age them with age_snapshot
        doc = json.loads(f.read_text(encoding="utf-8"))
        doc["fetched_at"] = now
        f.write_text(json.dumps(doc), encoding="utf-8")
    return Settings(
        anthropic_api_key=None,
        snapshots_dir=snaps,
        cache_dir=tmp_path / "cache",
        telemetry_path=tmp_path / "telemetry.db",
    )


@pytest.fixture()
def retriever(real_settings, store) -> Retriever:
    """Retriever reading only the committed snapshots (never the network)."""
    return Retriever(store, SourceStore(real_settings, store, http=_NoNetwork()))


class _NoNetwork:
    """Stand-in HTTP client that fails the test if anything tries to go online."""

    def get(self, *a, **k):  # pragma: no cover
        raise AssertionError("network call attempted in an offline test")


def age_snapshot(path: Path, days: int) -> None:
    from datetime import datetime, timedelta

    doc = json.loads(path.read_text())
    doc["fetched_at"] = (datetime.now(UTC) - timedelta(days=days)).isoformat(timespec="seconds")
    path.write_text(json.dumps(doc))
