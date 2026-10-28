# Evaluation log, 16 to 18 October 2026

Record of the evaluation session of 16 and 17 October 2026 on a laptop. Times are local. Entries are in the order they happened.

## Phase 0: preflight

- 05:05 Cloned `hudasol/island-echoes` (main at `25b6d06`) into a fresh folder beside the old copy, which is not a
  git checkout. Copied `.env` across without reading it; confirmed it is ignored by git (`git check-ignore`).
- Machine: AMD Ryzen 7 7730U (16 threads), integrated graphics, 13.9 GB RAM (0.6 GB free at the start, with WSL
  and other applications open), 77.4 GB free on C:.
- Python 3.13.0 virtual environment; installed `requirements-dev.txt` and `requirements-ml.txt` (fastembed 0.9.0,
  onnxruntime 1.31.0, numpy 2.5.4, fastapi 0.143.2).
- pytest: 227 passed, 1 failed on the first run. The failure (`test_factory_selects_providers_and_validates_config`)
  expects no Anthropic key, but `Settings` reads the local `.env`, which holds one. The test was not changed. Every
  run in this session sets `ANTHROPIC_API_KEY` to an empty string in the process environment, which both makes the
  suite hermetic (228 passed) and guarantees the unfunded key is never used. ruff: clean.
- Decision: the development set needed a way to run without touching the frozen 30, so `eval/run_eval.py` gained a
  `--questions` option (commit `757ad40`).

## Phase 1: local model

- 05:12 `winget install Ollama.Ollama` stalled: the Delivery Optimization download stayed at 0 bytes for 11 minutes.
  Stopped it and downloaded the same installer URL listed in the winget manifest
  (`github.com/ollama/ollama/releases/download/v0.40.4/OllamaSetup.exe`), checked against the manifest SHA256.
- 05:59 Installer download finished; SHA256 `45FCD47D...0BADDE` matches the manifest. Silent per user install
  (`/VERYSILENT`), no administrator rights. Ollama 0.40.4 started its own server on port 11434 at 06:06.
- 06:07 `ollama pull qwen2.5:3b-instruct` started (1.9 GB at about 1.5 MB/s); finished about 06:29.
- Started the app with `LLM_PROVIDER=ollama RETRIEVAL_MODE=hybrid` (uvicorn on port 8000). `/api/health` returned
  `{"status":"ok","chat_enabled":true,"islands":7,"retrieval_mode":"hybrid","llm":"ollama:qwen2.5:3b-instruct"}`.
  Server stopped afterwards. Phase 1 passed.
- Clock note: the system clock moved forward by roughly three hours during the session (the Ollama log shows
  UTC+04:00 from then on). Times before this point were read from the earlier clock; times after it are local
  (UTC+04:00). Durations are what matter and are stated where relevant.
- 09:46 Measured speed: 5.7 tokens per second generated, 28 tokens per second for prompt processing. The laptop was
  not idle: other workloads unrelated to this work kept the CPU
  near 100% and left about 0.4 GB of RAM free. They were left running. All latencies in this session were measured
  under that load and are not comparable with the earlier llama.cpp run.
- Decision: at that speed the five model runs would not fit the time budget if run one after another. Ollama was
  restarted with `OLLAMA_NUM_PARALLEL=2` and the bm25 run (A) was run concurrently with the hybrid run (B) and then the
  two development runs. Answers are produced at temperature 0, so concurrency affects timing, not content. This
  deviation from a strictly sequential plan is noted in RESULTS.

## Phase 2: preregistration

- 05:35 Wrote `docs/PREREGISTRATION.md` and committed it (`c5f5f37`) before any eval run, out of the planned order
  because the model download was slow. It discloses that the predictions were informed by the stored run from
  commit `4321023`, which was read for the diagnosis first.
- Decisions recorded there: `--k 8` for all model runs (matches the earlier run, keeps CPU time per question
  manageable); no judge pass, because the machine has 13.9 GB of RAM, under the 16 GB threshold in the plan.

## Phase 3: evaluations

- 05:38 `eval.retrieval_eval`: every metric reproduces the stored values exactly (preregistered prediction R: hit).
  Tied items swapped order inside two top 5 lists, which changes no metric; the commit message for `26d02f9`
  says only the run metadata changed, which is wrong: the file has no metadata, and this reordering is the whole
  change. Recorded here rather than rewriting published history.
- 05:47 Added `eval/compare.py` (exact McNemar test for paired runs, validator failures by kind), commit `8d67fd9`.
- 10:33 Run A (bm25) finished: 23/30 passed, false refusals 4/25, refusal accuracy 5/5, first-attempt failures 3/36,
  no errors. Committed `bbf0729`.
- 10:39 Run B (hybrid) finished: 20/30 passed, false refusals 5/25, refusal accuracy 5/5, first-attempt failures
  5/34, no errors. Committed `db38ca2`. Paired test A against B: false refusals p = 1.000, passes p = 0.375.
- Note on recorded commits: `run_eval` stamps the commit at the end of a run, so A and B show docs-only commits made
  while they ran (`54791c9`, `bbf0729`); the code they ran is that of `cd7fd79`.

## Phase 4: over-refusal

- Diagnosis from the saved A and B records (see `eval/results/NOTES.md`): evidence IDs written into sentence text,
  correct values cited to the wrong item, facts placed in voice sentences, cited answers marked unanswered, one
  misspelt name. Retrieval was not the cause except for part of Q15.
- 10:45 A first candidate run on the development set was stopped before any answer was saved, to add two fixes
  suggested by the B diagnosis (IDs out of the text, repair hints). Nothing from that aborted run was read.
- About 10:50 to 14:20 the session was interrupted. The development baseline (D0) had finished at 10:59. Work resumed
  at 14:21, past the planned five hours, and continued.
- 14:47 Development candidate (D1): false refusals 1/20 (unchanged from D0, 1/20), first-attempt failures 0/20
  (D0: 2/23), guards 5/5 (D0: 5/5), passed 21/25 (D0: 20/25). The one remaining refusal (D05) is a retrieval miss:
  the expected fact is not among the items shown at k = 8 or k = 12, so no further iteration could address it.
- Deviation: the preregistered rule keeps a change only if development false refusals fall. They did not, because
  the development set was already near its ceiling. The change was still run once on the frozen 30, as the before
  and after measurement the plan requires, and this is reported as a deviation, not as a pass of the rule.
- Manual check (one unblinded reader) of every shown fact sentence that differs between D0 and D1, against its
  cited evidence: D0 17 of 17 supported; D1 15 of 16 supported and 1 contradicted (D08 reports the August value
  8.2 as September's, and calls the NASA grid cell the airport). The mechanical validator cannot catch this because
  8.2 is in the cited table. Side effect found: on every decline D1 emits an empty voice sentence, which costs a
  needless repair call.
- Decision rule fixed before reading run C: the same manual check is applied to the shown fact sentences that differ
  between B and C. If C has more unsupported or contradicted sentences than B, the behaviour change is reverted on
  main with a new commit, and all results stay recorded.
- Merged the change to main as `0e97570` and `de39e10` (validator and its tests unchanged; 235 tests pass), then
  started run C from main.
- Run C was interrupted at 18 answers when the session ended (about 15:10). Resumed from its checkpoint on 17
  October at 23:28 with the same code; 17 answers were kept and Q16 was answered again. Finished 23:44. Result: 23/30
  passed, false refusals 3/25, refusal accuracy 5/5, first-attempt failures 3/28, no errors (`cde50c5`).
- Paired test B against C: answerable questions answered 20/25 against 22/25 (4 better, 2 worse, p = 0.688); passes
  20/30 against 23/30 (p = 0.375). Not significant.
- Decision rule applied. Manual check of changed shown fact sentences: B 24 sentences, 1 contradicted (Q20), 1 partly
  supported; C 22 sentences, 2 contradicted (Q20, and Q18 naming the driest month as the wettest), 1 partly supported.
  C has more, so the change was reverted on main (`ae62ae4`). The code on main is again the configuration of run B.
  All runs, including C and the development runs, stay recorded.

## Phase 5: Edge proposal

- `docs/EDGE_PROPOSAL.md` (`7984f43`): problem, architecture, results with intervals, what is not proven, risks, three
  stage roadmap with exit criteria, and a specific pilot ask. No endorsement claimed. The model is not claimed to beat
  the baseline: passes 23/30 against 15/30 give overlapping 95% intervals (59 to 88% against 33 to 67%), even though a
  paired test gives p = 0.039; that comparison was not preregistered.

## Phase 6: docs and review

- `eval/report.py` now also prints errored counts, validator issue kinds and development runs (labelled as tuned), and
  appends `eval/results/NOTES.md`. `docs/RESULTS.md` regenerated (`caa9167`).
- README evaluation table rewritten; every percentage cell was checked by script to appear verbatim in RESULTS
  (`f4d2bf5`). Retrospective and "what I would redesign" updated; `docs/LLM_PLAN.md` status updated.
- Adversarial review by a separate reader that had not seen the work. It confirmed that every count in the README
  and proposal tables matches the stored runs, that `eval.report` reproduces `docs/RESULTS.md` exactly, and that the
  paired p values reproduce. Findings fixed:
  - The model's free-text `missing` note reached the screen without any check. It now gets the voice sentence
    checks and falls back to the fixed line (`447aee0`, with a test).
  - Runs were stamped with the commit at the end; now at the start, marked dirty when tracked files differ. The
    conflict measure keyed on a field no question has; it now keys on `type`. A test now checks that RESULTS.md is
    exactly what the report generates (`bc89c99`). Provenance corrections are listed in RESULTS.
  - The refusal comparison with the baseline (5/5 against 1/5) is now reported with its overlapping intervals and
    paired p = 0.125 instead of as a capability difference. "Retrieval in milliseconds" was removed (hybrid
    retrieval had a median of 2.5 s under load), and "offline" now notes the one time model downloads.
  - Wording that pointed to an outside brief, research tools or a sandbox was removed or rewritten; the claim that
    keyword retrieval is as good on the development questions is limited to hit@5 and recall@12; the LLM judge is
    described as built but not run; untested or unstored claims (the conflict behaviour, the AUC figures, the
    accessibility audit, older library counts) are labelled as such; the README setup command now installs the
    optional packages into the virtual environment; style fixes (hyphens, em dashes in PLAN.md, promotional words).
- Findings not fixed, with reasons:
  - Store the API key as `SecretStr`: touches every call site of the Anthropic provider and the judge; left as a
    recommendation. The key was never committed or printed into a tracked file.
  - Make the provider factory test independent of a local `.env`: it would mean editing a test, which this work
    avoided; runs set `ANTHROPIC_API_KEY` to empty instead.
  - Package import cycle between `app/data/retrieval.py` and `app/retrieval/`: works today, refactor left for later.
  - `Makefile` assumes a POSIX `.venv/bin` path and its `eval-offline` target names a run file that does not exist:
    left for the maintainer to choose the intended file.
  - Missing tests for `app/narration.py` and some API routes: outside the scope of this work.

## Phase 7: wrap up

- Before the final push: 232 tests passed, ruff clean, `scripts/validate_data.py` passed. The temporary worktree used for the
  candidate change was removed; its branch `fix/over-refusal` stays local and unpublished.

## Left for the maintainer

1. Earlier published commits (before this session) carry assistant co-author trailers. Removing them needs a history
   rewrite and force push, which this work did not do.
2. Decide whether to switch the live demo to a model; nothing on Render was touched.
3. Consider the table aware check described in RESULTS; it targets the only error type seen to pass the validator.
4. `SecretStr` for the API key, and a `.env`-independent provider test, as above.
5. The development set label for D07 (and D01) uses one of two conflicting sources; the model quoted the other. The
   labels were not changed after the results were seen.

# Second session, 18 October 2026

Times are local (UTC+04:00). Work continued in the existing clone.
The machine was quieter than in the first session (about 30% CPU at the start).

## Phase 1: test hygiene

- 02:15 `test_factory_selects_providers_and_validates_config` failed with a dummy `ANTHROPIC_API_KEY` set.
  `tests/conftest.py` now blanks the provider key and selection variables when it is imported, before test modules
  (and `app.main`, which reads settings at import) are collected. No assertion changed. 232 passed with a dummy key,
  an empty key, `LLM_PROVIDER=anthropic` with either, and with the variables unset (`0c6090b`).

## Phase 2: preregistration

- 02:20 `docs/PREREGISTRATION_2.md` committed (`2941971`) before the check was built and before any run of the new
  set. It names the two earlier errors that motivated the design as known cases, not evidence.

## Phase 3: held out set and tuning

- 02:20 `eval/questions_heldout.jsonl`: 30 questions written from the facts and committed POWER snapshots before any
  model output was seen (`b88943e`): 10 climate, 12 fact, 6 unanswerable, 2 injection; 20 dev and 10 sealed, split by
  type before any run. Mistake: that commit's tests use a constant added in the next commit (`62a87eb`), so
  `b88943e` alone does not pass its tests. Left as is rather than rewriting published history.
- 02:21 to 03:05 Baselines with the check off: dev (`heldout-dev-off`) and sealed (`heldout-sealed-off`). The sealed
  baseline started before any dev result was read. Its output was not opened before the decision step, but it was
  committed at 03:06 and rendered into RESULTS.md at 03:28, before tuning ended, so the repository cannot show that.
- The check was built in a separate worktree so the running baselines kept their code, then main was fast forwarded
  (`d13cb7c` to `bb11b76`). 270 tests passed with and without a dummy key.
- Replay over stored runs (measurement P, `aafb82b`): 264 fact sentences, 38 citing a NASA table, 5 rejections
  covering 3 distinct sentences, all genuine errors on reading (C Q18 wettest month, C Q19 first attempt warmest
  month, D1 D08 August value given for September). False rejections: 0.
- Dev iteration 1 (check on, from the worktree, stamped `62a87eb-dirty`): the three wrong superlative answers of the
  baseline (H02, H04, H05) became refusals; false refusals 3/15 to 6/15; passes 13/20 both.
- Dev iteration 2 (`19822c0`, failure messages name the correct cell): no change (false refusals 6/15).
- Diagnosis: correct answers such as "August, 8.93 m/s" were rejected by the existing name check, because the table
  writes AUG. This false rejection also exists with the check off (H01 is refused in the baseline).
- Dev iteration 3 (`5c42102`): with the check on, a full month name whose abbreviation labels a cited table column
  passes the name check, and its number and superlative are checked against that column. Dev: passes 15/20 (off
  13/20), false refusals 4/15 (off 3/15), refusal accuracy 4/5 (off 4/5). Frozen at `c5caef1`.
- CI was red for one push (`7c36932`): run files were committed before RESULTS.md was regenerated, which the new
  consistency test caught. Fixed in `b87b837`.
- Stretch phase (local entailment model) skipped: about 1.3 GB of RAM was free and a transformer install needs more
  than that, plus the time left was needed for the sealed and frozen runs.

## Phase 4: final runs and decision

- 03:45 to 04:14 Sealed 10 and frozen 30 with the check on, each once, side by side on the two model slots, at
  `c5caef1`. The sealed baseline's one errored question (H06, Ollama read timeout) was repeated once with the check
  off as allowed for an infrastructure failure; it timed out again in the repair step and stays excluded. The retry is
  stamped `c5caef1-dirty` because the log file was being edited; with the check off that code validates as the
  baseline's `62a87eb` did, but it is not the identical commit.
- Sealed (paired on 9): passes 7/9 both, answered 6/6 both, refusals 3/3 both, McNemar p = 1.000. Frozen with the
  check against run B: passes 20/30 both, answered 19/25 against 20/25, refusal accuracy 5/5 both, p = 1.000.
  Predictions P1 to P6 were all hits.
- Manual read of differing shown sentences: sealed, none new; frozen, 1 unsupported (Q24) and 1 partly supported
  (Q14) sentence only in the check on run, against 1 contradicted (Q20) only in run B. Condition 1 of the rule
  failed, so the check was reverted (`c308b71`); the results stay recorded (`2615df2`, `e662064`). The Q24 sentence
  involves no table, so the revert reflects variation between runs that the rule could not separate, which is
  written up in RESULTS as a lesson for the next rule.
- README and proposal updated; every README percentage cell was checked by script against RESULTS (`9424f0a`).

## Phase 5: entailment check

- Skipped, as recorded above (RAM and time).

## Phase 6: review and finish

- A separate reviewer that had not seen the work checked everything since `307720e`. It confirmed the prediction
  and decision tables against the run files, that the revert is complete, and that no assertion was weakened.
  Findings fixed:
  - The claim that the check stopped no correct answer was wrong: in sealed H06 it rejected a repair with the right
    month and value ("April ... 80.92") because the sentence called that value annual. README, proposal and RESULTS
    now say so, and split the five first attempt catches by set (3 dev, 1 frozen, 1 sealed).
  - The month name acceptance added in tuning makes some name check failures pass, contrary to the preregistration;
    it is now recorded as a deviation, with the dev gain attributed to it rather than to the check.
  - H with and without the new issue kinds is now reported, as preregistered.
  - The sealed baseline's exposure in RESULTS.md during tuning is now stated.
  - `eval/compare.py` now maps the held out question file, so the sealed paired result can be reproduced.
  - Run reports now state the actual number of questions instead of a fixed "30".
- Not fixed: `tests/conftest.py` blanks the provider key and selection variables only. Other settings in a local
  `.env` (for example `RETRIEVAL_MODE`) can still reach `Settings()` in tests; the tests pass with this machine's
  `.env`, and blanking those would need valid defaults rather than empty values.
- Ollama server stopped at the end of the session to free memory.

## Left for the maintainer (second session)

1. Rerun the table check comparison under a fairer rule: check on and check off on the same day, same questions,
   unsupported sentences counted in both directions, and without the month name relaxation (or with it tested
   separately).
2. The leftover empty folder `island-echoes-fix` beside the clone could not be deleted because a process held it;
   it can be removed after a restart.
3. Items 1, 3 and 4 of the first session's list still stand (commit trailers, the live demo, `SecretStr`).
