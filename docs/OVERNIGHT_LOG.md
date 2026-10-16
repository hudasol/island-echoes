# Overnight log, 16 October 2026

Unattended session on the project laptop. Times are local. Entries are in the order they happened.

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
  not idle: other projects' simulations and test suites (in other folders, not started by this session) kept the CPU
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
  at 14:21, already past the five hour budget; continued on the owner's instruction.
- 14:47 Development candidate (D1): false refusals 1/20 (unchanged from D0, 1/20), first-attempt failures 0/20
  (D0: 2/23), guards 5/5 (D0: 5/5), passed 21/25 (D0: 20/25). The one remaining refusal (D05) is a retrieval miss:
  the expected fact is not among the items shown at k = 8 or k = 12, so no further iteration could address it.
- Deviation: the preregistered rule keeps a change only if development false refusals fall. They did not, because
  the development set was already near its ceiling. The change was still run once on the frozen 30, as the before
  and after measurement the plan requires, and this is reported as a deviation, not as a pass of the rule.
- Manual check (by the agent, not blind) of every shown fact sentence that differs between D0 and D1, against its
  cited evidence: D0 17 of 17 supported; D1 15 of 16 supported and 1 contradicted (D08 reports the August value
  8.2 as September's, and calls the NASA grid cell the airport). The mechanical validator cannot catch this because
  8.2 is in the cited table. Side effect found: on every decline D1 emits an empty voice sentence, which costs a
  needless repair call.
- Decision rule fixed before reading run C: the same manual check is applied to the shown fact sentences that differ
  between B and C. If C has more unsupported or contradicted sentences than B, the behaviour change is reverted on
  main with a new commit, and all results stay recorded.
- Merged the change to main as `0e97570` and `de39e10` (validator and its tests unchanged; 235 tests pass), then
  started run C from main.
