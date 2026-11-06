# Runbook: AI Token & Cloud Spend Cost Spike

> **Severity:** High  
> **Target Audience:** On-call engineer (2 a.m. playbook)  
> **System Component:** `backend/config/settings.py`, `backend/mbiu/llm/`, Cloudflare Turnstile  
> **Relevant Tickets:** MB-04, MB-18, MB-20, MB-30  

---

## 1. Incident Overview & Symptoms

Mbiu relies on paid commercial AI APIs (Google Gemini and OpenAI) with `store=False`. A runaway cost spike can drain operational budgets within hours if bot traffic bypasses challenge gates or users upload contracts with anomalous clause volumes.

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
# Docker Compose logs
docker compose logs --tail=200 api | grep -E "input_tokens|output_tokens|budget"

# Check Jaeger trace metrics on http://localhost:16686
# Look for span: 'mbiu.batch_compare' and attribute: 'llm.total_tokens'
```

### Step 2: Identify Traffic Source (Legitimate vs Bot Attack)
1. **Cloudflare Turnstile Dashboard:**
   * Check the pass rate on [Cloudflare Dashboard -> Turnstile](https://dash.cloudflare.com/).
   * If the pass rate dropped or bot score is low, automated scrapers may be hitting the upload endpoint directly.
2. **Nginx / Ingress Access Logs:**
   ```bash
   # Check top requester IPs
   tail -n 1000 /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -nr | head -n 10
   ```

---

## 3. Emergency Cost Mitigation Controls

Follow these tuning levers in order of severity:

### Lever 1: Switch to Gemini Flash-Lite (Instant 70% Cost Reduction)
Immediately switch from the main comparison model to the lightweight model:
```bash
# In .env or runtime config:
GEMINI_MODEL_MAIN=gemini-3.5-flash-lite
```
Restart the API service:
```bash
docker compose restart api
```
*Note: Flash-Lite processes evaluations with slightly simpler phrasing but remains within safety standards and dramatically cuts token unit price.*

### Lever 2: Restrict Token Budgets in `.env`
Lower the safety caps so oversized contracts are rejected before calling models:
```bash
# In .env:
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

### Lever 3: Enable Cloudflare "Under Attack" Mode / Rate Limiting
If automated bots are attacking the API endpoint:
1. Log into Cloudflare Dashboard.
2. Navigate to **Security -> WAF -> Rate Limiting Rules**.
3. Enforce a rule on `POST /api/v1/evaluations`:
   * **Limit:** 5 requests per IP per 10 minutes.
   * **Action:** Managed Challenge (Turnstile).
4. If necessary, toggle **Under Attack Mode** for `mbiu.org`.

---

## 4. Verification & Stabilization

1. **Verify Token Caps Take Effect:**
   Upload a contract that exceeds the tuned token budget and verify that the API rejects it cleanly with a user-friendly error before calling Gemini.
2. **Monitor Google Cloud Console:**
   Verify that the token consumption slope levels off in the Google Cloud Metrics Explorer.
3. **Check Error Rates:**
   Confirm that legitimate musicians on mobile devices are still receiving results and not hitting artificial 500 errors.

---

## 5. Post-Incident Review
1. Set up hard monthly quota caps in the Google Cloud Billing Console (prevents charges above the monthly grant).
2. Review Turnstile token validation logic in [`backend/mbiu/security/turnstile.py`](file:///home/mercyline/Desktop/KAMILIMU%20LIMITED/Innovation/MBIU/mbiu/backend/mbiu/security/turnstile.py) to prevent token replay attacks.
3. Archive traffic logs for security audit.
