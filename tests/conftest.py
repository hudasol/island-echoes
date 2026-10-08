from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402
from app.data.retrieval import Retriever  # noqa: E402
from app.data.sources import SourceStore  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def real_settings() -> Settings:
    return Settings(anthropic_api_key=None)


@pytest.fixture(scope="session")
def store(real_settings) -> IslandStore:
    return IslandStore.load(real_settings.islands_dir)


@pytest.fixture()
def tmp_settings(tmp_path) -> Settings:
    """Settings whose snapshots/cache live in a temp dir (islands stay the real ones)."""
    snaps = tmp_path / "snapshots"
    shutil.copytree(ROOT / "data" / "snapshots", snaps)
    return Settings(
        anthropic_api_key=None,
        snapshots_dir=snaps,
        cache_dir=tmp_path / "cache",
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
    from datetime import datetime, timedelta, timezone

    doc = json.loads(path.read_text())
    doc["fetched_at"] = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    path.write_text(json.dumps(doc))
