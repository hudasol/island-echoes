# API reference

Interactive documentation is served at `/api/docs` and the machine readable description is [openapi.json](openapi.json). Version 1 of the public API lives under `/api/v1`; the unversioned `/api` paths remain as aliases for existing clients and return the same data. All responses are JSON. Lookups are limited per client (`READ_RATE_PER_MIN`, default 240); chat has its own limit (`CHAT_RATE_PER_MIN`) and a daily cap (`CHAT_DAILY_CAP`).

A limited request returns status 429 with a `Retry-After` header in seconds. Any site may read the GET endpoints from a browser (CORS is open for GET only); chat is not available cross origin.

| Method and path | Purpose |
|---|---|
| `GET /api/v1/health` | Version, island count, retrieval mode, whether chat is on and which model, uptime. |
| `GET /api/v1/overview` | Per island fact counts, categories, confidence split, source mix, creatures with IUCN code, and the dates of the POWER and GBIF data. |
| `GET /api/v1/evaluation` | Stored evaluation numbers: retrieval on the gold sets and the end to end baselines. |
| `GET /api/v1/stats?days=7` | Usage and answer quality measured by this server. |
| `GET /api/v1/data-changes` | Values that changed when live data replaced older data. |
| `GET /api/v1/islands` | The seven islands with creatures and pin positions. |
| `GET /api/v1/islands/{slug}` | One island with all of its facts. |
| `GET /api/v1/islands/{slug}/sensors?creature=` | NASA POWER annual means and monthly values for four climate readings. |
| `GET /api/v1/islands/{slug}/conservation?creature=` | The IUCN Red List category GBIF holds for the creature. 404 when there is none. |
| `GET /api/v1/islands/{slug}/narration?creature=` | The cited field report for a creature. |
| `GET /api/v1/library/search` | Search an island's sourced entries. Parameters: `island`, `q`, `category`, `creature`, `limit`. |
| `GET /api/v1/islands/{slug}/educator` | The data behind the printable educator sheet: numbered facts, readings, discussion questions and sources. |
| `GET /educator/{slug}` and `/educator/{slug}.pdf` | The educator sheet as a page and as a PDF. |
| `POST /api/v1/chat` | Ask the creature. Body: `island`, `creature`, `message`, `history`. 503 when no model is configured. |

## Library search

```bash
curl "https://island-echoes.onrender.com/api/v1/library/search?island=socotra&q=highest%20point"
```

The response lists matching entries with their source, publisher, retrieval date and confidence label, per category counts, and a `quality` field: `strong`, `partial`, `none` or `browse`. A query the sources cannot answer returns no results with `quality: none`.

## Chat

```bash
curl -X POST localhost:8000/api/v1/chat -H "Content-Type: application/json" \
  -d '{"island":"socotra","creature":"socotra-buzzard","message":"Where is the highest point?"}'
```

Each sentence in the reply has `kind` (`fact` or `voice`) and `cites`, a list of evidence IDs. `evidence` carries the cited items first, then the retrieved items that were not cited, and `grounding` reports how many sentences were repaired or dropped.

## Embeddable widget

```html
<script src="https://island-echoes.onrender.com/embed.js" data-island="socotra"></script>
```

The widget runs in a shadow root, searches the library through `GET /api/v1/library/search`, and shows each result with its publisher, link, retrieval date and confidence label. A question the sources cannot answer returns nothing. It sets no cookies and sends no analytics. A preview is at `/embed-demo.html`.
