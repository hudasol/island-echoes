from __future__ import annotations

import pytest

from app.config import Settings
from app.data.climate_tool import ClimateTool
from app.data.islands import IslandStore
from app.data.sources import SourceStore


@pytest.fixture(scope="module")
def tool() -> tuple[ClimateTool, IslandStore]:
    settings = Settings(anthropic_api_key=None, telemetry=False, source_ttl_days=36500)
    islands = IslandStore.load(settings.islands_dir)
    return ClimateTool(islands, SourceStore(settings, islands, http=object())), islands


def test_question_about_a_place_outside_the_library_is_not_answered(tool) -> None:
    t, islands = tool
    pit = next(i for i in islands.islands.values() if i.slug.startswith("pitcairn"))
    assert t.answer(pit, "What is the annual average temperature on Mauritius according to NASA POWER?") is None
    assert t.answer(pit, "What is the annual average temperature on South Georgia?") is None


def test_question_without_a_place_still_uses_the_selected_island(tool) -> None:
    t, islands = tool
    pit = next(i for i in islands.islands.values() if i.slug.startswith("pitcairn"))
    ans = t.answer(pit, "What is the annual average air temperature in the NASA POWER data?")
    assert ans is not None and ans.route.startswith("annual")
