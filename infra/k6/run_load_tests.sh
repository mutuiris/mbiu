#!/usr/bin/env bash
# ==============================================================================
# Mbiu Load Testing Runner Script — Ticket MB-30
#
# Runs k6 evaluation stream load benchmarks against a target Mbiu API instance.
# Usage:
#   ./infra/k6/run_load_tests.sh [scenario] [api_url]
#
# Examples:
#   ./infra/k6/run_load_tests.sh normal http://localhost:8000
#   ./infra/k6/run_load_tests.sh slow_gemini http://localhost:8000
#   ./infra/k6/run_load_tests.sh failover http://localhost:8000
#   ./infra/k6/run_load_tests.sh all http://localhost:8000
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SCENARIO="${1:-${SCENARIO:-normal}}"
API_URL="${2:-${API_URL:-http://localhost:8000}}"
TURNSTILE_TOKEN="${TURNSTILE_TOKEN:-1x0000000000000000000000000000000AA}"
FIXTURE_PATH="${SCRIPT_DIR}/fixtures/contract_40p.pdf"

echo "========================================================================"
echo " Mbiu k6 Load Benchmark: Scenario '${SCENARIO}'"
echo " Target Endpoint : ${API_URL}/api/v1/evaluations"
echo " Page Cap Fixture: ${FIXTURE_PATH}"
echo "========================================================================"

# Step 1: Ensure fixture exists
if [[ ! -f "${FIXTURE_PATH}" ]]; then
  echo "[-] Fixture not found. Generating synthetic 40-page contract..."
  uv run --directory "${REPO_ROOT}/backend" python "${SCRIPT_DIR}/generate_40p_contract.py"
fi

# Step 2: Verify k6 is available
if ! command -v k6 &> /dev/null; then
  echo "[-] k6 binary not found in PATH. Checking ~/.local/bin/k6..."
  if [[ -x "${HOME}/.local/bin/k6" ]]; then
    export PATH="${HOME}/.local/bin:${PATH}"
  else
    echo "[!] Error: k6 is not installed. Please install k6 before proceeding."
    exit 1
  fi
fi

# Step 3: Run pre-flight health check (optional, non-blocking if target is remote)
echo "[+] Checking API readiness at ${API_URL}/readyz..."
if curl -sf --connect-timeout 3 "${API_URL}/readyz" > /dev/null 2>&1; then
  echo "[+] API is healthy and ready for load tests."
else
  echo "[!] Warning: API at ${API_URL}/readyz did not respond immediately. Continuing..."
fi

# Step 4: Run k6 scenario
echo "[+] Executing k6 load test..."
cd "${SCRIPT_DIR}"

if [[ "${SCENARIO}" == "all" ]]; then
  k6 run \
    -e API_URL="${API_URL}" \
    -e TURNSTILE_TOKEN="${TURNSTILE_TOKEN}" \
    k6_evaluations_load.js
else
  k6 run \
    -e API_URL="${API_URL}" \
    -e TURNSTILE_TOKEN="${TURNSTILE_TOKEN}" \
    -e SCENARIO="${SCENARIO}" \
    k6_evaluations_load.js
fi

echo "[+] Load benchmark completed successfully."
