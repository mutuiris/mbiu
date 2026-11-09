# Runbook: AI provider outage

Use this when Gemini (or OpenAI, if failover is on) is down, rate-limiting or very slow.

## Symptoms

- Artists see "Mbiu can't check contracts right now" or many cards that could not be checked.
- `llm.call` spans show `llm.error_category` of `unavailable`, `rate_limited` or `timeout`.
- After 5 outage errors in a row the circuit breaker opens for 60 seconds and calls stop.

## Check

1. Provider status: <https://status.cloud.google.com/> and <https://status.openai.com/>.
2. Recent API logs. In Render: **mbiu-api → Logs**.

3. Quota and billing for the Gemini API key in Google AI Studio.

## Mitigate

Changing an environment variable in Render (**mbiu-api → Environment → Save**) redeploys the API.

**Gemini is down: turn on OpenAI failover.** Only if OpenAI has passed the golden set. OpenAI then receives contract text, with `store: false`, as listed in [data-transfers.md](../data-transfers.md).

Set `FAILOVER_ENABLED=true` in Render → mbiu-api → Environment.

`OPENAI_API_KEY` and `OPENAI_MODEL` must already be set on the service.

**Gemini is rate-limiting or slow: switch to the light model.**

Set `GEMINI_MODEL_MAIN=gemini-3.5-flash-lite` in Render → mbiu-api → Environment.

## Verify

Upload a synthetic contract from `evals/datasets/pdfs/` in the web app. Never use a real contract. Cards should arrive, and the final summary's `versions.model` shows which model answered.

## Revert

When the provider recovers:

Set `FAILOVER_ENABLED=false` and `GEMINI_MODEL_MAIN=gemini-3.8-flash` in Render → mbiu-api → Environment.
