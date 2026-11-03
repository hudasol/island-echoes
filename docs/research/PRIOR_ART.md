# Prior art

Searched on 3 November 2026. The search was time boxed. The question is whether an existing free tool already
combines (a) a globe interface to remote islands, (b) one field agent per species, (c) answers restricted to cited
sources with a mechanical grounding validator, (d) abstention on unanswerable questions, and (e) no paid model.

## Queries and results

| Query | Result that mattered | Verdict |
|---|---|---|
| globe interface remote islands endangered species chatbot cited sources grounded answers abstain | Generic hits (species prompt collections, GBIF assistant guides). No product combining a globe, species agents and a validator. | No match |
| citation grounded RAG mechanical validator numbers entities abstention small local model | GRACE (arXiv 2601.04525): reinforcement learning for grounded answers with abstention on QASPER and HotpotQA. Rule based checks cover output format and text overlap only. No validator for numbers or names, no map interface. | Related method, different scope |
| NASA Space Apps islands endangered species 3D globe project | Space Apps gallery entries from 2017 to 2020 on biodiversity visualisation. None with grounded question answering. | No match |
| "talk to" endangered species chatbot persona IUCN grounded retrieval github | WildLabs discussion of a chatbot that lets visitors talk to endangered animals and ecosystems: no mention of cited sources, a globe or validation. WildInsight (ECML PKDD 2025): a cited chatbot over peer reviewed wildlife machine learning papers; abstention behaviour is not described and it has no species or island interface. | Partial overlap on persona and on citation |
| sentence level citation verification, rule based numeric entity check, extractive fallback | Citation verification systems (SemanticCite, DeepSciVerify, CiteAudit) judge claim to citation alignment with large models or benchmarks; none replaces a rejected sentence with the verbatim cited sentence on a small local model. | Related method, different scope |

## Verdict

No free tool found closes the whole gap. Existing work covers parts: persona chatbots for species without cited
sources, cited chatbots without a species or island interface, and training based abstention research without a
mechanical validator. The open part, and the positioning of this project, is the combination of per island and per
species field agents, a mechanical validator whose effect is measured against ablations, a deterministic route for
numeric climate questions, and a pipeline that runs on a laptop CPU with no paid model. The stop rule did not apply
and the product work continued.

## Limits of this search

The search used a general web index and a small number of queries. It did not cover private products or every
conference proceeding, and a closer match may exist.
