# LLM layer: architecture and evaluation plan

Goal: add a language-model layer to Island Echoes that costs nothing to run, can be swapped for any
provider, can only say what the cited sources say, and reports its own statistics.

## Principles

1. **Grounded by construction.** The model never sees anything but retrieved evidence, and every sentence
   it returns is checked (citation exists, numbers and proper nouns appear in the cited text) before a
   user sees it. Unsupported sentences are repaired once, then dropped.
2. **Zero-cost by default.** No paid key is needed. The deployed site stays model-free; chat is switched
   on with `LLM_PROVIDER` (a local model, a free hosted endpoint, or Anthropic if a key exists).
3. **Every layer is swappable and measured.** Each choice (retriever, generator, validator) is a config
   value, and the eval reports the same metrics for each, so comparisons are one command.
4. **Honest numbers.** Tuned sets and held-out sets are labelled separately. Every eval run is stored
   with its configuration, data hash and git revision, so a number can be traced to what produced it.

## Layers

| Layer | Module | What it does | Swap via |
|---|---|---|---|
| L0 Data | `app/data/*`, `data/` | 469 cited facts, NASA POWER and GBIF evidence, snapshots | (existing) |
| L1 Retrieval | `app/data/retrieval.py`, `app/retrieval/` | BM25, dense vectors (bge-small-en-v1.5, precomputed), reciprocal-rank fusion, answerability gate | `RETRIEVAL_MODE=bm25\|dense\|hybrid` |
| L2 Generation | `app/llm/` | one `AnswerLLM` interface: `extractive` (no model, baseline), `ollama`, `llamacpp`, `huggingface`, `anthropic` | `LLM_PROVIDER` |
| L3 Guardrails | `app/chat/grounding.py` | citation, number and proper-noun checks, one repair retry, refusal on no evidence | (existing) |
| L4 Telemetry | `app/telemetry/` | one SQLite row per request: stage latencies, retrieval quality, provider, tokens, validator outcome. Question text is not stored unless `LOG_QUESTIONS=true` | `TELEMETRY=on\|off` |
| L5 Evaluation | `eval/` | runs registry, metrics with confidence intervals, comparison report | `make eval-*` |
| L6 Surface | `app/main.py`, `web/` | `/api/chat` (when a provider is set), `/api/stats`, chat tab shown only when enabled | (existing) |

Dense retrieval is optional at runtime (extra dependency file `requirements-ml.txt`), because the free
Render instance has 512 MB of memory. Without it the app falls back to BM25 and says so in `/api/health`.

## Evaluation design

Three sets, kept separate:

- `eval/questions.jsonl` (30): expected fact IDs, required strings, refusal cases. Used for retrieval
  recall and generation correctness.
- `eval/library_relevance.jsonl` (106): answerable or not, split `tuned` or `heldout`. Used for the
  answerability gate (false-positive and false-negative rates).
- `eval/heldout.jsonl` (new): written after the retriever settled and never used for tuning.

Metrics (all with 95% Wilson or bootstrap intervals):

- Retrieval: recall@1/3/5/12, MRR, nDCG@5 on gold fact IDs.
- Gate: false-positive rate on unanswerable questions, empty rate on answerable ones.
- Generation: answered-correctly (required strings present), refusal accuracy, citation precision (cited
  IDs that were retrieved), groundedness (share of kept fact sentences passing every check),
  hallucination rate (unsupported fact sentences before validation), repair rate, drop rate.
- System: latency p50/p95 per stage, tokens per answer, error rate.

Comparison matrix, reported in the README: retriever (bm25, dense, hybrid) by generator (extractive and
each model that was actually run). Only combinations that were run are reported.

## Statistics

- Live: `GET /api/stats?days=7` returns aggregates from the telemetry store (volume, answer rate,
  refusal rate, latency percentiles, validator outcomes, top islands, retrieval-mode share).
- Offline: `python -m scripts.stats` prints the same as a table or CSV; `eval/report.py` renders the
  comparison between stored eval runs as Markdown.
- Telemetry is a plain SQLite file, so any query tool, pandas or DuckDB can read it directly.

## Build order

1. Retrieval package: embeddings build script, hybrid retriever, retrieval eval. Gate: no regression on
   the 106-question set, measured gain on recall@k.
2. Provider layer: interface, extractive baseline, Ollama, llama.cpp, Hugging Face, Anthropic; structured
   output through JSON schema for the local ones; tests with recorded responses.
3. Telemetry and stats: store, middleware hooks, `/api/stats`, CLI.
4. Eval runs registry and report; run the matrix with whatever model can run for free; write results to
   the README with the caveat that applies (model size, number of questions, tuned or held-out).
5. UI: chat tab appears only when `chat_enabled`; stats page.
6. Demo video last.

## Constraints and risks

- Small local models follow citation formats less reliably than large ones. The validator is the
  safety net, and the eval reports how often it had to intervene.
- A 30-question eval has wide intervals; the report prints them rather than hiding them.
- Telemetry on the free Render plan is lost on restart (ephemeral disk). `/api/stats` says since when the
  data starts. A persistent disk or external store is a later option.

## Status

Built and measured: retrieval modes with a held-out gold set, provider layer, telemetry and stats, checkpointed eval runner, report generator. Not built: an entailment-based verifier and a judge model run (no free option was run yet), a persistent telemetry store for the deployed instance.
