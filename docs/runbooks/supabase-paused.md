# Runbook: Supabase paused or pooler saturated

The API reads public templates from Supabase and stores no contracts there. If the database is unreachable, the API is not ready.

## Symptoms

- `GET /readyz` returns `503` with `{"status": "not_ready", "failed": ["database"]}`.
- Logs show `could not connect to server` or `remaining connection slots are reserved`.
- The Supabase dashboard shows the project as **Paused**. Free projects pause after a week without activity.

## Check

```bash
curl -i "$API_URL/readyz"
```

Then check the logs in Render: **mbiu-api → Logs**.

## Mitigate

**Project paused.** In the Supabase dashboard, open the project and choose **Restore project**. It takes a minute or two. Then check `/readyz` again; the API reconnects on the next request.

**Pooler saturated.**

1. `DATABASE_URL` must use the transaction pooler (port 6543). Django keeps no connections open (`CONN_MAX_AGE` is 0 in [settings.py](../../backend/config/settings.py)), so a saturated pooler usually means another client is holding connections.
2. In the Supabase dashboard, check active connections under Database, then restart the pooler.
3. As a temporary workaround, set `DATABASE_URL` in Render → mbiu-api → Environment to the session pooler (port 5432); saving redeploys. Switch back afterwards.

## Verify

`curl -f "$API_URL/readyz"` returns `{"status": "ready"}`, and a synthetic contract from `evals/datasets/pdfs/` gets results in the web app.

## Prevent

- An UptimeRobot check on `/readyz` every 5 minutes alerts on downtime and keeps the free project active.
- Move to Supabase Pro before the pilot so the project never pauses.
