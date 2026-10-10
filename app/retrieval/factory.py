from __future__ import annotations

import logging

from ..config import Settings
from ..data.islands import IslandStore
from ..data.retrieval import Retriever
from ..data.sources import SourceStore
from .dense import DenseIndex, fact_texts

log = logging.getLogger(__name__)


def build_retriever(settings: Settings, islands: IslandStore, sources: SourceStore) -> Retriever:
    """BM25 always; dense and hybrid only when asked for and loadable (optional dependency, fresh vectors)."""
    dense = None
    mode = settings.retrieval_mode.lower()
    if mode != "bm25":
        try:
            dense = DenseIndex.load(settings.embeddings_path, fact_texts(islands))
        except Exception as exc:  # noqa: BLE001 - an optional layer must never stop the app
            log.warning("dense retrieval disabled, using bm25: %s", exc)
    return Retriever(islands, sources, k=settings.retrieval_k, dense=dense, mode=mode if dense else "bm25", dense_min_sim=settings.dense_min_sim)
