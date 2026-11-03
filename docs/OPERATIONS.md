# Operations

## Scheduled checks

`.github/workflows/ops.yml` runs every six hours and on demand.

| Check | What it does | Fails when |
|---|---|---|
| Uptime | Requests `/api/health` on the live site, up to five tries thirty seconds apart to allow for a cold start on the free tier | the response is not `"status":"ok"` |
| Public API | Requests `/api/v1/islands` | the response has no island entries |
| Data freshness | Runs `scripts/check_freshness.py --max-days 120` on the committed snapshots | any snapshot in `data/snapshots/` is older than 120 days |

A failed scheduled run appears in the Actions tab and GitHub emails the repository owner. The freshness limit is a
reminder to refresh, not a claim that older data is wrong: NASA POWER climatology covers the fixed period 2001 to 2020,
and GBIF counts only grow as records are added.

## Refreshing the snapshots

1. `python scripts/snapshot_sources.py` fetches NASA POWER and GBIF again for every island (or name islands to refresh some).
2. `python scripts/validate_data.py` and `pytest -q` confirm the files still match the schema and the tests.
3. Counts change when GBIF grows, so regenerate the stored evaluation tables that quote them and list the change in the
   CHANGELOG. Do not edit committed evaluation runs by hand.
4. Commit the changed snapshots in one commit and push to main. Render redeploys from main.

## Health and cold starts

`render.yaml` points the platform health check at `/api/health`. The free tier sleeps after inactivity, so the first
request after a quiet period can take tens of seconds; the offline shell (service worker) keeps the interface usable
meanwhile.
