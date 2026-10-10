"""Dense retrieval: precomputed sentence embeddings of every island fact.

Vectors are computed offline by scripts/build_embeddings.py and committed, so the running app only embeds
the user's question. The fact vectors are stamped with a hash of the fact texts; if the facts change and
the vectors are not rebuilt, the index refuses to load rather than answer from stale vectors.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "  # recommended by the BGE authors


def fact_texts(store) -> list[tuple[str, str]]:
    """(id, evidence text) of every fact: exactly what is embedded and what the model is shown."""
    return [(f.id, store.fact_to_evidence(isl, f).text) for isl in store.islands.values() for f in isl.facts]


class DenseUnavailable(RuntimeError):
    pass


def _np():
    """numpy is only needed for dense retrieval, so the keyword-only deployment does not install it."""
    try:
        import numpy
    except ImportError as exc:
        raise DenseUnavailable("numpy is not installed (pip install -r requirements-ml.txt)") from exc
    return numpy


def texts_hash(items: list[tuple[str, str]]) -> str:
    h = hashlib.sha256()
    for fid, text in sorted(items):
        h.update(f"{fid}\x1f{text}\x1e".encode())
    return h.hexdigest()[:16]


class Embedder:
    """Thin wrapper over fastembed (ONNX, CPU). Imported lazily: it is an optional dependency."""

    def __init__(self, model: str = DEFAULT_MODEL, cache_dir: str | None = None):
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise DenseUnavailable("fastembed is not installed (pip install -r requirements-ml.txt)") from exc
        self.model_name = model
        self._model = TextEmbedding(model, cache_dir=cache_dir)

    def embed(self, texts: list[str]):
        np = _np()
        v = np.array(list(self._model.embed(texts)), dtype=np.float32)
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)

    def embed_query(self, query: str):
        return self.embed([QUERY_PREFIX + query])[0]


class DenseIndex:
    def __init__(self, ids: list[str], vectors, embedder, model: str):
        np = _np()
        self.ids = ids
        self.pos = {i: n for n, i in enumerate(ids)}
        self.vectors = vectors.astype(np.float32)
        self.embedder = embedder
        self.model = model
        self._qcache: dict = {}

    @classmethod
    def load(cls, path: Path, current: list[tuple[str, str]], embedder=None) -> DenseIndex:
        path = Path(path)
        if not path.exists():
            raise DenseUnavailable(f"embeddings file {path} not found (run scripts/build_embeddings.py)")
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        if meta["texts_hash"] != texts_hash(current):
            raise DenseUnavailable("embeddings are stale: the facts changed since they were built")
        z = _np().load(path, allow_pickle=False)
        ids = [str(x) for x in z["ids"]]
        return cls(ids, z["vectors"], embedder or Embedder(meta["model"]), meta["model"])

    def _query_vec(self, query: str):
        if query not in self._qcache:
            if len(self._qcache) > 512:
                self._qcache.clear()
            self._qcache[query] = self.embedder.embed_query(query)
        return self._qcache[query]

    def rank(self, query: str, ids: list[str]) -> list[tuple[float, str]]:
        """Cosine similarity of the question to each requested fact id, best first."""
        keep = [i for i in ids if i in self.pos]
        if not keep:
            return []
        sims = self.vectors[[self.pos[i] for i in keep]] @ self._query_vec(query)
        return sorted(zip(sims.tolist(), keep, strict=True), key=lambda x: -x[0])


def rrf(rankings: list[list[str]], k: int = 60, weights: list[float] | None = None) -> dict[str, float]:
    """Reciprocal rank fusion of several best-first id lists."""
    weights = weights or [1.0] * len(rankings)
    out: dict[str, float] = {}
    for w, ranking in zip(weights, rankings, strict=True):
        for r, i in enumerate(ranking, start=1):
            out[i] = out.get(i, 0.0) + w / (k + r)
    return out
