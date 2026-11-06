# Runbook: AI provider outage

Use this when Gemini (or OpenAI, if failover is on) is down, rate-limiting or very slow.

## Symptoms

- Artists see "Mbiu can't check contracts right now" or many cards that could not be checked.
- `llm.call` spans show `llm.error_category` of `unavailable`, `rate_limited` or `timeout`.
- After 5 outage errors in a row the circuit breaker opens for 60 seconds and calls stop.

## Check

1. Provider status: <https://status.cloud.google.com/> and <https://status.openai.com/>.
2. Recent API logs:

   ```bash
   gcloud run services logs read mbiu-api --region "$REGION" --limit 200
   ```

3. Quota and billing for the Gemini API key in Google AI Studio.

## Mitigate

Every `gcloud run services update` creates a new revision, which restarts the API.

**Gemini is down: turn on OpenAI failover.** Only if OpenAI has passed the golden set. OpenAI then receives contract text, with `store: false`, as listed in [data-transfers.md](../data-transfers.md).

```bash
gcloud run services update mbiu-api --region "$REGION" --update-env-vars FAILOVER_ENABLED=true
```

`OPENAI_API_KEY` and `OPENAI_MODEL` must already be set on the service.

**Gemini is rate-limiting or slow: switch to the light model.**

```bash
gcloud run services update mbiu-api --region "$REGION" --update-env-vars GEMINI_MODEL_MAIN=gemini-3.5-flash-lite
```

## Verify

Upload a synthetic contract from `evals/datasets/pdfs/` in the web app. Never use a real contract. Cards should arrive, and the final summary's `versions.model` shows which model answered.

## Revert

When the provider recovers:

```bash
gcloud run services update mbiu-api --region "$REGION" \
  --update-env-vars FAILOVER_ENABLED=false,GEMINI_MODEL_MAIN=gemini-3.8-flash
```
