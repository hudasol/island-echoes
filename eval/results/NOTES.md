## Analysis of the October 2026 local model runs

Hand written; the tables above are generated. Predictions are from `docs/PREREGISTRATION.md`, committed before any
of these runs. No judge model was run (the machine has 13.9 GB of RAM, below the 16 GB set in the plan), so
groundedness (G) and hallucination (H) are the mechanical proxies defined there: H is the share of first-attempt
fact sentences failing a validator check, G is 1 − H. Neither measures semantic faithfulness.

### Conditions

- Qwen2.5-3B-Instruct, 4-bit, through Ollama 0.40.4 with JSON schema constrained output, temperature 0, 8 facts
  shown per question, on a laptop CPU (Ryzen 7 7730U).
- Other workloads kept the CPU near 100% and RAM nearly full throughout, and runs A and B shared the model server
  (two parallel slots). Timings in these tables are therefore pessimistic and not comparable with the earlier
  llama.cpp row.
- The earlier `qwen25-3b-hybrid` row used the same weights through llama.cpp without constrained decoding. The
  Ollama rows differ from it in serving stack as well as date, so the two are not a controlled comparison.

### Predictions against measurements

| Prediction | Predicted | Measured | Result |
|---|---|---|---|
| R: retrieval reproduces stored values | exact | exact (two tied pairs reordered, no metric changed) | hit |
| A (bm25): H | 27%, range 15 to 40% | 8.3% (3/36) | miss, lower |
| A: G | 73%, range 60 to 85% | 91.7% (33/36) | miss, higher |
| A: false refusals | 40%, range 25 to 55% | 16.0% (4/25) | miss, lower |
| A: refusal accuracy | 4/5, range 3 to 5 | 5/5 | hit |
| A: passed | 50%, range 35 to 65% | 76.7% (23/30) | miss, higher |
| B (hybrid): H | 27%, range 15 to 40% | 14.7% (5/34) | miss, just below range |
| B: G | 73%, range 60 to 85% | 85.3% (29/34) | miss, just above range |
| B: false refusals | 40%, range 25 to 55% | 20.0% (5/25) | miss, lower |
| B: refusal accuracy | 4/5, range 3 to 5 | 5/5 | hit |
| B: passed | 50%, range 35 to 65% | 66.7% (20/30) | miss, just above range |
| 1. A and B do not differ beyond their intervals | no difference | false refusals 21/25 against 20/25 answered, McNemar p = 1.000; passes 23/30 against 20/30, p = 0.375 | hit |
| 2. At most one errored question per run | at most 1 | 0 in A, 0 in B | hit |
| 3. Same refusal causes as the earlier llama.cpp run | same causes | missing citations, the main earlier cause, did not occur; IDs in the text and citations to the wrong item dominated; answers marked unanswered recurred | miss |
| C (after the change): H | not above B (14.7%); range 10 to 35% | 10.7% (3/28) | hit |
| C: G | range 65 to 90% | 89.3% (25/28) | hit |
| C: false refusals | 15%, range 5 to 30% | 12.0% (3/25) | hit |
| C: refusal accuracy | at least 4/5 | 5/5 | hit |
| C: passed | 60%, range 45 to 75% | 76.7% (23/30) | miss, higher |
| 2 (run C). At most one errored question | at most 1 | 0 in the final file; Q16 was rerun on resume (see below) | hit |
| 4. C lowers false refusals against B; claimed only if the paired test supports it | lower, probably not significant | 22/25 against 20/25 answered (4 better, 2 worse), McNemar p = 0.688 | point estimate as predicted; no improvement is claimed |

The predictions were anchored on the earlier llama.cpp run and were too pessimistic. The same weights served through
Ollama with schema constrained output refused less and failed the validator less often. The likely reason is the
serving stack (constrained decoding and the chat template), but this was not isolated, so it is a hypothesis.

### Why answerable questions were refused (runs A and B)

Read from the saved records of the frozen runs, before any change was made:

1. **Evidence IDs written into the sentence.** "According to PIT-036, there are about 1,568..." The digits of the ID
   fail the number check, the sentence is dropped, and the repair attempt then gives up (Q09 in B, Q23 in A).
2. **A correct value cited to the wrong item.** The 1984 vote figures were cited to `COC-216` instead of `COC-020`
   (Q13 in B); the 1927 claim was cited to `BOU-018` instead of `BOU-019` (Q15 in B). The validator is right to
   reject these, and the repair retry usually produced a long voice sentence instead of a corrected citation.
3. **Facts placed in voice sentences**, mostly in repair attempts, which are then dropped (Q22, Q13, Q15 in B).
4. **A cited, correct answer marked as not answered** by the model (Q14 in both runs, Q17 in A).
5. **A misspelt name** ("Hajir" for "Hajhir", Q22). The validator is right to reject it.

Retrieval was not the cause: in every falsely refused question, the expected fact was among the 8 items shown, except
two of the three expected items for Q15 in B. Missing citations, the main problem in the earlier llama.cpp run,
did not occur at all under Ollama's constrained decoding.

### The change that was tried (run C)

Tuned only on `eval/dev_questions.jsonl`; `app/chat/grounding.py` is unchanged and its tests pass unchanged.

- The prompt says evidence IDs go only in `cites`, that any sentence with a number, date, name or place is a fact
  sentence, and that `answered` is true whenever a cited fact sentence states what was asked.
- For Ollama, the output schema is narrowed per request: a fact sentence must cite one to three of the retrieved
  IDs, a voice sentence none.
- The repair prompt names the retrieved item that contains a rejected number, and asks for IDs to be removed from the
  text. These hints never mark a sentence as passing; the retry is checked again in full.
- If the repair attempt keeps fewer passing fact sentences than the first attempt, the first attempt is used. Only
  sentences that passed every check are shown either way.

### Results of the change, and why it was reverted

| | B (before) | C (after) | Paired test |
|---|---|---|---|
| Answerable questions answered | 20/25 | 22/25 | 4 better, 2 worse, p = 0.688 |
| Questions passed | 20/30 | 23/30 | 4 better, 1 worse, p = 0.375 |
| Refusal accuracy | 5/5 | 5/5 | no change |
| First-attempt failures (H) | 14.7% (5/34) | 10.7% (3/28) | |

None of these differences is statistically supported. On the development set the change also left false refusals
unchanged (1/20 before and after; the remaining case is a retrieval miss), so it did not meet the preregistered
rule for keeping a change; it was run on the frozen 30 anyway as the planned single before and after measurement,
and that is a recorded deviation.

**Manual check of shown sentences.** Because the mechanical proxy cannot see a wrong claim built from correct words,
every shown fact sentence that differed between the runs was read against its cited evidence (one unblinded
reader, so a check rather than a measurement):

| Set | Sentences only in the earlier run | Sentences only in the later run |
|---|---|---|
| Development (D0 against D1) | 17: all supported | 16: 15 supported, 1 contradicted (D08 gives the August value 8.2 as September's) |
| Frozen (B against C) | 24: 22 supported, 1 contradicted (Q20, misreads the GBIF counts), 1 partly supported (Q05) | 22: 19 supported, 2 contradicted (Q20 as in B; Q18 names the driest month, March, as the wettest), 1 partly supported (Q05) |

Both contradicted sentences that are new in C and D1 passed the validator because the number they quote does appear
in the cited table, only for a different month. The rule fixed before run C was read says to revert the change if C
has more unsupported or contradicted sentences than B. It has (2 against 1), so the change was reverted on main
(`ae62ae4`); the code on main again matches the configuration of run B (the deployed instance runs no model). With one sentence of difference this is not evidence
that the change causes errors, only that it was not shown to be safe.

**Side effect.** Under the narrowed schema the model emits an empty voice sentence whenever it declines, which costs
a needless repair call.

**Run C conditions.** The session was interrupted after 18 answers. The runner resumed from its checkpoint with the
same code; 17 answers were kept and one record (Q16, most likely the request in flight at the interruption) was
answered again. The resumed part ran on a quieter machine, so run C timings mix two load conditions.

### Provenance corrections

- Runs A, B and C record a later commit than the code they ran, because the runner stamped the commit when a run
  finished: A and B ran the code of `cd7fd79` (recorded `54791c9` and `bbf0729`, which changed only documentation);
  C ran the code of `de39e10` (recorded `575380e`). The runner now stamps the commit at the start.
- `dev-candidate-1` records `b48847c`, a commit on a local branch that was not published. Its code is the same as
  `0e97570` plus `de39e10` on main, except for one import style change in a test.

### What this means for the next step

The remaining errors are of a kind the mechanical validator cannot catch: a value that appears in the cited table but
belongs to a different row or month. A table-aware check (the number must sit next to the month or field the sentence
names) or a small entailment model would target them directly. Prompt changes alone moved the false refusal rate
within noise and did not reduce these errors.

## Analysis of the label aware number check (18 October 2026)

Predictions and the keep or revert rule are in `docs/PREREGISTRATION_2.md`, committed before the check was built.
All runs: Qwen2.5-3B-Instruct through Ollama, hybrid retrieval, 8 facts, temperature 0. The check was reverted under
that rule; the code on main again matches run B.

### What the check did

It bound each number quoted from a NASA POWER table to the month, annual period or parameter written next to it,
and required a month called wettest, driest and so on to be its row's maximum or minimum (code at `5c42102`, reverted
in `c308b71`; the replay script is at `ff9d866`). On first attempts it fired on 5 questions and each claim it rejected was wrong when read against the table: dev
H02, H04 and H05 (tuned against: wrong driest, coldest and wettest months), frozen Q18 (October called the wettest
month, at the annual value 7.75; the wettest is August, 13.4) and sealed H06 (October called the most humid month, at
November's value 79.43). In one repair attempt it also rejected a sentence with the right answer in the wrong words:
sealed H06's retry said "most humid in April (APR) with an annual value of 80.92%". April and 80.92 are correct, but
80.92 is April's value, not the annual one (79.33), so the rejection is right by the letter and cost a correct month
answer. That is the one sealed false refusal with the check on.

The replay over 264 stored fact sentences (`eval/results/table_check_replay.md`) rejected 3 distinct sentences, all
genuine errors on reading, and no supported sentence.

During tuning on the 20 dev questions, two changes were made: failure messages name the correct cell, which did not
help, and a month written in full ("August") is accepted by the name check when its abbreviation labels a cited
table column, which removed a false rejection that the earlier validator also makes (dev H01 is refused with the
check off for this reason).

**Deviation from the preregistration.** The preregistration says the check "only adds failures; it never makes a
failing sentence pass". The month name change does make some name check failures pass, so the configuration run on
the sealed and frozen questions differs from runs S-off and B by more than the check. The dev gain from 13/20 to
15/20 comes from this relaxation (H01) and from variation between runs (H15, a prose question), not from the check
itself. The replay ran before this change and tests only the check.

**First attempt failure rate (H) with and without the new issue kinds**, as promised in the preregistration: frozen
with the check, 20% (7/35) with them and 17% (6/35) without; sealed with the check, 1/7 and 0/7; dev iteration 3, 6/19
and 3/19. Only the figures without the new kinds are comparable with runs where the check is off.

**Exposure of the sealed baseline.** The sealed run with the check off was committed at `7c36932` (03:06) and, through
`b87b837` (03:28), rendered into RESULTS.md before dev iteration 3 ran and before the configuration was frozen. Its
output was not opened during tuning, but the repository cannot show that. It is a run with the check off, so it could
not have guided the check's tuning directly.

### Predictions against measurements

| Prediction | Predicted | Measured | Result |
|---|---|---|---|
| P1. The replay rejects D08 (D1) and Q18 (C) | both rejected | both rejected, plus C Q19 first attempt (also an error) | hit |
| P2. At most 2 false rejections in the replay | at most 2 | 0 | hit |
| P3. Sealed: passes and false refusals differ by at most 1; none significant | small difference | paired on 9: passes 7/9 both, answered 6/6 both, refusals 3/3 both, p = 1.000 | hit |
| P4. Frozen with the check against run B: passed 18 to 23, false refusals 3 to 7, refusal accuracy 5/5, nothing significant | as stated | passed 20/30 (B 20/30), false refusals 6/25 (B 5/25), refusal accuracy 5/5, McNemar p = 1.000 for both | hit |
| P5. The check fires on 1 to 4 frozen questions | 1 to 4 | 1 (Q18) | hit |
| P6. No significant aggregate gain | none | none | hit |

The sealed baseline has 9 scored questions: H06 errored there after an Ollama read timeout, and a single logged
repeat with the check off (`eval/results/heldout-retry/`) timed out again in the repair step, so it stays excluded.

### Keep or revert

| Condition | Result |
|---|---|
| 1. No new contradicted or unsupported shown sentence in a check on run | **failed.** Sealed: the differing shown sentences (H20 in both runs, and H06 "The annual value is 79.33%." in the check on run) are all supported. Frozen: of 13 sentences only in the check on run, 11 are supported, 1 is partly supported (Q14 widens "0 living or captive animals inside the search box" to "no living or captive Pinta Island tortoises have been recorded") and 1 is unsupported (Q24 adds "Pitcairn is the only inhabited island of its territory", which its cited fact does not say). Of 10 sentences only in run B, 9 are supported and 1 is contradicted (Q20, which the check on run states correctly). |
| 2. Answered not lower by more than 1 (sealed) or 2 (frozen); refusal accuracy not lower | passed (sealed 6/6 against 6/6; frozen 19/25 against 20/25; refusal accuracy equal) |
| 3. At most 2 false rejections in the replay | passed (0) |
| 4. Tests pass unchanged, with and without a dummy key | passed |

Condition 1 failed, so the check was reverted. The unsupported Q24 sentence cites prose, not a table, so the check
did not cause it: it comes from variation between runs (run B was made two days earlier, under different load and
with two parallel model slots). The rule compares a new run with an old one and cannot separate such variation from
an effect of the change. A fairer rule would compare check on and check off runs made the same day on the same
questions, and would count unsupported sentences in both directions. That design change is recorded here rather than
applied after the fact.

### Dev results (tuned against)

| Run | passed | false refusals | refusal accuracy |
|---|---|---|---|
| dev, check off | 13/20 | 3/15 | 4/5 |
| dev, check on, iteration 1 | 13/20 | 6/15 | 4/5 |
| dev, check on, iteration 2 (correct cell named) | 13/20 | 6/15 | 4/5 |
| dev, check on, iteration 3 (table months accepted) | 15/20 | 4/15 | 4/5 |

With the check off, dev H02, H04 and H05 showed a wrong month as the answer; with the check on they were declined
instead. The 3B model rarely recovered the right month on repair even when the failure message named it.
