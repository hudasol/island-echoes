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
| KI-6 | low | `app/providers/` | The `anthropic` provider remains in the code but is unused and has no key set. Default configuration never calls it. | accepted, free tools only |
| KI-7 | medium | `eval/results/` | Every run is at temperature 0, so a rerun reproduces stored answers. There is no estimate of generation variance. | accepted, stated in the preregistration |
| KI-8 | low | CI | Lighthouse speed assertions are warnings until measured on the CI runner; accessibility and best practice floors fail the build. A measurement on the development machine under CPU load was invalid. | open |
