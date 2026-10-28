# Preregistration: local model evaluation, October 2026

Written and committed before any of the runs below. The predictions are informed by one earlier stored run
(`eval/results/qwen25-3b-hybrid.json`, commit `4321023`, same model through llama.cpp), which was read before this
file was written. Nothing else about the new runs was known.

## Hardware and setup

- Laptop CPU, AMD Ryzen 7 7730U (8 cores, 16 threads), integrated graphics, 13.9 GB RAM, Windows 11.
- Answer model: `qwen2.5:3b-instruct` (quantised to 4 bits) served by Ollama, temperature 0, context 8192 tokens,
  JSON schema constrained output.
- Retrieval: `bm25` or `hybrid` (BM25 plus bge-small-en-v1.5, reciprocal rank fusion), 8 facts shown to the model
  (`--k 8`, the same as the earlier run, to keep CPU time per question manageable).
- The grounding validator (`app/chat/grounding.py`) is the same in every run.

## Judge pass

The plan allowed a judge pass with a larger local model only on a machine with 16 GB of RAM or more. This machine
has 13.9 GB, so no judge is run. Groundedness and hallucination below are therefore mechanical proxies, not
semantic judgements, and every report will say so.

## Configurations

| ID | Run label | Questions | When |
|---|---|---|---|
| R | `retrieval.json` | 58 held out, 19 development | first, no model |
| A | `qwen25-3b-ollama-bm25` | frozen 30 | after R |
| B | `qwen25-3b-ollama-hybrid` | frozen 30 | after A |
| C | `qwen25-3b-ollama-hybrid-fixed` | frozen 30, run once | after tuning on the development set only |

## Metric definitions

- **Hallucination proxy (H)**: share of the model's first-attempt fact sentences that fail at least one validator
  check (no citation, a citation that was not retrieved, a number or a name absent from the cited evidence). This is
  the `first-attempt failures` column. Sentences that fail are never shown, so H measures what the model tried to
  say, not what a user sees.
- **Groundedness proxy (G)**: share of first-attempt fact sentences that pass every mechanical check, that is 1 − H.
  It cannot detect a wrong claim built from correct words.
- **False refusal rate (FR)**: answerable questions (25 of 30) where the reply was not marked answered.
- **Refusal accuracy (RA)**: unanswerable or injection questions (5 of 30) declined without asserting a forbidden
  value.
- **Pass rate (P)**: questions passing every check.

All proportions are reported with 95% Wilson intervals. Errored questions (for example malformed model output after
one retry) are excluded, counted and listed.

## Predictions

| Config | H | G | FR | RA | P |
|---|---|---|---|---|---|
| R | held out hit@5 reproduces the stored values exactly (bm25 0.81, hybrid 0.90), since retrieval is deterministic | | | | |
| A (bm25) | 27%, range 15 to 40% | 73%, range 60 to 85% | 40%, range 25 to 55% | 4/5, range 3 to 5 | 50%, range 35 to 65% |
| B (hybrid) | 27%, range 15 to 40% | 73%, range 60 to 85% | 40%, range 25 to 55% | 4/5, range 3 to 5 | 50%, range 35 to 65% |
| C (fixed) | not above B's point value; range 10 to 35% | range 65 to 90% | 15%, range 5 to 30% | at least 4/5 | 60%, range 45 to 75% |

Further predictions:

1. A and B will not differ on any metric by more than their intervals allow. Retrieval on these 30 questions is
   already near ceiling for BM25, which was developed against them.
2. Ollama's schema constrained decoding will produce no more than one errored question per run.
3. The main causes of false refusal in B will be the same as in the earlier run: facts written as voice sentences,
   fact sentences without citations, and the model setting `answered` to false although a cited fact survives.
4. C will lower FR against B. With 25 answerable questions the intervals will probably overlap, so the comparison
   will be tested with a paired two sided exact McNemar test on the same questions (alpha 0.05). An improvement is
   claimed only if that test or non overlapping intervals support it.

## Tuning protocol for C

- Tuning uses only `eval/dev_questions.jsonl`: 20 answerable questions written from `data/islands`, targeting facts
  that no frozen question expects, plus 5 refusal guards (4 unanswerable, 1 injection). Tests enforce the separation.
- At most four development iterations. A change is kept only if, on the development set, FR falls, H does not rise
  above the development baseline point value, and the refusal guards stay at 4/5 or better.
- The validator must not become more permissive. `app/chat/grounding.py` checks are not relaxed; the existing
  grounding tests must pass unchanged.
- The frozen 30 are run once with the chosen configuration. No further change is made after seeing that result.

## How misses will be reported

- `docs/RESULTS.md` will carry a table of every prediction above against the measured value, marked hit or miss.
- A miss is reported as measured, with a one line explanation if one is evident, and is not hidden or rerun.
- A run is repeated only after an infrastructure failure (process crash, Ollama down), and the repeat is logged in
  `docs/research/EVALUATION_LOG.md`.
- Numbers from the development set are labelled as tuned. Numbers on the frozen 30 for C are a single
  run after tuning, on questions the tuning never saw, but the frozen 30 were used to diagnose the problem in the earlier run, so
  they are reported as a regression check, not as a fully held out result.

## Amendment before results (16 October, 09:50 UTC+04:00)

Added after the runs started and before any result was read. Under the load on the machine at run time (other
processes kept the CPU near 100%), generation ran at about 5.7 tokens per second, too slow to run A, B and the
development runs one after another in the time available. Ollama was therefore restarted with two parallel slots,
and A ran at the same time as B and the development runs. Answers are generated at temperature 0, so this changes
timing, not the predictions or the metrics above. Latency figures from these runs are reported but are not
comparable with earlier runs or with an idle machine.
