# Runbook: AI Token & Cloud Spend Cost Spike

> **Severity:** High  
> **Target Audience:** On-call engineer (2 a.m. playbook)  
> **System Component:** `backend/config/settings.py`, `backend/mbiu/llm/`, Cloudflare Turnstile  

---

## 1. Incident Overview & Symptoms

Mbiu relies on paid commercial AI APIs (Google Gemini and OpenAI) with `store=False`. A runaway cost spike can drain operational budgets within hours if bot traffic bypasses challenge gates or users upload contracts with anomalous clause volumes.

### Quick Diagnostic Checks
1. **Is it real traffic or bots?** Check the pass rate and request volume in the Cloudflare dashboard under Turnstile.
2. **Recent API logs:** In Render: **mbiu-api → Logs** (or `docker compose logs --tail=200 api`).
3. **Are there unusually long contracts?** Uploads are capped by `MAX_UPLOAD_MB` and `MAX_PAGES`.

### Alert Triggers
* **Cloud Billing Alert:** Google Cloud Billing or OpenAI usage threshold alert (e.g., daily spend > $50 or token velocity > 10M tokens/hour).
* **Grafana Alert:** `mbiu_llm_tokens_consumed_hourly` exceeds 3x rolling average.
* **Turnstile Bypass Alert:** High volume of requests with missing or reused Turnstile tokens.
* **Traffic Anomaly:** Spike in concurrent evaluations from identical IP subnets or user agents.

---

## 2. Immediate 2 A.M. Triage (First 5 Minutes)

### Step 1: Check Current Token Burn Rate
Inspect live OpenTelemetry metrics or API logs for token consumption:
```bash
# Render logs
# Go to Render Dashboard -> mbiu-api -> Logs and filter by "input_tokens" or "budget"

# Or Docker Compose local / staging
docker compose logs --tail=200 api | grep -E "input_tokens|output_tokens|budget"

# Check Jaeger trace metrics on http://localhost:16686 (if running locally)
# Look for span: 'mbiu.batch_compare' and attribute: 'llm.total_tokens'
```

### Step 2: Identify Traffic Source (Legitimate vs Bot Attack)
1. **Cloudflare Turnstile Dashboard:**
   * Check the pass rate on [Cloudflare Dashboard -> Turnstile](https://dash.cloudflare.com/).
   * If the pass rate dropped or bot score is low, automated scrapers may be hitting the upload endpoint directly.
2. **Nginx / Ingress / Server Access Logs:**
   ```bash
   # Check top requester IPs
   tail -n 1000 /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -nr | head -n 10
   ```

---

## 3. Emergency Cost Mitigation Controls

Follow these tuning levers in order of severity. Note that updating environment variables in Render (**mbiu-api → Environment → Save**) triggers an immediate redeploy.

### Lever 1: Switch to Gemini Flash-Lite (Instant 70% Cost Reduction)
Immediately switch from the main comparison model to the lightweight model:
* **In Render:** Set `GEMINI_MODEL_MAIN=gemini-3.5-flash-lite` in **mbiu-api → Environment → Save**.
* **In Docker / Local:**
  ```bash
  GEMINI_MODEL_MAIN=gemini-3.5-flash-lite
  docker compose restart api
  ```
*Note: Flash-Lite processes evaluations with slightly simpler phrasing but remains within safety standards and dramatically cuts token unit price.*

### Lever 2: Restrict Token Budgets & Upload Caps
Lower the safety caps so oversized contracts are rejected before calling models:
* **In Render:** Set `MAX_PAGES=20` and lower token budgets in **mbiu-api → Environment**.
* **In `.env`:**
  ```bash
  # Lower upload caps
  MAX_PAGES=20

  # Reduce token ceiling from 400,000 to 150,000
  TOKEN_BUDGET_PER_CONTRACT=150000

  # Throttle concurrent model requests from 4 to 2
  LLM_CONCURRENCY=2

  # Increase batch size to 8 (packs more clauses into one system prompt, saving input tokens)
  BATCH_SIZE=8
  ```
  Restart the API service:
  ```bash
  docker compose restart api
  ```

### Lever 3: Enable Cloudflare Rate Limiting / "Under Attack" Mode
If automated bots are attacking the API endpoint:
1. Log into Cloudflare Dashboard.
2. Navigate to **Security -> WAF -> Rate Limiting Rules**.
3. Enforce a rule on `POST /api/v1/evaluations` and `POST /api/v1/clause-evaluations`:
   * **Limit:** 5 requests per IP per 10 minutes.
   * **Action:** Managed Challenge (Turnstile).
4. If necessary, toggle **Under Attack Mode** for `mbiu.org`.

### Lever 4: Emergency Spend Halt (Last Resort)
Stop all spend immediately:
* In Render: **mbiu-api → Settings → Suspend service**.
* Resume the service once the root cause has been identified and mitigated.

---

## 4. Verification & Stabilization

1. **Verify Spend Levels Off:**
   Verify that token consumption and spend slope levels off in the Google Cloud Billing / Metrics Explorer and OpenAI dashboards.
2. **Verify Token Caps Take Effect:**
   Upload a contract that exceeds the tuned token budget (or test with a synthetic contract from `evals/sample_contracts/pdf/`) and verify that the API rejects it cleanly with a user-friendly error before calling Gemini.
3. **Check Legitimate User Traffic:**
   Confirm that legitimate musicians on mobile devices are still receiving results in the web app and not encountering unhandled 500 errors.

---

## 5. Post-Incident Review & Afterwards

1. Set up a hard monthly quota cap and budget alert in Google Cloud Billing (prevents charges above the monthly grant).
2. Review Turnstile token validation logic in [`backend/mbiu/security/turnstile.py`](../../backend/mbiu/security/turnstile.py) to prevent token replay attacks.
3. Revert the model and upload caps, and resume the suspended service, once the incident is resolved.
4. Archive traffic logs for security audit.
