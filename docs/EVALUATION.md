# Evaluation

The evaluation answers three separate questions: does the right fact reach the model (retrieval), does the whole system answer correctly and refuse when it should (end to end), and does the library search stay quiet on questions it cannot answer (library relevance). Every run is stored in `eval/results/` with its model, retrieval mode, commit and a hash of the fact files. Generated tables are in [RESULTS.md](RESULTS.md); the operations page at `/stats.html` shows the same numbers.

## Question sets

| File | Questions | Use |
|---|---|---|
| `eval/questions.jsonl` | 30 | Frozen end to end set. Single fact, multiple fact, climate, species, source conflict, unanswerable and prompt injection questions. |
| `eval/dev_questions.jsonl` | 25 | Development set used while changing the prompt or the validator. |
| `eval/questions_heldout.jsonl` | 30 | Questions written after the design was fixed. Ten are sealed. |
| `eval/retrieval_gold.jsonl` | 58 | Paraphrased questions with gold fact IDs, for retrieval. |
| `eval/library_relevance.jsonl` | 106 | 52 answerable and 54 unanswerable questions for the no model library search. |

## Baselines

All four systems answer the frozen 30 questions with the same scorer. The model rows use one model and one serving stack (Qwen2.5 3B Instruct, 4 bit, llama.cpp, temperature 0) and hybrid retrieval where retrieval is used, so each row differs from the next by one component. Brackets are 95% Wilson intervals.

| System | Passed | False refusals (of 25 answerable) | Refusal accuracy (of 5) | Key fact recall (of 41) |
|---|---|---|---|---|
| Always refuse | 5 of 30 | 25 | 5 | 0 |
| Model alone, no sources | 4 of 30 | 15 | 2 | 6 |
| Retrieval and model, no validator | 25 of 30 | 0 | 4 | 37 |
| Retrieval, model and validator | 19 of 30 | 8 | 5 | 30 |

Sources account for the large effect: the model alone passes 4 of 30 and states a number or name found in no source in 4 of its 12 answers. The validator removed the one unsupported answer that the unvalidated system produced (1 of 26 against 0 of 17), at the price of 8 additional false refusals on this small model. The interval for the unsupported content difference is wide, so only the cost in refusals is established by this run. Retrieval baselines (random, file order, word overlap) are measured the same way on the held out retrieval set, where hybrid retrieval is significantly better than word overlap (exact McNemar p = 0.013) and BM25 is not (p = 0.227).

Reproduce on any machine with a GGUF model:

```bash
python -m eval.run_eval --system refuse-all
python -m eval.run_eval --system closed-book  --provider llamacpp --retrieval hybrid
python -m eval.run_eval --system unvalidated  --provider llamacpp --retrieval hybrid
python -m eval.run_eval --system full         --provider llamacpp --retrieval hybrid
python -m eval.retrieval_eval
python -m eval.report && python -m eval.summary
```

Set `LLAMACPP_MODEL_PATH` to the model file. With Ollama use `--provider ollama`; earlier rows in RESULTS were served that way and differ in serving stack.

## Detailed results and notes

Three kinds of check, kept separate. Full tables are generated into [docs/RESULTS.md](docs/RESULTS.md) by `make report`; every run is stored in `eval/results/` with its model, retrieval mode, commit and a hash of the facts. Runs before 18 October 2026 stamped the commit when they finished, so some record a later commit that changed only documentation; newer runs stamp it at the start.

### Retrieval (`make eval-retrieval`). Does the right fact reach the model? 58 held out questions, paraphrased on purpose so they do not reuse the fact wording, each with gold fact IDs (`eval/retrieval_gold.jsonl`), plus the 19 fact-ID questions of the 30-question set, which the keyword retriever was developed against.

| Held-out set, n=58 | hit@1 | hit@5 | recall@12 | MRR |
|---|---|---|---|---|
| keyword (BM25) | 0.59 | 0.81 | 0.75 | 0.68 |
| dense (bge-small-en-v1.5) | 0.71 | 0.90 | 0.87 | 0.79 |
| hybrid (reciprocal rank fusion) | 0.71 | 0.90 | 0.88 | 0.78 |

Dense and hybrid retrieval find a correct fact more often when the question uses different words from the source. The 95% intervals overlap (for example hit@5 0.81 [0.71-0.91] against 0.90 [0.81-0.97]), so this is a likely gain, not a proven one. On the development questions keyword search is as good or better on hit@5 and recall@12 (hit@5 1.00 against 0.95), though not on hit@1 or MRR, which is expected because it was tuned on them. Gold IDs were labelled by one person (the author), so they carry that person's judgement.

### End to end with a local model (`python -m eval.run_eval --provider <name>`). The 30 questions in `eval/questions.jsonl` (11 single fact, 4 multiple fact, 4 climate, 2 species, 4 source conflicts, 4 unanswerable, 1 prompt injection) run through retrieval, the model and the validator. Scoring is mechanical: required values present, expected evidence cited, unanswerable questions refused, plus how many of the model's fact sentences the validator had to reject on the first attempt (a proxy for hallucination: invented IDs, numbers or names not in the cited text). Runs checkpoint after every answer and resume if interrupted.

Rows are copied from [docs/RESULTS.md](docs/RESULTS.md); brackets are 95% intervals. Every model run uses Qwen2.5-3B-Instruct (4-bit) at temperature 0 with 8 facts shown, on a laptop CPU.

| Run | passed | false refusals | refusal accuracy | first attempt failures |
|---|---|---|---|---|
| No model: quote the top sources (`extractive`, keyword retrieval) | 50% (15/30) [33-67] | 0% (0/25) [0-13] | 20% (1/5) [4-62] | 0% (0/83) [0-4] |
| Ollama, keyword retrieval | 77% (23/30) [59-88] | 16% (4/25) [6-35] | 100% (5/5) [57-100] | 8% (3/36) [3-22] |
| Ollama, hybrid retrieval | 67% (20/30) [49-81] | 20% (5/25) [9-39] | 100% (5/5) [57-100] | 15% (5/34) [6-30] |
| Ollama, hybrid, after a prompt change that was then reverted | 77% (23/30) [59-88] | 12% (3/25) [4-30] | 100% (5/5) [57-100] | 11% (3/28) [4-27] |
| Ollama, hybrid, with a table check that was then reverted | 67% (20/30) [49-81] | 24% (6/25) [11-43] | 100% (5/5) [57-100] | 20% (7/35) [10-36] |
| llama.cpp, hybrid (earlier run, no constrained decoding) | 48% (14/29) [31-66] | 42% (10/24) [24-61] | 80% (4/5) [38-96] | 27% (12/45) [16-41] |

What this says:

- The local model declined every unanswerable or injection question (5 of 5, against 1 of 5 for quoting the sources) and answered most answerable ones. With only five such questions the intervals overlap ([57-100] against [4-62]; paired p = 0.125), so the refusal difference is not proven either. Its pass rate is higher than the baseline's, but the 95% intervals overlap, so this is **not claimed as a proven gain**. A paired test on passes gives p = 0.039 for the keyword run, but that comparison was not preregistered and is one of several.
- Keyword and hybrid retrieval do not differ significantly end to end (paired exact McNemar test: passes p = 0.375, false refusals p = 1.000).
- A prompt and schema change aimed at false refusals was tried after tuning on a separate development set of 25 questions. It did not meet the preregistered rule for keeping a change (development false refusals stayed at 1 of 20) and was run once on the frozen 30 anyway, as a recorded deviation. There it lowered false refusals from 5 to 3 of 25 (p = 0.688, not significant). A manual reading of the changed answers found 2 contradicted sentences against 1 before, and a rule fixed in advance said to revert in that case, so it was reverted. Details are in [docs/RESULTS.md](docs/RESULTS.md).
- The errors that get through quote a number that is in the cited table but belongs to another month or row (for example the driest month given as the wettest). A table aware check was built for this and tested against a fresh question set ([docs/research/PREREGISTRATION_2.md](docs/research/PREREGISTRATION_2.md)). Its first attempt rejections were all wrong claims (3 on tuned dev questions, 1 frozen, 1 sealed), but in one sealed repair it rejected an answer with the right month and value because the sentence called that value annual, and it changed no aggregate result significantly. Tuning also relaxed the name check for month names, a deviation from the preregistration. It was reverted because the frozen run with it on contained one new unsupported sentence that has nothing to do with tables; the rule written in advance did not separate run to run variation from an effect of the check. Details are in RESULTS.

Fresh held out questions (`eval/questions_heldout.jsonl`, 10 sealed, each configuration run once, hybrid retrieval):

| Run | passed | false refusals | refusal accuracy |
|---|---|---|---|
| Table check off (one question errored) | 78% (7/9) [45-94] | 0% (0/6) [0-39] | 100% (3/3) [44-100] |
| Table check on | 70% (7/10) [40-89] | 14% (1/7) [3-51] | 100% (3/3) [44-100] |

Paired on the 9 questions scored in both, the two configurations give identical results (McNemar p = 1.000).
- Predictions for these runs were written before they ran ([docs/research/PREREGISTRATION.md](docs/research/PREREGISTRATION.md)). Most missed because they were anchored on the earlier llama.cpp run, which served the same weights without constrained decoding and did much worse. The cause of that difference was not isolated.
- With 30 questions the intervals are wide, and these questions were used to diagnose problems, so they are a regression guard, not a benchmark. No judge model was run (the machine had less than 16 GB of RAM), so groundedness is measured only by the mechanical checks. Timings were taken on a heavily loaded laptop and are left out of this table; they are in RESULTS.

### Library relevance (`pytest tests/test_library_relevance.py`). 106 questions, 52 answerable and 54 not, guard the no-model library search against returning facts for off topic questions. Part of this set was used for tuning (see "Library search quality").

## Library search quality

The library's search is lexical (BM25 with a small stemmer and handwritten synonyms). A question is answered only when the facts cover enough of its words, and a question that names something the library has never seen, such as a capitalised place or an unfamiliar noun, is refused. Matches that cover only part of a question are labelled as the closest entries.

`eval/library_relevance.jsonl` holds 106 questions (52 the library can answer, 54 it cannot) and `tests/test_library_relevance.py` guards them.

| Measure | Before the fix | After |
|---|---|---|
| Out of scope questions that still returned facts (20 questions) | 10 of 20 | 1 of 54 in the saved set |
| Answerable questions that returned nothing | not measured | 0 of 52 in the saved set |
| First run on 42 fresh questions, before tuning on them | | 1 of 20 false positives, 6 of 22 answerable empty |

Both sets were tuned against, so the "after" figures are regression checks, not an independent score. The fresh question row is the better estimate: roughly 5% wrong answers to out-of-scope questions and about a quarter of answerable questions missed, before the later fixes for synonyms. A held out set written by someone else would be a better test. Only the saved set is rechecked by tests; the other counts in this table were recorded once.
