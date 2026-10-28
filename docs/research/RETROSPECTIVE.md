# Retrospective

What went wrong during the build, the assumptions made, and what would change next. Moved out of the README so that it describes the product.

## What went wrong

- **A second research pass needed a second check.** The 182 library facts added later (species, water, climate, ecology) were first compiled from page summaries rather than the full source text. An independent re-read of every one found 26 statements that overstated or mixed up their source (for example two bird population figures swapped), and they were corrected before publishing. Facts that rest on Wikipedia alone are labelled medium confidence in the UI, and on 9 October a further check of the 32 Wikipedia facts labelled High found 14 that needed correcting.
- **The fact base had to be researched from scratch.** That took the largest share of the work and left many facts at medium confidence because they rest on a single secondary source.
- **IUCN pages could not be fetched** when the facts were compiled, so statuses come secondhand. This is stated in the UI and on every creature.
- **A relevance threshold on retrieval was the wrong gate.** The first design refused any question whose best BM25 score fell below a cutoff. It refused good questions phrased unusually and passed bad ones. It was replaced by a narrow rule (refuse only on zero word overlap) and the model plus validator handle the rest.
- **Naive stemming broke matches** ("tortoises" against "tortoise"), and first-person questions ("what do you eat?") pulled in evidence about the wrong topic when I anchored them to the creature name. Both were fixed with tests.
- **Some sources disagree** (population figures, assessment years). These are kept as separate facts rather than merged, which makes answers longer but faithful to the sources.

- **A small local model followed the citation format badly at first.** The first run of Qwen2.5-3B padded evidence IDs with punctuation (".TDC-019"), so every citation was rejected and the model looked useless. A cleaner for the wrapper characters (the ID itself must still match retrieved evidence) fixed it. Serving the same weights through Ollama with schema constrained output later coincided with first attempt failures of 8 to 15% instead of 27% and false refusals of 16 to 20% instead of 42%; the cause was not isolated. Measuring before blaming the model mattered.
- **Predictions anchored on one old run were wrong.** The preregistered predictions assumed the llama.cpp behaviour would carry over; most missed on the optimistic side. They are reported as misses.
- **A useful check was reverted by its own rule.** The table aware check rejected five wrong month claims on first attempts and one correctly valued but wrongly worded repair, but the rule fixed in advance compared its run with a two day old baseline, and one unrelated unsupported sentence in the new run triggered a revert. The rule was kept as written; the lesson is in how the next rule is designed.
- **A fix that looked better was reverted.** A prompt and schema change lowered false refusals within noise, but a manual reading found one more contradicted sentence among the changed answers. A rule set before the run said to revert, and it was. The mechanical proxy alone would have kept it.
- **Embeddings helped less than hoped as a gate.** Dense similarity separates answerable from unanswerable questions better than BM25 scores (AUC 0.93 against 0.85 on the 106-question set), but no threshold is clean (at 0.55, 19 of 54 off topic questions pass; measured once, and the script and output are not stored in this repository), so the library keeps its tuned keyword gate and dense retrieval is used only to rank evidence for the chat.
- **A long eval run was lost** when the machine restarted. The runner now checkpoints every answer and resumes; this later saved an interrupted run.

## Assumptions

- A sentence is grounded if its numbers and names appear in the evidence it cites. This catches invented figures and names cheaply, but it cannot catch a wrong claim built from correct words. An LLM judge (`eval/judge.py`) is built for this but has not been run.
- One representative creature per island (two on the Galápagos), chosen because presence on or near the island is verifiable in GBIF.
- NASA POWER's coarse grid cell is a fair proxy for an island's climate. For tiny islands such as Clipperton it is an approximation, and the sensor note shows the cell used.
- Anthropic's model is called through a forced tool, so output shape is guaranteed but content is not. Local and hosted open models are asked for JSON against a schema, and small ones sometimes return malformed output, which counts as an error.

## What would change

- Store claims, not paragraphs: break each fact into atomic statements so the validator can check meaning, not only numbers and names.
- Check meaning, not only words, with a small local entailment model, so a wrong claim built from correct words is caught without a paid judge.
- Grow the held out set and have a second person label the gold fact IDs; 58 questions from one annotator leave wide intervals.
- Bring back the table aware check, without the month name relaxation added during tuning, under a fairer rule: compare runs with and without it made the same day on the same questions, and count unsupported sentences in both directions.
- Try a 7B-class free hosted model and a fine-tuned small model on the citation format, then compare in the same table.
- Add a second, independent verifier model call for every answer instead of only in the eval.
- Pull Red List statuses from the official API once a token is available.
- Run the eval in CI on every change to the fact files.
