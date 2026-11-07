# Runbook: AI cost spike

Use this when Gemini or OpenAI spend rises much faster than traffic explains.

## Symptoms

- A billing alert from Google AI Studio, Google Cloud or OpenAI.
- `llm.call` spans show far more calls, or more `llm.input_tokens`, than usual.

## Check

1. Is it real traffic or bots? Look at the pass rate and request volume in the Cloudflare dashboard, under Turnstile.
2. Recent API logs. In Render: **mbiu-api → Logs**.

3. Are there unusually long contracts? Uploads are capped by `MAX_UPLOAD_MB` and `MAX_PAGES`.

## Mitigate

In order, stopping when spend levels off.

1. **Switch to the light model.** It is much cheaper per token.

   Set `GEMINI_MODEL_MAIN=gemini-3.5-flash-lite` in Render → mbiu-api → Environment.

2. **Lower the upload caps** so fewer clauses are sent per contract.

   Set `MAX_PAGES=20` in Render → mbiu-api → Environment.

3. **Bots are getting through.** In Cloudflare, add a rate-limiting rule on `POST /api/v1/evaluations` and `POST /api/v1/clause-evaluations`, for example 5 requests per IP per 10 minutes, with a managed challenge.

4. **Last resort.** Stop all spend: Render → mbiu-api → Settings → **Suspend service**. Resume it there once the cause is fixed.

## Verify

Spend levels off in the provider's billing page, and a synthetic contract from `evals/datasets/pdfs/` still gets results in the web app.

## Afterwards

- Set a monthly budget alert and quota cap in Google Cloud Billing.
- Revert the model and caps, and resume the service, once the cause is fixed.
