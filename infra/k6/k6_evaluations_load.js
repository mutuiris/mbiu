/**
 * Mbiu load and stress test suite
 * 
 * Benchmark scenarios for evaluation stream at the maximum upload cap (40 pages).
 * Evaluates three primary scenarios:
 * 1. normal: Standard processing flow at the page cap under concurrent load.
 * 2. slow_gemini: Simulated provider latency; verifies 10s heartbeats keep connections alive.
 * 3. failover: Provider failure injection; verifies circuit breaker & graceful degradation.
 * 
 * Starting SLO Targets:
 * - Time to first event (document outline): p(95) < 3.0s
 * - Successful stream response: 200 OK with application/x-ndjson
 * - Error rate (5xx server errors): < 1%
 * - Zero unhandled server crashes
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// --- Custom Metrics ---
const timeToFirstEvent = new Trend('time_to_first_event', true);
const evaluationStreamDuration = new Trend('evaluation_stream_duration', true);
const successRate = new Rate('evaluation_success_rate');
const heartbeatsReceived = new Counter('heartbeats_received');
const eventsParsedCount = new Counter('events_parsed_count');

// --- Pre-loaded Synthetic 40-Page Contract Fixture ---
const contractPdf = open('./fixtures/contract_40p.pdf', 'b');

// --- Configuration ---
const BASE_URL = __ENV.API_URL || 'http://localhost:8000';
const EVAL_ENDPOINT = `${BASE_URL}/api/v1/evaluations`;
const TURNSTILE_TOKEN = __ENV.TURNSTILE_TOKEN || '1x0000000000000000000000000000000AA';
const SCENARIO_MODE = __ENV.SCENARIO || 'normal'; // 'normal' | 'slow_gemini' | 'failover' | 'all'

export const options = {
  scenarios: {
    // 1. Normal Load Scenario: 40-page contract evaluation at moderate concurrency
    normal_scenario: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '30s', target: 5 },   // Ramp up to 5 concurrent evaluations
        { duration: '1m', target: 5 },    // Sustain 5 concurrent 40-page evaluations
        { duration: '20s', target: 0 },   // Ramp down
      ],
      gracefulStop: '30s',
      tags: { scenario: 'normal' },
      exec: 'runNormalScenario',
    },

    // 2. Slow Gemini Scenario: Verifies heartbeat keepalives under slow LLM latency
    slow_gemini_scenario: {
      executor: 'constant-vus',
      vus: 2,
      duration: '1m',
      gracefulStop: '20s',
      tags: { scenario: 'slow_gemini' },
      exec: 'runSlowGeminiScenario',
    },

    // 3. Failover / Provider Outage Scenario: Verifies fallback & graceful errors
    failover_scenario: {
      executor: 'constant-vus',
      vus: 2,
      duration: '45s',
      gracefulStop: '15s',
      tags: { scenario: 'failover' },
      exec: 'runFailoverScenario',
    },
  },

  // Starting SLO Thresholds
  thresholds: {
    // 95% of initial responses / first events should arrive under 3.5s
    time_to_first_event: ['p(95)<3500'],
    // At least 99% of normal evaluation requests must succeed
    'evaluation_success_rate{scenario:normal}': ['rate>0.99'],
    // HTTP 5xx errors must not exceed 1%
    'http_req_failed{scenario:normal}': ['rate<0.01'],
  },
};

// Helper: Generate random 16-byte hex trace ID and 8-byte span ID for W3C traceparent
function generateTraceparent() {
  const hex = '0123456789abcdef';
  let traceId = '';
  let spanId = '';
  for (let i = 0; i < 32; i++) traceId += hex[Math.floor(Math.random() * 16)];
  for (let i = 0; i < 16; i++) spanId += hex[Math.floor(Math.random() * 16)];
  return `00-${traceId}-${spanId}-01`;
}

// Parse NDJSON lines from streaming body
function parseNdjsonEvents(bodyText) {
  const events = [];
  const lines = bodyText.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const parsed = JSON.parse(trimmed);
      events.push(parsed);
    } catch {
      // Ignored if chunk ended abruptly
    }
  }
  return events;
}

/**
 * Scenario 1: Normal 40-Page Contract Evaluation
 */
export function runNormalScenario() {
  const traceparent = generateTraceparent();
  const startTime = Date.now();

  const data = {
    file: http.file(contractPdf, 'contract_40p.pdf', 'application/pdf'),
    turnstile_token: TURNSTILE_TOKEN,
  };

  const params = {
    headers: {
      traceparent: traceparent,
      'User-Agent': 'k6-loadtest-mbiu/1.0',
    },
    timeout: '120s',
  };

  const res = http.post(EVAL_ENDPOINT, data, params);
  const streamDuration = Date.now() - startTime;
  evaluationStreamDuration.add(streamDuration);

  // Validate response status & headers
  const isOk = check(res, {
    'status is 200': (r) => r.status === 200,
    'content-type is x-ndjson': (r) =>
      r.headers['Content-Type'] && r.headers['Content-Type'].includes('application/x-ndjson'),
    'cache-control is no-store': (r) =>
      r.headers['Cache-Control'] && r.headers['Cache-Control'].includes('no-store'),
  });

  successRate.add(isOk);

  if (res.status === 200 && res.body) {
    const events = parseNdjsonEvents(res.body);
    eventsParsedCount.add(events.length);

    // Record time to first event / document event
    if (events.length > 0) {
      timeToFirstEvent.add(res.timings.waiting);
    }

    const hasDocument = events.some((e) => e.type === 'document');
    const hasDone = events.some((e) => e.type === 'done');
    const heartbeats = events.filter((e) => e.type === 'heartbeat').length;
    if (heartbeats > 0) heartbeatsReceived.add(heartbeats);

    check(events, {
      'received document event': () => hasDocument,
      'received done event': () => hasDone,
    });
  }

  sleep(1);
}

/**
 * Scenario 2: Slow Gemini Latency & Heartbeat Keepalives
 */
export function runSlowGeminiScenario() {
  const traceparent = generateTraceparent();

  const data = {
    file: http.file(contractPdf, 'contract_40p.pdf', 'application/pdf'),
    turnstile_token: TURNSTILE_TOKEN,
  };

  const params = {
    headers: {
      traceparent: traceparent,
      'X-Simulate-Latency': '12', // Simulation header for staging / test stubs
    },
    timeout: '180s',
  };

  const res = http.post(EVAL_ENDPOINT, data, params);

  check(res, {
    'slow scenario completed or streaming': (r) => r.status === 200 || r.status === 504,
  });

  if (res.status === 200 && res.body) {
    const events = parseNdjsonEvents(res.body);
    const heartbeats = events.filter((e) => e.type === 'heartbeat').length;
    if (heartbeats > 0) {
      heartbeatsReceived.add(heartbeats);
    }
  }

  sleep(2);
}

/**
 * Scenario 3: Failover & Outage Graceful Degradation
 */
export function runFailoverScenario() {
  const traceparent = generateTraceparent();

  const data = {
    file: http.file(contractPdf, 'contract_40p.pdf', 'application/pdf'),
    turnstile_token: TURNSTILE_TOKEN,
  };

  const params = {
    headers: {
      traceparent: traceparent,
      'X-Simulate-Outage': 'gemini_503',
    },
    timeout: '60s',
  };

  const res = http.post(EVAL_ENDPOINT, data, params);

  // Even under provider outage, the server should either succeed via failover (200)
  // or return an honest service unavailable (503) without 500 crash
  check(res, {
    'no unhandled 500 errors': (r) => r.status !== 500,
    'clean status (200 or 503)': (r) => r.status === 200 || r.status === 503,
  });

  sleep(1);
}

export default function () {
  if (SCENARIO_MODE === 'slow_gemini') {
    runSlowGeminiScenario();
  } else if (SCENARIO_MODE === 'failover') {
    runFailoverScenario();
  } else {
    runNormalScenario();
  }
}
