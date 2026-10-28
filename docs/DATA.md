# Data

## Sources

| Source | Used for | Stored as |
|---|---|---|
| Island fact files | Facts about each island and creature | `data/islands/*.json` |
| NASA POWER | 2001 to 2020 climatology for the grid cell around each island | `data/snapshots/power/` |
| GBIF | Species match, occurrence counts, IUCN Red List category | `data/snapshots/gbif/` |
| NASA GIBS | Satellite imagery tiles, loaded by the browser | not stored |

No keys are needed for any of them.

## Fact record

Each fact has an ID (`SOC-011`), a category, a subject (`island` or a creature slug), the statement, the source URL, title and publisher, the retrieval date, a note on what in the source supports it, and a confidence label.

- **High**: the source states it plainly and nothing found contradicts it. No High fact cites Wikipedia.
- **Medium**: it rests on one source, often an encyclopedia or a news report.
- **Low**: sources conflict or are thin.

Conflicts between sources are kept as separate facts and listed in each island file together with known gaps. `python scripts/validate_data.py` checks every file against the schema, and CI runs it on every push.

## Composition

Counts are produced by `/api/overview` and shown on the operations page.

| | |
|---|---|
| Islands | 7 |
| Creatures | 8 |
| Facts | 469 |
| Distinct sources | 90 |
| Confidence | 223 high, 244 medium, 2 low |
| Facts citing Wikipedia | 36.7% |

## Reading the climate values

Each NASA POWER value describes a grid cell of about 0.5 by 0.625 degrees. Every island here is smaller than one cell, so the numbers describe the surrounding area. When a creature lives away from the pin (the Pinta Island tortoise), the panel names the place and the distance.

## Species records

GBIF counts are split into observations, preserved or fossil specimens, and living or captive animals, using only records with coordinates and no flagged coordinate issue. The search box around each island is stated in the evidence text. For the extinct Pinta Island tortoise, 22 of its 27 nearby records are specimens.

The conservation category shown on each creature is the one GBIF holds for the species. GBIF republishes the category and the IUCN taxon ID but not the assessment year or criteria, so those come from the fact files and are shown as reported.

## Refreshing

`python scripts/snapshot_sources.py` refreshes the POWER and GBIF snapshots. A weekly workflow checks that every source link still resolves. To report an error in a fact, use the link on the entry or open an issue.
