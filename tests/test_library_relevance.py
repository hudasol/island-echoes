"""Guards the library's "say so when it does not know" behaviour.

eval/library_relevance.jsonl holds questions the library should answer and questions it should not.
Both splits were tuned against, so these are regression checks, not an independent score. The first
run on a fresh set (before any tuning on it) gave 27% answerable questions empty and 5% false positives.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.data.islands import IslandStore
from app.data.retrieval import Retriever
from app.data.sources import SourceStore

ROWS = [json.loads(line) for line in (Path(__file__).resolve().parents[1] / "eval" / "library_relevance.jsonl").read_text().splitlines()]


@pytest.fixture(scope="module")
def retriever():
    s = get_settings()
    islands = IslandStore.load(s.islands_dir)
    return Retriever(islands, SourceStore(s, islands))


def _answered(retriever, row) -> bool:
    res = retriever.library(row["island"], row["question"])
    return res.total > 0 and res.quality in ("strong", "partial")


def test_unanswerable_questions_get_no_results(retriever):
    rows = [r for r in ROWS if not r["answerable"]]
    wrong = [r["question"] for r in rows if _answered(retriever, r)]
    assert len(wrong) / len(rows) <= 0.05, wrong


def test_answerable_questions_get_results(retriever):
    rows = [r for r in ROWS if r["answerable"]]
    empty = [r["question"] for r in rows if not _answered(retriever, r)]
    assert len(empty) / len(rows) <= 0.10, empty


def test_island_and_creature_names_alone_still_return_facts(retriever):
    res = retriever.library("cocos-keeling", "Napoleon wrasse")
    assert res.total > 0 and res.quality == "strong"


def test_unknown_capitalised_name_is_rejected(retriever):
    assert retriever.library("socotra", "what language is spoken in Brazil").total == 0


def test_empty_query_still_browses_everything(retriever):
    res = retriever.library("bouvet", "")
    assert res.quality == "browse" and res.total > 30
