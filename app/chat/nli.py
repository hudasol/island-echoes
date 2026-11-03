"""Optional entailment check: does the cited evidence entail the sentence?

Uses a small openly licensed natural language inference model (cross-encoder/nli-deberta-v3-xsmall, Apache 2.0,
exported to ONNX and quantised) through onnxruntime and the tokenizers library. It is not used by the service
unless a model directory is supplied; it exists so the evaluation can measure what an entailment check adds to the
word and number validator (see docs/research/PREREGISTRATION_3.md and docs/RESULTS.md).
"""

from __future__ import annotations

import math
from pathlib import Path

LABELS = ("contradiction", "entailment", "neutral")  # order of the model's output logits
MAX_TOKENS = 512


class Entailment:
    def __init__(self, model_dir: Path, onnx_name: str = "onnx/model_quint8_avx2.onnx") -> None:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(str(model_dir / onnx_name), sess_options=opts, providers=["CPUExecutionProvider"])
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=MAX_TOKENS, strategy="only_first")
        self.inputs = {i.name for i in self.session.get_inputs()}

    def score(self, premise: str, hypothesis: str) -> dict[str, float]:
        """Probabilities for contradiction, entailment and neutral."""
        import numpy as np

        enc = self.tokenizer.encode(premise, hypothesis)
        feed = {"input_ids": np.array([enc.ids], dtype=np.int64), "attention_mask": np.array([enc.attention_mask], dtype=np.int64)}
        if "token_type_ids" in self.inputs:
            feed["token_type_ids"] = np.array([enc.type_ids], dtype=np.int64)
        logits = self.session.run(None, feed)[0][0]
        m = float(max(logits))
        exp = [math.exp(float(x) - m) for x in logits]
        total = sum(exp)
        return {name: e / total for name, e in zip(LABELS, exp, strict=True)}

    def entails(self, premise: str, hypothesis: str, threshold: float = 0.5) -> bool:
        return self.score(premise, hypothesis)["entailment"] >= threshold
