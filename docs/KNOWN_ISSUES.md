# Known issues

Findings from an adversarial review of the repository at version 1.2.0 (in progress), logged with severity and status.
Severity: high means a published claim or a user facing behaviour is wrong; medium means a limit a reader could be
misled by; low means cosmetic or contained. Status: fixed, open, or accepted with a reason.

| ID | Severity | Where | Finding | Status |
|---|---|---|---|---|
| KI-1 | medium | `eval/v3/` | The sealed questions were written by a 1.5B model and the gold answers are constructed from the fact files. Results measure whether the system finds and states the fact a question was built around, and overstate performance on free form questions. The writer is smaller than the 3B answerer, so shared phrasing habits may favour it. The bias is stated, not measured. | accepted, stated in `docs/RESULTS.md` and the preregistration |
| KI-2 | medium | `eval/v3/second_labeller.jsonl` | The second labeller is a model. Agreement with the constructed gold is model to model: exact match 66% (45 of 68), below the 85% predicted (P10). | accepted, reported as a miss |
| KI-3 | medium | `web/i18n.js`, `web/app.js` | Dynamic strings produced from data (fact text, citations, library results, model answers) stay in the source language in the Arabic interface. Interface text is translated. | accepted, stated in the About text |
| KI-4 | low | `app/chat/` | The climate answers are produced from templates, not free text. This is deliberate (they cannot hallucinate) but they read plainly. | accepted |
| KI-5 | low | git history | The commit "Add a shareable field report page and image card" appears twice. History is not rewritten, so it stays. | accepted |
| KI-6 | low | `app/providers/` | A hosted commercial API provider remains in the code from an earlier version. It is unused, has no key set, and the default configuration never calls it. | accepted, free tools only |
| KI-7 | medium | `eval/results/` | Every run is at temperature 0, so a rerun reproduces stored answers. There is no estimate of generation variance. | accepted, stated in the preregistration |
| KI-8 | medium | CI, `lighthouserc.json` | On the CI runner the Lighthouse performance score and total blocking time warnings fire (the globe is software rendered there). Accessibility and best practice floors pass and fail the build. No measurement on a real phone exists. | open |
| KI-9 | low | `eval/`, `scripts/` | mypy runs on `app/` in CI and passes. Running it on `eval/` and `scripts/` reports 14 typing errors that are not gated. | open |
| KI-10 | low | `docs/RESULTS.md` history | The first committed sealed table (commit 5ad4b42) divided false refusals by all 112 answerable questions, including those the model errored on (ten questions returned malformed JSON). Denominators now use the scored questions, which moved the dropped arm from 37% (41/112) to 40% (41/102); the earlier figure was never quoted in the README. | fixed |
| KI-11 | medium | `app/data/climate_tool.py` | As run, the climate route answered four questions about places not in the library from the selected island. Fixed after the sealed results were read and reported as post hoc. | fixed |
| KI-12 | low | `eval/results/v3/nli.json` | The entailment check was measured on 117 sentences, fewer than the 200 planned, because the 3B run produced no more fact sentences. | accepted |
| KI-13 | low | `data/islands/` | Not added: new islands or creatures. The seven island count is built into the interface, tests and evaluation sets, and each fact needs a source fetched at the time. Five Clipperton facts were added. | open |
| KI-14 | high | hosted service | At the end of the 1.2.0 session the live site still served an earlier build: the Arabic interface assets, educator pages and `/api/v1` returned 404. The hosting account was not modified. | open |
