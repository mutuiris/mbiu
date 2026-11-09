# Runbook: Corpus Rollback (Flipping `active_corpus_version` Back)

> **Severity:** High  
> **Target Audience:** On-call engineer (2 a.m. playbook)  
> **System Component:** `backend/mbiu/corpus/`, `scripts/seed_local_corpus.py`, `backend/config/settings.py`  
> **Relevant Tickets:** MB-10, MB-12, MB-13, MB-19, MB-30  

---

## 1. Incident Overview & Symptoms

The standard reference corpus contains reviewed contract templates, Kenya Copyright Act Cap. 130 provisions, and KECOBO guidance. When a newly published corpus pipeline release introduces corrupted template text, bad embeddings, or incorrect royalty benchmarks, artists will receive faulty advice or unexpected `cannot_compare` (⚪ Couldn't compare) outcomes.

### Alert Triggers
* **Quality Gate Failure:** Golden set evaluation regression (`cannot_compare` rate > 10% or planted risks missed).
* **Musician Feedback / Support Escalation:** Inaccurate comparison advice reported on standard recording or publishing clauses.
* **Database Inconsistency:** Unverified template chunks or invalid license metadata flagged in audit queries.

---

## 2. Immediate 2 A.M. Triage (First 5 Minutes)

### Step 1: Identify the Current & Previous Corpus Versions
Check the active corpus version currently loaded in the running API:
```bash
# Check the API health / settings via Docker / container
docker compose exec api python -c "from django.conf import settings; print('Active corpus:', getattr(settings, 'ACTIVE_CORPUS_VERSION', 'unknown'))"
```

Inspect the database corpus version table:
```bash
docker compose exec postgres psql -U mbiu -d mbiu -c "
SELECT version_id, published_at, is_active, notes 
FROM corpus_versions 
ORDER BY published_at DESC 
LIMIT 5;
"
```

Identify:
* **Failing Active Version:** e.g., `corpus-2026-11-05-v2`
* **Last Known Good Version:** e.g., `synthetic-v0` or `corpus-2026-10-27-v1`

---

## 3. Rollback Execution Procedure

### Step 1: Flip the Active Version in Database
Deactivate the failing version and mark the last known good version as active:
```sql
-- Connect via psql:
-- docker compose exec postgres psql -U mbiu -d mbiu

BEGIN;

-- 1. Deactivate current flawed version
UPDATE corpus_versions 
SET is_active = FALSE 
WHERE is_active = TRUE;

-- 2. Activate last known good version (e.g., 'synthetic-v0')
UPDATE corpus_versions 
SET is_active = TRUE 
WHERE version_id = 'synthetic-v0';

COMMIT;
```

### Step 2: Update Runtime Environment Variable
Ensure the environment variable `ACTIVE_CORPUS_VERSION` points to the target rollback version so worker processes initialize with the correct snapshot:
```bash
# In .env or deployment manifest:
ACTIVE_CORPUS_VERSION=synthetic-v0
```

### Step 3: Restart API Workers to Reload Startup Snapshot
Mbiu caches standard templates in an in-memory startup snapshot on worker boot to eliminate per-request database queries. You **must restart the workers** to load the rolled-back snapshot:
```bash
# Docker Compose
docker compose restart api

# Kubernetes
kubectl rollout restart deployment/mbiu-api
```

---

## 4. Verification & Health Check

### Step 1: Run Smoke Evaluation Test
Verify that an evaluation response returns the rolled-back corpus version in the `done` event:
```bash
curl -s -X POST http://localhost:8000/api/v1/evaluations \
  -F "file=@infra/k6/fixtures/contract_40p.pdf" \
  -F "turnstile_token=1x0000000000000000000000000000000AA" \
  | grep -o '"corpus":"[^"]*"'
```
**Expected Output:** `"corpus":"synthetic-v0"`

### Step 2: Run Golden Set Quality Gate Check
Run the offline evaluation gate against the synthetic Golden Set:
```bash
uv run --directory backend pytest ../tests/test_golden_set_eval.py
```
Confirm:
* Zero planted risky clauses classified as `matches_standard`.
* All cross-clause conflicts detected cleanly.

---

## 5. Post-Incident Actions
1. Mark the corrupted corpus version as deprecated in `corpus/sources.yaml`.
2. File a bug ticket for the ingestion pipeline team (MB-12 / MB-13).
3. Do not re-trigger the corpus publish action until root-cause analysis on the rejected source templates is completed.
