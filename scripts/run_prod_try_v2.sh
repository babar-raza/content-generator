#!/usr/bin/env bash
# Production Try Runner V2 - Official Acceptance Gate
# Runs 3 scenarios × 3 topics = 9 validations (Engine, REST, MCP)
# STOP-THE-LINE: Does not declare success unless 9/9 PASS

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

echo "========================================="
echo "Production Try Runner V2 - Acceptance Gate"
echo "========================================="

# Generate timestamp (Asia/Karachi = UTC+5)
TIMESTAMP=${PROD_TRY_TIMESTAMP:-$(TZ='Asia/Karachi' date +%Y%m%d-%H%M)}
export PROD_TRY_TIMESTAMP=$TIMESTAMP
export TEST_MODE=live
export LLM_PROVIDER=OLLAMA
export ALLOW_NETWORK=1

REPORT_DIR="reports/prod_try_v2/$TIMESTAMP"
mkdir -p "$REPORT_DIR"

echo "Timestamp: $TIMESTAMP"
echo "Test Mode: $TEST_MODE"
echo "Report Dir: $REPORT_DIR"
echo ""

# =============================================================================
# PREFLIGHT CHECKS
# =============================================================================
echo "=== PREFLIGHT CHECKS ==="

echo "Checking Ollama..."
if ! curl -sf http://localhost:11434/api/tags > /dev/null; then
    echo "ERROR: Ollama not running on http://localhost:11434"
    echo "Please start Ollama: ollama serve"
    exit 1
fi

echo "Checking Ollama model (phi4-mini)..."
# Use venv Python if available for model check
if [ -f ".venv_stage/Scripts/python.exe" ]; then
    CHECK_PYTHON=".venv_stage/Scripts/python.exe"
elif [ -f ".venv_stage/bin/python" ]; then
    CHECK_PYTHON=".venv_stage/bin/python"
else
    CHECK_PYTHON="python"
fi
MODELS=$(curl -s http://localhost:11434/api/tags | $CHECK_PYTHON -c "import sys, json; data=json.load(sys.stdin); print([m['name'] for m in data.get('models', [])])")
if [[ ! "$MODELS" =~ "phi4-mini:latest" ]]; then
    echo "ERROR: phi4-mini:latest model not found"
    echo "Please pull model: ollama pull phi4-mini"
    exit 1
fi
echo "Ollama OK (phi4-mini:latest found)"

echo "Checking ChromaDB..."
# Check for HTTP ChromaDB (docker-compose) or persistent mode
if [[ -n "${CHROMA_HOST:-}" ]] && [[ -n "${CHROMA_PORT:-}" ]]; then
    # Try v2 API first, then fall back to v1
    if ! curl -sf "http://${CHROMA_HOST}:${CHROMA_PORT}/api/v2/heartbeat" > /dev/null 2>&1 && \
       ! curl -sf "http://${CHROMA_HOST}:${CHROMA_PORT}/api/v1/heartbeat" > /dev/null 2>&1; then
        echo "WARNING: ChromaDB not reachable at http://${CHROMA_HOST}:${CHROMA_PORT}"
        echo "Attempting to start ChromaDB via docker-compose..."
        if docker-compose -f docker-compose.chromadb.yml up -d 2>/dev/null || docker compose -f docker-compose.chromadb.yml up -d 2>/dev/null; then
            sleep 5
            if curl -sf "http://${CHROMA_HOST}:${CHROMA_PORT}/api/v2/heartbeat" > /dev/null 2>&1 || \
               curl -sf "http://${CHROMA_HOST}:${CHROMA_PORT}/api/v1/heartbeat" > /dev/null 2>&1; then
                echo "ChromaDB started successfully"
            else
                echo "ERROR: ChromaDB still not reachable"
                exit 1
            fi
        else
            echo "ERROR: Could not start ChromaDB"
            exit 1
        fi
    else
        echo "ChromaDB HTTP OK at http://${CHROMA_HOST}:${CHROMA_PORT}"
    fi
else
    echo "ChromaDB: Using persistent client mode (./chroma_db)"
fi

echo "Checking Python..."
if ! python --version > /dev/null 2>&1; then
    echo "ERROR: Python not found"
    exit 1
fi
echo "Python OK"

echo ""
echo "=== PREFLIGHT PASSED ==="
echo ""

# =============================================================================
# RUN PRODUCTION TRY MATRIX
# =============================================================================
echo "=== RUNNING PRODUCTION TRY MATRIX V2 ==="

# Use venv Python if available, otherwise use system Python
if [ -f ".venv_stage/Scripts/python.exe" ]; then
    PYTHON_CMD=".venv_stage/Scripts/python.exe"
    echo "Using venv Python: $PYTHON_CMD"
elif [ -f ".venv_stage/bin/python" ]; then
    PYTHON_CMD=".venv_stage/bin/python"
    echo "Using venv Python: $PYTHON_CMD"
else
    PYTHON_CMD="python"
    echo "Using system Python: $PYTHON_CMD"
fi

echo "Running: $PYTHON_CMD tools/prod_try_runner.py --ts $TIMESTAMP"
echo ""

if $PYTHON_CMD tools/prod_try_runner.py --ts "$TIMESTAMP"; then
    EXIT_CODE=0
else
    EXIT_CODE=$?
fi

echo ""

# =============================================================================
# VALIDATE 9/9 PASS
# =============================================================================
RESULTS_JSON="$REPORT_DIR/matrix_results.json"
if [ -f "$RESULTS_JSON" ]; then
    PASS_COUNT=$($PYTHON_CMD -c "import json; d=json.load(open('$RESULTS_JSON')); print(d.get('pass_count', 0))")
    TOTAL_RUNS=$($PYTHON_CMD -c "import json; d=json.load(open('$RESULTS_JSON')); print(d.get('total_runs', 0))")

    if [ "$PASS_COUNT" -ne "$TOTAL_RUNS" ] || [ "$TOTAL_RUNS" -ne 9 ]; then
        echo "STOP-THE-LINE: Matrix is $PASS_COUNT/$TOTAL_RUNS (expected 9/9)"
        exit 1
    fi
else
    echo "ERROR: Results JSON not found at $RESULTS_JSON"
    exit 1
fi

# =============================================================================
# CREATE EVIDENCE TARBALL
# =============================================================================
if [ $EXIT_CODE -eq 0 ]; then
    echo "=== PRODUCTION TRY V2: 9/9 PASS ==="

    TARBALL_PATH="$REPORT_DIR/prod_try_v2_${TIMESTAMP}_evidence.tar.gz"

    echo ""
    echo "=== CREATING EVIDENCE TARBALL ==="

    tar -czf "$TARBALL_PATH" \
        "$REPORT_DIR/" \
        "scripts/run_prod_try_v2.sh" \
        "scripts/run_prod_try_v2.ps1" \
        "tools/prod_try_runner.py" \
        2>/dev/null || true

    if [ -f "$TARBALL_PATH" ]; then
        echo "Evidence tarball: $TARBALL_PATH"
    fi

    echo ""
    echo "========================================="
    echo "FINAL SUMMARY"
    echo "========================================="
    echo "1) TS: $TIMESTAMP"
    echo "2) Matrix: $PASS_COUNT/$TOTAL_RUNS PASS"
    echo "3) Evidence: $TARBALL_PATH"
    echo "========================================="

    exit 0
else
    echo "=== PRODUCTION TRY V2: FAIL ==="
    echo "Results: $REPORT_DIR/"
    echo "Check logs for details"
    exit $EXIT_CODE
fi
