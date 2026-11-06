# Runbook: AI cost spike

Use this when Gemini or OpenAI spend rises much faster than traffic explains.

## Symptoms

- A billing alert from Google AI Studio, Google Cloud or OpenAI.
- `llm.call` spans show far more calls, or more `llm.input_tokens`, than usual.

## Check

1. Is it real traffic or bots? Look at the pass rate and request volume in the Cloudflare dashboard, under Turnstile.
2. Recent API logs:

   ```bash
   gcloud run services logs read mbiu-api --region "$REGION" --limit 200
   ```

3. Are there unusually long contracts? Uploads are capped by `MAX_UPLOAD_MB` and `MAX_PAGES`.

## Mitigate

In order, stopping when spend levels off.

1. **Switch to the light model.** It is much cheaper per token.

   ```bash
   gcloud run services update mbiu-api --region "$REGION" --update-env-vars GEMINI_MODEL_MAIN=gemini-3.5-flash-lite
   ```

2. **Lower the upload caps** so fewer clauses are sent per contract.

   ```bash
   gcloud run services update mbiu-api --region "$REGION" --update-env-vars MAX_PAGES=20
   ```

3. **Bots are getting through.** In Cloudflare, add a rate-limiting rule on `POST /api/v1/evaluations` and `POST /api/v1/clause-evaluations`, for example 5 requests per IP per 10 minutes, with a managed challenge.

4. **Last resort.** Scale the API to zero to stop all spend:

   ```bash
   gcloud run services update mbiu-api --region "$REGION" --max-instances 0
   ```

## Verify

Spend levels off in the provider's billing page, and a synthetic contract from `evals/datasets/pdfs/` still gets results in the web app.

## Afterwards

- Set a monthly budget alert and quota cap in Google Cloud Billing.
- Revert the model, caps and instance limit once the cause is fixed.
