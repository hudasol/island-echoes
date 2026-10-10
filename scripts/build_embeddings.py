"""Embed every island fact and write data/embeddings/<model>.npz (+ .json manifest).

Run after the facts change: python -m scripts.build_embeddings
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402
from app.retrieval.dense import DEFAULT_MODEL, Embedder, fact_texts, texts_hash  # noqa: E402


def main() -> None:
    s = get_settings()
    store = IslandStore.load(s.islands_dir)
    items = fact_texts(store)
    emb = Embedder(DEFAULT_MODEL)
    vecs = emb.embed([t for _, t in items])
    out = s.embeddings_path
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, ids=np.array([i for i, _ in items]), vectors=vecs.astype(np.float16))
    out.with_suffix(".json").write_text(
        json.dumps(
            {
                "model": DEFAULT_MODEL,
                "dim": int(vecs.shape[1]),
                "count": len(items),
                "texts_hash": texts_hash(items),
                "built": date.today().isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out} ({len(items)} facts, dim {vecs.shape[1]})")


if __name__ == "__main__":
    main()
