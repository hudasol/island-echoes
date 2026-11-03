"""Small helper to run a local GGUF model with a JSON schema, for question writing and second labelling."""

from __future__ import annotations

import json
import os
from pathlib import Path

MODELS = Path(os.environ.get("MODELS_DIR", "/tmp/claude-0/models"))


def load(name: str, n_ctx: int = 4096):
    from llama_cpp import Llama

    return Llama(model_path=str(MODELS / name), n_ctx=n_ctx, n_threads=2, verbose=False)


def ask(llm, system: str, user: str, schema: dict, max_tokens: int = 120) -> dict:
    r = llm.create_chat_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object", "schema": schema},
        temperature=0,
        max_tokens=max_tokens,
    )
    return json.loads(r["choices"][0]["message"]["content"])
