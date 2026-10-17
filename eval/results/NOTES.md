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
every shown fact sentence that differed between the runs was read against its cited evidence (by the agent, not
blind, so a check rather than a measurement):

| Set | Sentences only in the earlier run | Sentences only in the later run |
|---|---|---|
| Development (D0 against D1) | 17: all supported | 16: 15 supported, 1 contradicted (D08 gives the August value 8.2 as September's) |
| Frozen (B against C) | 24: 22 supported, 1 contradicted (Q20, misreads the GBIF counts), 1 partly supported (Q05) | 22: 19 supported, 2 contradicted (Q20 as in B; Q18 names the driest month, March, as the wettest), 1 partly supported (Q05) |

Both contradicted sentences that are new in C and D1 passed the validator because the number they quote does appear
in the cited table, only for a different month. The rule fixed before run C was read says to revert the change if C
has more unsupported or contradicted sentences than B. It has (2 against 1), so the change was reverted on main
(`ae62ae4`); the deployed code is the configuration of run B. With one sentence of difference this is not evidence
that the change causes errors, only that it was not shown to be safe.

**Side effect.** Under the narrowed schema the model emits an empty voice sentence whenever it declines, which costs
a needless repair call.

**Run C conditions.** The session was interrupted after 18 answers. The runner resumed from its checkpoint with the
same code; 17 answers were kept and one record (Q16, most likely the request in flight at the interruption) was
answered again. The resumed part ran on a quieter machine, so run C timings mix two load conditions.

### What this means for the next step

The remaining errors are of a kind the mechanical validator cannot catch: a value that appears in the cited table but
belongs to a different row or month. A table-aware check (the number must sit next to the month or field the sentence
names) or a small entailment model would target them directly. Prompt changes alone moved the false refusal rate
within noise and did not reduce these errors.
