# Preregistration 2: a label aware number check, October 2026

Written and committed before the check is built and before any run of the new question set. The design was
motivated by two errors found in earlier runs (development D08 and frozen Q18 in run C), so those two cases are
known to the author; they are listed below as expected catches, not as evidence.

## Problem

The grounding validator accepts a number if it appears anywhere in the cited evidence. NASA POWER evidence is a
table of twelve monthly values and an annual value per parameter, so a sentence can quote the right table and the
wrong cell. Two such errors passed the validator: "In September ... 8.2 m/s" (8.2 is the August value; September is
8.15) and "March has the most rain ... 1.42 mm/day" (March is the driest month; August, 13.4, is the wettest).

## The check

For each fact sentence whose cited evidence contains POWER table rows (`Name (CODE, unit): JAN v, ..., ANN v`):

1. **Binding.** A number in the sentence that occurs as a value in a cited row is bound to the nearest period label
   in the sentence: a month (full name or three letter abbreviation) or the annual period ("annual", "a year", "per
   year", "each year", "yearly", "ANN"). If the sentence names a parameter (temperature, maximum or minimum
   temperature, rain or precipitation, wind, humidity), only the matching rows count. The bound number must equal
   that row's value for that label; otherwise the sentence fails with the label the number actually belongs to.
   Numbers with no period label in the sentence are not checked by this rule.
2. **Superlatives.** If the sentence names exactly one month together with a word such as wettest, driest,
   warmest, coldest, windiest, most, least, highest or lowest, that month must be the maximum (or minimum) of the
   twelve monthly values in at least one matching row. Rows are narrowed by the parameter named and, when the
   sentence quotes a table value, by the row that holds it.

Out of scope for this version: years and periods inside prose facts, unit conversions, and number words. The check
only adds failures; it never makes a failing sentence pass. A setting (`TABLE_CHECK`, default on if kept) lets runs
switch it off for comparison.

## Measurements

| ID | What | Questions |
|---|---|---|
| P | Replay: apply the check to every first attempt and shown fact sentence stored in the existing runs (A, B, C, D0, D1), then classify each rejection by reading it against its evidence | stored runs |
| DEV | Tuning on the 20 development questions of `eval/questions_heldout.jsonl`, check off and on | 20 |
| S-off, S-on | The 10 sealed questions, each configuration run once | 10 |
| F-on | The frozen 30, check on, run once; compared with run B (check absent), which it otherwise matches | 30 |

All runs: Qwen2.5-3B-Instruct through Ollama 0.40.4, hybrid retrieval, k = 8, temperature 0. The frozen 30 were
used to diagnose earlier problems, so F-on is a regression check, not a held out result. The sealed 10 are held out
from all tuning. Wilson 95% intervals and exact McNemar tests on paired questions are reported.

Mechanical note: the check adds a new kind of validator failure, so the first attempt failure rate (H) is not like
for like between check off and check on. H is reported both with and without the new issue kind.

## Predictions

| ID | Prediction |
|---|---|
| P1 | The replay rejects the two known errors (D08 in D1, Q18 in C). |
| P2 | Across all stored sentences the replay rejects at most 2 sentences that are in fact supported (false rejections). |
| P3 | On the sealed 10, S-on and S-off differ by at most 1 question in passes and at most 1 in false refusals; no difference is significant. |
| P4 | F-on against run B: passed 18 to 23 of 30 (B: 20), false refusals 3 to 7 of 25 (B: 5), refusal accuracy 5 of 5. No difference is significant. |
| P5 | The check fires (at least one first attempt rejection of the new kind) on 1 to 4 of the 30 frozen questions. |
| P6 | Aggregate metrics will not show a significant gain. Any value of the check lies in the specific errors it catches. |

## Keep or revert rule

The check is kept on main only if every condition holds. Otherwise it is reverted with a new commit and all results
stay recorded.

1. **No new contradiction.** A manual read (one unblinded reader) of every shown fact sentence that differs between
   S-off and S-on, and between run B and F-on, finds no contradicted or unsupported sentence in the check on runs
   that is absent from the matching check off run. Any such sentence means revert.
2. **Refusals do not rise materially.** Answerable questions answered: S-on not lower than S-off by more than 1;
   F-on not lower than run B by more than 2. Refusal accuracy is not lower in either comparison.
3. **Few false rejections.** In the replay (P), at most 2 supported sentences are rejected.
4. **Tests.** Every existing test passes unchanged, with and without a dummy Anthropic key set.

## How misses will be reported

Every prediction will be listed against its measured value as hit or miss in `docs/RESULTS.md`. Runs are repeated
only after an infrastructure failure, and that is logged. Development numbers are labelled as tuned against.
