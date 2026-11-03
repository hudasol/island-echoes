# Preregistration 3: sealed evaluation, lossless validation and a climate tool, November 2026

Written and committed before any answering system is run on the sealed test questions. The question files and their
SHA256 hashes (`eval/v3/SHA256SUMS`) are committed in the same commit. After the first run on the sealed set this file
is not edited; changes are recorded only as dated addenda at the end.

## Questions asked

1. Does replacing a rejected sentence with the verbatim cited source sentence (the "extractive fallback") lower false
   refusals compared with dropping the sentence, without letting unsupported sentences into the final answer?
2. Does a deterministic route for numeric climate questions remove wrong month and wrong row errors?
3. How do the earlier headline claims hold on a larger set the author did not tune on?
4. How does model size (1.5B, 3B, 7B, all openly licensed) change the result?

## Data

All items in the sealed and development files are **synthetic**: the question text was written by a local model
(Qwen2.5 1.5B Instruct) from a randomly chosen fact or from templates, and the gold answer is constructed from the
fact file the question was made from. The file names, the `synthetic` field on every item, and every table header that
reports them say so. A different local model (Phi 3.5 mini Instruct, MIT licence) labelled which facts answer each
retrieval type question without seeing the gold; agreement between the two is **model to model**, reported in
`eval/v3/labeller_agreement.json`, and is not a human check. The writer is smaller than the main answerer (3B), which may
favour the 3B answerer when it shares phrasing habits with the writer; this is a stated limit, not a measured one.

| File | Items | Use |
|---|---|---|
| `eval/v3/test.jsonl` | 150 (48 single fact, 15 multiple fact, 30 climate, 10 species, 5 source conflict, 15 unanswerable, 15 not in the library, 12 prompt injection; 112 answerable, 38 should refuse) | sealed, run once per system |
| `eval/v3/dev.jsonl` | 55 | development: routing rules of the climate tool may be tuned here only |
| `eval/questions.jsonl` (frozen 30), `eval/questions_heldout.jsonl`, retrieval gold | as before | regression only; their results are not rewritten |

Set construction seeds: test 20261103, development 20261104. No question appears in both files. Questions were
filtered if they named a source ("Wikipedia", "FishBase"). Counts above are the final counts after filtering.

## Arms

All arms share one stored generation per question (temperature 0, a fixed model file and prompt), so arms differ only in
what happens after generation. The full pipeline is run once on the sealed set per model with default settings, storing
the first attempt, the repair attempt and the validator's issues. Arms are derived offline by `eval/arms.py`.

| Arm | Definition |
|---|---|
| refuse | always refuse (floor) |
| closed | the model without sources |
| unvalidated | retrieval and model, no validator |
| drop | retrieval, model, validator, one repair, rejected sentences dropped (the 1.1 behaviour) |
| extractive | as drop, but a sentence still rejected after the repair is replaced by the verbatim source sentence it was meant to cite |
| drop+climate, extractive+climate | the above with the deterministic climate route answering numeric POWER questions before the model |

Main model: Qwen2.5 3B Instruct, Q4_K_M, llama.cpp, hybrid retrieval, 8 facts shown, 2 CPU threads, temperature 0.
Further models: Qwen2.5 1.5B Instruct (smaller, Apache 2.0) on the full sealed set if time allows; Qwen2.5 7B Instruct (larger, Apache
2.0) on a stratified subsample of the sealed set, because its speed on 2 vCPU and 8 GB of memory allows no more.
Models above 7B are excluded by the memory limit of the machine (about 8 GB of RAM including the index).

## Measures (computed by the existing scorer)

Pass rate; false refusals (of 112 answerable); refusal accuracy (of 38 that should refuse); unsupported sentences in the
final answer (a sentence whose number or name is in none of its cited evidence, checked by the validator and read by
hand for a sample); key fact recall (of 148 required values); for climate items, wrong month or wrong row errors.
Intervals are Wilson 95%. Paired comparisons use the exact McNemar test on the same questions. No correction for the
number of comparisons is applied; they are listed in the order below and a result is called established only below 0.05
on the planned comparisons C1 to C3.

Planned comparisons: C1 extractive against drop (pass rate, false refusals); C2 climate route on against off (climate
items, then all items); C3 unvalidated against drop (unsupported sentences, false refusals). Everything else is
descriptive.

## Predictions (ranges fixed before the run)

| ID | Prediction | Range |
|---|---|---|
| P1 | drop arm, 3B: pass rate on the sealed set | 55% to 75% |
| P2 | drop arm, 3B: false refusals of 112 answerable | 20% to 40% |
| P3 | extractive arm lowers false refusals by at least 10 percentage points against drop | yes, with at most 12% false refusals remaining |
| P4 | extractive arm: unsupported sentences in the final answer | 0 of all kept sentences by construction, because kept sentences are source sentences; at most 2 if the sentence selection errs |
| P5 | refusal accuracy of extractive against drop | no more than 5 points lower |
| P6 | closed book, 3B: pass rate | 5% to 20% |
| P7 | unvalidated, 3B: unsupported sentences | 3% to 12% of fact sentences, which is more than drop and extractive |
| P8 | climate route answers at least 85% of the 30 sealed climate items | 26 to 30 of 30 |
| P9 | wrong month or row errors among the 30 climate items | model alone 3 to 9, with the route 0 |
| P10 | model to model agreement, exact match of the supporting fact set between the two labellers | at least 85% |
| P11 | 7B subsample outperforms 3B on pass rate by at least 5 points | yes |
| P12 | 1.5B full pipeline passes fewer questions than 3B | yes, by 5 to 25 points |

**The prediction most likely to fail is P10.** A second labeller shown twelve candidates tends to mark neighbouring
facts as supporting, so exact set match is likely below 85%; the more informative figures are "covers gold" and mean
Jaccard overlap, which are also reported. P11 is the next most likely to fail, because the subsample is small and its
interval will be wide.

## Success and failure criteria

* Extractive fallback is **kept as the new default** in 1.2.0 only if all hold: false refusals fall by at least 10 points
  against drop (C1), unsupported sentences in the final answer do not increase, and refusal accuracy falls by no more than
  5 points. Otherwise the setting stays available and off by default, and the result is reported as not meeting the rule.
* The climate route is **kept as the new default** only if it answers at least 85% of sealed climate items correctly,
  introduces no new wrong answer on non climate items, and does not lower the pass rate on any other type. Otherwise it
  stays off by default.
* If neither is kept, the 1.1 behaviour remains the default and every number in the README is regenerated from stored runs.

## Exact commands

```bash
export LLAMACPP_MODEL_PATH=/tmp/claude-0/models/qwen2.5-3b-instruct-q4_k_m.gguf
# full pipeline trace, 3B
python -m eval.run_eval --questions eval/v3/test.jsonl --provider llamacpp --retrieval hybrid --k 8 \
    --label v3-qwen25-3b-full --out eval/results/v3/qwen25-3b-full
# closed book and baselines
python -m eval.run_eval --questions eval/v3/test.jsonl --system closed-book --provider llamacpp --retrieval hybrid --k 8 \
    --label v3-qwen25-3b-closed --out eval/results/v3/qwen25-3b-closed
python -m eval.run_eval --questions eval/v3/test.jsonl --system refuse-all --out eval/results/v3/refuse-all
# arms derived from the stored trace
python -m eval.arms eval/results/v3/qwen25-3b-full.json --arm unvalidated --questions eval/v3/test.jsonl --out eval/results/v3/arm-unvalidated.json
python -m eval.arms eval/results/v3/qwen25-3b-full.json --arm drop --questions eval/v3/test.jsonl --out eval/results/v3/arm-drop.json
python -m eval.arms eval/results/v3/qwen25-3b-full.json --arm extractive --questions eval/v3/test.jsonl --out eval/results/v3/arm-extractive.json
# climate overlay: add --climate to each arms command, then score every derived file with
python -m eval.run_eval --from-run <derived.json> --questions eval/v3/test.jsonl --out <scored>
```

The 1.5B run and the 7B subsample repeat the first command with the matching model file and label. The frozen 30
regression is re-run only if time remains, with the same flags, and is reported next to its earlier numbers.

## Keep or revert rule for code

The fallback, the climate route and the month name flag are already in the code behind settings that default to the 1.1
behaviour. A default changes only by the criteria above. Nothing is tuned on the sealed set; routing rules for the
climate tool were written against the development set and the frozen 30, and any further change after the first sealed
run is made, if at all, as a dated addendum and reported as post hoc.

## Known weaknesses stated in advance

Synthetic questions made from the fact files measure whether the system finds and states the fact it was built around;
they overstate performance on free form questions from people. The gold is constructed, not human labelled. The second
labeller is a model. The 7B subsample is small. Wall clock limits prevent repeated seeds; temperature 0 makes a rerun
reproduce the stored answers, so there is no estimate of generation variance.

## Addenda

Addendum 1, 3 November 2026, before any system was run on the sealed set. The sealed and development question files, the
second labeller output and their SHA256 hashes (`eval/v3/SHA256SUMS`) are committed in the commit that adds this addendum;
the draft of this file had been committed earlier, before the hashes existed. No answering system has been run on either
file at this point. Second labeller result, recorded here because it is a measured quantity of the sets and not of any
system: of 68 retrieval type items, the labeller's set equals the constructed gold in 45 (66%), covers it in 58 (85%), and the mean Jaccard
overlap is 0.775; in 9 items the gold fact was not among the 12 candidates it was shown. This is a miss on P10 (at least
85% exact match) and is reported as such; it does not change any other prediction.

Addendum 2, 3 November 2026, written after the 3B run on the sealed set had started and before any result of it was read.
Measured speed on the 2 vCPU machine is about 150 to 180 seconds per question for the 3B model, so the plan above for the
other runs cannot finish. The following replaces the plan for the three secondary runs; the primary 3B run on all 150
questions is unchanged.

| Run | Questions | Fixed by |
|---|---|---|
| Qwen2.5 3B, closed book | 50 | every third question of `test.jsonl` in file order (`eval/v3/subset50.txt`; 16 single fact, 10 climate, 5 multiple fact, 5 unanswerable, 5 not in the library, 4 prompt injection, 3 species, 2 source conflict) |
| Qwen2.5 1.5B, full pipeline | the same 50 | `eval/v3/subset50.txt` |
| Qwen2.5 7B, full pipeline | 30 | every fifth question (`eval/v3/subset30.txt`; 9 single fact, 6 climate, 3 multiple fact, 3 unanswerable, 3 not in the library, 3 prompt injection, 2 species, 1 source conflict) |

Comparisons with the 3B model for these runs use the same questions from the 3B run, as paired tests on that subset.
With 30 and 50 questions the intervals are wide, and P11 and P12 will be reported with that caveat. If time runs out, runs
are stopped in the order 7B, then 1.5B, and what was completed is reported with the exact count.
