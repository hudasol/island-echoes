# Overnight log, 16 October 2026

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
