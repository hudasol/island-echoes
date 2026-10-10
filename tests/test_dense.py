import json

import numpy as np
import pytest

from app.config import Settings
from app.data.retrieval import Retriever
from app.data.sources import SourceStore
from app.retrieval.dense import DenseIndex, DenseUnavailable, fact_texts, rrf, texts_hash
from app.retrieval.factory import build_retriever


class FakeEmbedder:
    """Deterministic bag-of-words embedder: lets the tests exercise ranking without downloading a model."""

    def __init__(self, dim=64):
        self.dim = dim

    def _vec(self, text):
        v = np.zeros(self.dim, dtype=np.float32)
        for w in text.lower().split():
            v[hash(w.strip(".,?")) % self.dim] += 1
        n = np.linalg.norm(v)
        return v / n if n else v

    def embed_query(self, q):
        return self._vec(q)

    def embed(self, texts):
        return np.array([self._vec(t) for t in texts])


def _index(store, tmp_path, embedder=None):
    items = fact_texts(store)
    emb = embedder or FakeEmbedder()
    path = tmp_path / "e.npz"
    np.savez_compressed(path, ids=np.array([i for i, _ in items]), vectors=emb.embed([t for _, t in items]).astype(np.float16))
    path.with_suffix(".json").write_text(json.dumps({"model": "fake", "texts_hash": texts_hash(items)}))
    return DenseIndex.load(path, items, embedder=emb)


def test_rrf_rewards_agreement():
    out = rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert out["a"] == pytest.approx(out["b"], rel=0.05) and out["a"] > out["c"] and out["b"] > out["d"]
    assert rrf([["x"]], weights=[2.0])["x"] == pytest.approx(2 / 61)


def test_committed_embeddings_match_current_facts(real_settings, store):
    meta = json.loads(real_settings.embeddings_path.with_suffix(".json").read_text())
    assert meta["texts_hash"] == texts_hash(fact_texts(store)), "facts changed: run python -m scripts.build_embeddings"
    assert meta["count"] == len(fact_texts(store))


def test_stale_embeddings_are_refused(store, tmp_path):
    idx_path = tmp_path / "e.npz"
    _index(store, tmp_path)
    items = fact_texts(store)
    items[0] = (items[0][0], items[0][1] + " changed")
    with pytest.raises(DenseUnavailable, match="stale"):
        DenseIndex.load(idx_path, items, embedder=FakeEmbedder())


def test_missing_file_is_a_clean_error(store, tmp_path):
    with pytest.raises(DenseUnavailable, match="not found"):
        DenseIndex.load(tmp_path / "nope.npz", fact_texts(store), embedder=FakeEmbedder())


def test_dense_rank_orders_by_similarity_and_caches_queries(store, tmp_path):
    idx = _index(store, tmp_path)
    ids = [f.id for f in store.get("socotra").facts]
    ranked = idx.rank("highest point Mashanig Hajhir Mountains", ids)
    assert ranked[0][1] == "SOC-011"
    assert ranked == sorted(ranked, key=lambda x: -x[0])
    idx.rank("highest point Mashanig Hajhir Mountains", ids)
    assert len(idx._qcache) == 1


def test_retriever_modes(real_settings, store, tmp_path):
    idx = _index(store, tmp_path)
    r = Retriever(store, SourceStore(real_settings, store), dense=idx, mode="hybrid")
    q = "highest point Mashanig Hajhir Mountains"
    for mode in ("bm25", "dense", "hybrid"):
        ranked, info = r.rank("socotra", q, None, mode=mode)
        assert ranked[0].id == "SOC-011" and info["mode"] == mode
    assert r.search("socotra", q).evidence[0].id == "SOC-011"
    bm = Retriever(store, SourceStore(real_settings, store))
    assert bm.mode == "bm25"
    with pytest.raises(ValueError):
        bm.rank("socotra", q, None, mode="dense")


def test_build_retriever_falls_back_when_vectors_missing(real_settings, store, tmp_path):
    s = Settings(retrieval_mode="hybrid", embeddings_path=tmp_path / "missing.npz", telemetry=False)
    r = build_retriever(s, store, SourceStore(real_settings, store))
    assert r.mode == "bm25"
