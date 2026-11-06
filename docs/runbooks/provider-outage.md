# Runbook: AI Provider Outage (Gemini / OpenAI)

> **Severity:** High / Critical  
> **Target Audience:** On-call engineer (2 a.m. playbook)  
> **System Component:** `backend/mbiu/llm/`, `backend/mbiu/evaluation/orchestrator.py`  
> **Relevant Tickets:** MB-04, MB-20, MB-30  

---

## 1. Incident Overview & Symptoms

This runbook applies when the primary AI model provider (**Google Gemini**) or secondary provider (**OpenAI**) experiences severe latency, rate-limiting, or an outright service outage.

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
# Docker Compose local / staging
docker compose logs --tail=100 api | grep -E "LLMError|circuit_breaker|gemini|openai"

# Kubernetes / Production
kubectl logs -l app=mbiu-api --tail=100 | grep -E "LLMError|CircuitBreaker"
```

Look for the error category:
* `ErrorCategory.RATE_LIMITED` (`429`): Quota exhausted or unexpected traffic burst.
* `ErrorCategory.UNAVAILABLE` (`503` / `502`): Provider infrastructure down.
* `ErrorCategory.TIMEOUT`: Provider is responding too slowly (> `BATCH_TIMEOUT_S=30s`).

---

## 3. Mitigation & Failover Procedures

### Option A: Enable OpenAI Failover (Gemini Outage)
If Google Gemini is confirmed down and the circuit breaker is tripping, activate the OpenAI failover provider:

1. **Verify OpenAI Credentials & Quota:**
   Ensure `OPENAI_API_KEY` and `OPENAI_MODEL` (e.g. `gpt-4o-mini`) are populated in your secrets manager.
2. **Enable Failover in Runtime Environment:**
   Set `FAILOVER_ENABLED=true`:
   ```bash
   # In .env or deployment environment variables:
   FAILOVER_ENABLED=true
   ```
3. **Restart API Service:**
   ```bash
   # Docker Compose
   docker compose up -d api

   # Kubernetes
   kubectl rollout restart deployment/mbiu-api
   ```
4. **Confirm Privacy & Storage-Off Guarantee:**
   Confirm against [`docs/data-transfers.md`](file:///home/mercyline/Desktop/KAMILIMU%20LIMITED/Innovation/MBIU/mbiu/docs/data-transfers.md) that `store: false` is enforced on every call to OpenAI (verified in `mbiu.llm.openai`).

### Option B: Switch Gemini to Light Model (Latency / Rate Limit Spike)
If Gemini Flash (`gemini-3.8-flash`) is hitting rate limits or throttling, switch the primary model to the lighter tier:
```bash
# Update environment variable:
GEMINI_MODEL_MAIN=gemini-3.5-flash-lite
```
Restart the API service and monitor latency.

---

## 4. Verification & Recovery

1. **Run Smoke Test Evaluation:**
   Execute a test evaluation against the running API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/evaluations \
     -F "file=@infra/k6/fixtures/contract_40p.pdf" \
     -F "turnstile_token=1x0000000000000000000000000000000AA" \
     --header "traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01" \
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
       "corpus": "synthetic-v0"
     }
     ```

---

## 5. Reverting After Provider Restores

Once the primary provider (Gemini) announces resolution:
1. Revert `FAILOVER_ENABLED=false` in the deployment config.
2. If `GEMINI_MODEL_MAIN` was temporarily downgraded, revert to `gemini-3.8-flash`.
3. Restart the API workers.
4. Verify Gemini circuit breaker resets to `CLOSED`.
