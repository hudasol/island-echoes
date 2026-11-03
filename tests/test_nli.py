from __future__ import annotations

import numpy as np

from app.chat.nli import LABELS, Entailment
from eval.nli_eval import kappa


class _FakeSession:
    def __init__(self, logits):
        self._logits = logits

    def run(self, _out, feed):
        assert set(feed) == {"input_ids", "attention_mask"}
        return [np.array([self._logits])]


class _Enc:
    ids = [1, 2, 3]
    attention_mask = [1, 1, 1]
    type_ids = [0, 0, 0]


class _FakeTok:
    def encode(self, _a, _b):
        return _Enc()


def _entail(logits):
    e = Entailment.__new__(Entailment)
    e.session, e.tokenizer, e.inputs = _FakeSession(logits), _FakeTok(), {"input_ids", "attention_mask"}
    return e


def test_probabilities_sum_to_one_and_follow_label_order() -> None:
    p = _entail([0.0, 5.0, 0.0]).score("premise", "claim")
    assert list(p) == list(LABELS)
    assert abs(sum(p.values()) - 1) < 1e-9 and p["entailment"] > 0.98


def test_threshold() -> None:
    assert _entail([0.0, 5.0, 0.0]).entails("a", "b")
    assert not _entail([5.0, 0.0, 0.0]).entails("a", "b")


def test_kappa() -> None:
    assert kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert abs(kappa([True, True, False, False], [True, False, True, False])) < 1e-9
    assert kappa([], []) == 0.0
