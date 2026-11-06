# Runbook: Supabase Project Paused or Connection Pooler Saturated

> **Severity:** Critical  
> **Target Audience:** On-call engineer (2 a.m. playbook)  
> **System Component:** `backend/config/settings.py`, Supabase PostgreSQL / Supavisor  
> **Relevant Tickets:** MB-10, MB-28, MB-30  

---

## 1. Incident Overview & Symptoms

Mbiu uses Supabase PostgreSQL to host public reviewed standard templates, Kenyan statutes, and guidance. The API does not store uploaded contracts, but it reads the standard templates snapshot at startup.

If the Supabase project enters a **PAUSED** state (due to free-tier inactivity, maintenance, or billing hold) or if the **connection pooler** is exhausted, the API health check will fail and startup snapshots cannot be fetched.

### Alert Triggers
* **Health Check Failure:** `GET /readyz` returns `503 Service Unavailable` with `database: false`.
* **Sentry / Log Alert:** `django.db.utils.OperationalError: could not connect to server: Connection refused` or `FATAL: remaining connection slots are reserved`.
* **Supabase Web Console:** Project status shows **"PAUSED"**.

---

## 2. Immediate 2 A.M. Triage (First 5 Minutes)

### Step 1: Differentiate Port 6543 vs Port 5432
Mbiu configures two distinct database connection URLs:
1. **`DATABASE_URL` (Port 6543 — Transaction Mode Pooler):**
   * Connects via Supavisor / PgBouncer for API traffic.
   * **Mandatory Setting:** `CONN_MAX_AGE: 0` in Django settings to ensure connections are released immediately after each query.
2. **`DATABASE_DIRECT_URL` (Port 5432 — Session Mode / Direct):**
   * Used strictly for running schema migrations (`manage.py migrate`) and heavy corpus batch ingestion scripts.

### Step 2: Check API Health Endpoint
Test the database readiness check directly:
```bash
curl -i http://localhost:8000/readyz
```
* If HTTP `200`: Database is connected and healthy.
* If HTTP `503`: Database connection failed. Check output for diagnostic message.

---

## 3. Recovery Procedures

### Scenario A: Supabase Project is Paused (Dashboard Unpause)
1. Log into the [Supabase Dashboard](https://supabase.com/dashboard).
2. Select the `mbiu` project.
3. If the project banner displays **"Project is paused"**:
   * Click **"Restore Project"** (or **"Unpause Project"**).
   * Project restoration takes approximately 60 to 120 seconds while PostgreSQL containers are spun up.
4. Once the dashboard indicates **"Active"**, test the connection:
   ```bash
   docker compose exec api python -c "from django.db import connection; connection.cursor(); print('Connected successfully!')"
   ```
5. Restart the API service:
   ```bash
   # Docker Compose
   docker compose restart api

   # Kubernetes
   kubectl rollout restart deployment/mbiu-api
   ```

### Scenario B: Connection Pooler (Supavisor) Exhaustion
If the database is active but connections are timing out with pooler errors:
1. **Verify `CONN_MAX_AGE` Setting:**
   Confirm in [`backend/config/settings.py`](file:///home/mercyline/Desktop/KAMILIMU%20LIMITED/Innovation/MBIU/mbiu/backend/config/settings.py) that `CONN_MAX_AGE` is set to `0`:
   ```python
   # Must be 0 for transaction-mode poolers
   "CONN_MAX_AGE": 0,
   ```
   *(A non-zero value holds connections open, exhausting the pooler within minutes).*
2. **Restart Supavisor Pooler:**
   * Go to **Supabase Dashboard -> Settings -> Database -> Connection Pooler**.
   * Click **Restart Pooler**.
3. **Emergency Direct Connection (Temporary Workaround):**
   If the pooler on port 6543 is unresponsive, temporarily route API traffic through the session pooler on port 5432:
   ```bash
   # Temporarily set DATABASE_URL to use port 5432 in .env
   DATABASE_URL=postgresql://postgres.xxx:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
   ```
   Restart the API service and monitor recovery.

### Scenario C: Fallback to Local PostgreSQL (Total Cloud Outage)
If Supabase is experiencing a protracted multi-region cloud outage:
1. Spin up the local PostgreSQL container with the seed corpus:
   ```bash
   docker compose up -d postgres pgbouncer
   uv run --directory backend python ../scripts/seed_local_corpus.py
   ```
2. Point the API to the local PgBouncer instance:
   ```bash
   DATABASE_URL=postgresql://mbiu:PASSWORD@localhost:6432/mbiu
   ```
3. Restart the API service. All evaluation features will continue functioning against the local template snapshot.

---

## 4. Verification & Health Check

1. **Verify Health Endpoint:**
   ```bash
   curl -f http://localhost:8000/readyz
   ```
   Ensure output is `{"status": "ready", "database": true}`.
2. **Run Quick Stream Check:**
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/evaluations \
     -F "file=@infra/k6/fixtures/contract_40p.pdf" \
     -F "turnstile_token=1x0000000000000000000000000000000AA" \
     | head -n 3
   ```
   Ensure the `document` event returns immediately.

---

## 5. Preventative Measures
* **Upgrade to Supabase Pro:** Prevents free-tier automatic pausing after 7 days of inactivity.
* **Automated Health Check Monitor:** Set up an external UptimeRobot / BetterUptime ping on `/readyz` every 5 minutes to keep the database active and alert immediately if downtime occurs.
