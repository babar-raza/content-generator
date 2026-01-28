#!/usr/bin/env bash
# Live E2E Full Test Runner - Real Ollama + ChromaDB
# Runs all 5 phases: Preflight, Ingestion, Workflow, REST, MCP
# STOP-THE-LINE: Exit on any phase failure

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

echo "========================================="
echo "Live E2E Test Runner - Ollama + ChromaDB"
echo "========================================="

# Generate timestamp
TIMESTAMP=${LIVE_E2E_TIMESTAMP:-$(TZ='Asia/Karachi' date +%Y%m%d-%H%M)}
export LIVE_E2E_TIMESTAMP=$TIMESTAMP
export TEST_MODE=live

echo "Timestamp: $TIMESTAMP"
echo "Test Mode: $TEST_MODE"

# Preflight checks
echo ""
echo "=== PREFLIGHT CHECKS ==="

echo "Checking Ollama..."
if ! curl -sf http://localhost:11434/api/tags > /dev/null; then
    echo "ERROR: Ollama not running on http://localhost:11434"
    echo "Please start Ollama: ollama serve"
    exit 1
fi

echo "Checking Ollama model (phi4-mini)..."
MODELS=$(curl -s http://localhost:11434/api/tags | python -c "import sys, json; data=json.load(sys.stdin); print([m['name'] for m in data.get('models', [])])")
if [[ ! "$MODELS" =~ "phi4-mini:latest" ]]; then
    echo "ERROR: phi4-mini:latest model not found"
    echo "Please pull model: ollama pull phi4-mini"
    exit 1
fi

echo "Checking Docker..."
if ! docker version > /dev/null 2>&1; then
    echo "ERROR: Docker not available"
    echo "Please install Docker and ensure it's running"
    exit 1
fi

echo "Checking Python..."
if ! python --version > /dev/null 2>&1; then
    echo "ERROR: Python not found"
    exit 1
fi

echo ""
echo "=== PREFLIGHT PASSED ==="
echo ""

# Run the main Live E2E suite
echo "=== RUNNING LIVE E2E SUITE ==="
echo "Running: python tools/live_e2e/run_live_e2e.py"
echo ""

if python tools/live_e2e/run_live_e2e.py; then
    EXIT_CODE=$?
else
    EXIT_CODE=$?
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "=== LIVE E2E TEST: PASS ==="
    echo "Results: reports/live_e2e_full_v3_gates/$TIMESTAMP/"

    # Create evidence tarball
    TARBALL_PATH="reports/live_e2e_prod/$TIMESTAMP/live_e2e_prod_evidence_$TIMESTAMP.tar.gz"
    mkdir -p "reports/live_e2e_prod/$TIMESTAMP"

    echo ""
    echo "=== CREATING EVIDENCE TARBALL ==="
    tar -czf "$TARBALL_PATH" \
        "reports/live_e2e_full_v3_gates/$TIMESTAMP/" \
        "docs/live_e2e/README.md" \
        "scripts/run_live_e2e_ollama_real.sh" \
        "scripts/run_live_e2e_ollama_real.ps1" \
        2>/dev/null || true

    if [ -f "$TARBALL_PATH" ]; then
        echo "Evidence tarball: $TARBALL_PATH"
    fi

    exit 0
else
    echo "=== LIVE E2E TEST: FAIL ==="
    echo "Results: reports/live_e2e_full_v3_gates/$TIMESTAMP/"
    echo "Check logs for details"
    exit $EXIT_CODE
fi
