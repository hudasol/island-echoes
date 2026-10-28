# API reference

Interactive documentation is served at `/api/docs`. All responses are JSON. Lookups are limited per client (`READ_RATE_PER_MIN`, default 240); chat has its own limit (`CHAT_RATE_PER_MIN`) and a daily cap (`CHAT_DAILY_CAP`).

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Version, island count, retrieval mode, whether chat is on and which model, uptime. |
| `GET /api/overview` | Per island fact counts, categories, confidence split, source mix, creatures with IUCN code, and the dates of the POWER and GBIF data. |
| `GET /api/evaluation` | Stored evaluation numbers: retrieval on the gold sets and the end to end baselines. |
| `GET /api/stats?days=7` | Usage and answer quality measured by this server. |
| `GET /api/data-changes` | Values that changed when live data replaced older data. |
| `GET /api/islands` | The seven islands with creatures and pin positions. |
| `GET /api/islands/{slug}` | One island with all of its facts. |
| `GET /api/islands/{slug}/sensors?creature=` | NASA POWER annual means and monthly values for four climate readings. |
| `GET /api/islands/{slug}/conservation?creature=` | The IUCN Red List category GBIF holds for the creature. 404 when there is none. |
| `GET /api/islands/{slug}/narration?creature=` | The cited field report for a creature. |
| `GET /api/library/search` | Search an island's sourced entries. Parameters: `island`, `q`, `category`, `creature`, `limit`. |
| `POST /api/chat` | Ask the creature. Body: `island`, `creature`, `message`, `history`. 503 when no model is configured. |

## Library search

```bash
curl "https://island-echoes.onrender.com/api/library/search?island=socotra&q=highest%20point"
```

The response lists matching entries with their source, publisher, retrieval date and confidence label, per category counts, and a `quality` field: `strong`, `partial`, `none` or `browse`. A query the sources cannot answer returns no results with `quality: none`.

## Chat

```bash
curl -X POST localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"island":"socotra","creature":"socotra-buzzard","message":"Where is the highest point?"}'
```

Each sentence in the reply has `kind` (`fact` or `voice`) and `cites`, a list of evidence IDs. `evidence` carries the cited items first, then the retrieved items that were not cited, and `grounding` reports how many sentences were repaired or dropped.
