# Runbook: AI Provider Outage (Gemini / OpenAI)

> **Severity:** High / Critical  
> **Target Audience:** On-call engineer (2 a.m. playbook)  
> **System Component:** `backend/mbiu/llm/`, `backend/mbiu/evaluation/orchestrator.py`  

---

## 1. Incident Overview & Symptoms

This runbook applies when the primary AI model provider (**Google Gemini**) or secondary provider (**OpenAI**) experiences severe latency, rate-limiting, or an outright service outage.

### Quick Status & Log Checks
1. **Provider Status Pages:**
   * Google Cloud / Vertex AI Status: <https://status.cloud.google.com/>
   * OpenAI Status: <https://status.openai.com/>
2. **Recent API Logs:** In Render: **mbiu-api → Logs** (or `docker compose logs --tail=100 api`).
3. **Quota & Billing:** Check quota and billing for the Gemini API key in Google Cloud Console / Google AI Studio.

### Alert Triggers
* **PagerDuty / Sentry Alert:** `LLMError: unavailable` or `LLMError: rate_limited` surge.
* **Grafana Alert:** `mbiu_llm_requests_failed_total` > 5% over 5 minutes.
* **Circuit Breaker Trip:** `pybreaker.CircuitBreakerError` logged in API worker spans.
* **User Impact:** Artists see the `ServiceUnavailableBanner` (*"Mbiu can't check contracts right now. Your clauses are listed below; try again in a few minutes."*) or multiple `clause_failed` cards.

---

## 2. Immediate 2 A.M. Triage (First 5 Minutes)

### Step 1: Check Provider Health
1. **Google Gemini Status:**
   * Visit [Google Cloud Status Dashboard](https://status.cloud.google.com/) and [Vertex AI / Gemini Status](https://status.cloud.google.com/).
   * Check your Google Cloud Console for project quota warnings or API billing limits.
2. **OpenAI Status:**
   * Visit [OpenAI Status](https://status.openai.com/).

### Step 2: Inspect Live Error Logs
Connect to the API container / cluster and inspect the recent LLM error logs:
```bash
# Render logs:
# Go to Render Dashboard -> mbiu-api -> Logs

# Or Docker Compose local / staging:
docker compose logs --tail=100 api | grep -E "LLMError|circuit_breaker|gemini|openai"

# Or Kubernetes / Production:
kubectl logs -l app=mbiu-api --tail=100 | grep -E "LLMError|CircuitBreaker"
```

Look for the error category:
* `ErrorCategory.RATE_LIMITED` (`429`): Quota exhausted or unexpected traffic burst.
* `ErrorCategory.UNAVAILABLE` (`503` / `502`): Provider infrastructure down.
* `ErrorCategory.TIMEOUT`: Provider is responding too slowly (> `BATCH_TIMEOUT_S=30s`).

---

## 3. Mitigation & Failover Procedures

> [!NOTE]
> Changing an environment variable in Render (**mbiu-api → Environment → Save**) automatically triggers a redeploy of the API service.

### Option A: Enable OpenAI Failover (Gemini Outage)
If Google Gemini is confirmed down and the circuit breaker is tripping, activate the OpenAI failover provider:

1. **Verify Golden Set & Privacy Guarantees:**
   Only fail over if OpenAI has passed the golden test set. In accordance with [`docs/data-transfers.md`](../../docs/data-transfers.md), contract text is transmitted with `store: false` enforced.
2. **Enable Failover in Runtime Environment:**
   * **In Render:** Set `FAILOVER_ENABLED=true` in **mbiu-api → Environment → Save**.
   * **In Docker / Local:**
     ```bash
     # In .env:
     FAILOVER_ENABLED=true
     docker compose restart api
     ```
   * **In Kubernetes:**
     ```bash
     kubectl set env deployment/mbiu-api FAILOVER_ENABLED=true
     kubectl rollout restart deployment/mbiu-api
     ```

### Option B: Switch Gemini to Light Model (Latency / Rate Limit Spike)
If Gemini Flash (`gemini-3.8-flash`) is hitting rate limits or throttling, switch the primary model to the lighter tier:
* **In Render:** Set `GEMINI_MODEL_MAIN=gemini-3.5-flash-lite` in **mbiu-api → Environment → Save**.
* **In Docker / Local:**
  ```bash
  GEMINI_MODEL_MAIN=gemini-3.5-flash-lite
  docker compose restart api
  ```

---

## 4. Verification & Recovery

1. **Run Smoke Test Evaluation:**
   Execute a test evaluation against the running API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/evaluations \
     -F "file=@evals/sample_contracts/pdf/01_brand_partnership_fair_savannah_mobile.pdf" \
     -F "turnstile_token=1x0000000000000000000000000000000AA" \
     | head -n 10
   ```
2. **Verify Stream Output:**
   * Confirm that the first event is `{"type": "document", ...}`.
   * Confirm that `clause_result` events arrive without 500 errors.
   * Check the `versions` object in the final `done` event to see the active provider and model:
     ```json
     "versions": {
       "model": "gpt-4o-mini",
       "prompt": "compare_openai_v1",
       "corpus": "kenyan-music-v1"
     }
     ```

---

## 5. Reverting After Provider Restores

Once the primary provider (Gemini) announces resolution:
1. Revert settings in Render:
   * Set `FAILOVER_ENABLED=false` and `GEMINI_MODEL_MAIN=gemini-3.8-flash` in **mbiu-api → Environment → Save**.
2. If running locally / Docker / Kubernetes, revert `.env` and restart workers:
   ```bash
   FAILOVER_ENABLED=false
   GEMINI_MODEL_MAIN=gemini-3.8-flash
   docker compose restart api
   ```
3. Verify Gemini circuit breaker resets to `CLOSED` and evaluations process via Gemini.
