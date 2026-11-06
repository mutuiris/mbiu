# Mbiu Load Testing Suite (k6)

**Ticket:** MB-30 · Load tests and runbooks  
**Scope:** Performance, concurrency, and reliability benchmarks for the Evaluation Stream (`POST /api/v1/evaluations`) at the maximum upload page cap (40 pages).

---

## 1. Overview

Mbiu processes English-language music contracts for Kenyan musicians in real-time. Because contract evaluations stream results via NDJSON over mobile data connections, the system must meet strict Service Level Objectives (SLOs) without unbounded memory growth or dropping connections.

All tests utilize a pre-generated **synthetic 40-page contract** ([`fixtures/contract_40p.pdf`](fixtures/contract_40p.pdf)), guaranteeing compliance with the project rule that **real contracts are never used in test suites**.

---

## 2. Starting Service Level Objectives (SLOs)

| Metric | SLO Target | Business Rationale |
|---|---|---|
| **Time to First Event (TTFE)** | `p(95) < 3.0s` | Mobile artists must receive the `document` event immediately so the contract outline appears without perceived latency. |
| **Normal Evaluation Success Rate** | `> 99.0%` | Less than 1% failure rate for valid 40-page uploads under concurrent traffic. |
| **Server Error Rate (5xx)** | `< 1.0%` | Zero unhandled exceptions (`500`); transient failures must map to structured errors. |
| **Heartbeat Keepalive Interval** | `10s ± 1s` | Emitted periodically during model batch processing to prevent mobile carrier and proxy timeouts. |
| **Hard Processing Deadline** | `≤ 300s (5 min)` | Enforced by `DEADLINE_CAP_S`; requests exceeding this are safely terminated to prevent resource leaks. |
| **Memory Invariant** | `0 bytes to disk` | PDF extraction and streaming occur entirely in memory; buffers are freed immediately on stream completion or disconnect. |

---

## 3. Test Scenarios

### Scenario 1: `normal`
* **What it tests:** Happy-path stream processing under ramping load (1 to 5 concurrent 40-page evaluations).
* **Checks:**
  * HTTP status `200 OK`
  * Response headers: `Content-Type: application/x-ndjson`, `Cache-Control: no-store`
  * Presence of initial `document` event and final `done` event
  * Time to first event and total stream duration

### Scenario 2: `slow_gemini`
* **What it tests:** Behavior when the primary AI model experiences latency (> 10s per batch).
* **Checks:**
  * Emission of `heartbeat` events every 10 seconds
  * Client connection survival without gateway timeouts (HTTP `504`)
  * Proper stream completion within deadline

### Scenario 3: `failover`
* **What it tests:** Behavior during provider degradation, rate limits (`429`), or outages (`503`).
* **Checks:**
  * Seamless failover to secondary provider when `FAILOVER_ENABLED=true`
  * Clean, structured error events (`clause_failed` or `service_unavailable`) when failover is unavailable, with an honest Retry button
  * Zero unhandled `500 Internal Server Error` crashes

---

## 4. How to Run

### Prerequisites
* `k6` installed (`v2.0+` or `v0.50+`)
* Mbiu API running on `http://localhost:8000` (or via Docker Compose: `just dev`)

### Quick Start
```bash
# Run the default normal scenario
./infra/k6/run_load_tests.sh normal

# Run the slow provider heartbeat test
./infra/k6/run_load_tests.sh slow_gemini

# Run the failover / provider outage test
./infra/k6/run_load_tests.sh failover

# Run all scenarios sequentially
./infra/k6/run_load_tests.sh all
```

### Direct k6 Command
```bash
k6 run \
  -e API_URL=http://localhost:8000 \
  -e TURNSTILE_TOKEN=1x0000000000000000000000000000000AA \
  -e SCENARIO=normal \
  infra/k6/k6_evaluations_load.js
```

---

## 5. Regenerating the 40-Page Fixture

If the 40-page contract fixture ever needs modification or regeneration:
```bash
uv run --directory backend python ../infra/k6/generate_40p_contract.py
```
This generates [`fixtures/contract_40p.pdf`](fixtures/contract_40p.pdf) with 40 distinct synthetic contract clauses and page provenance.
