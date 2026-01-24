#!/bin/bash
# verify_all.sh
# One-command verification script for content-generator
# Runs all mock-mode gates required for release

set -e

INCLUDE_LIVE=false
if [[ "$1" == "--live" ]]; then
    INCLUDE_LIVE=true
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
VENV_DIR="$REPO_ROOT/.venv_verify"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "================================================"
echo "Content Generator - Local Verification Suite"
echo "================================================"
echo ""

# Create or activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "[SETUP] Creating verification venv..."
    python3 -m venv "$VENV_DIR"
else
    echo "[SETUP] Using existing verification venv"
fi

# Install dependencies
echo "[SETUP] Installing dependencies..."
"$PIP" install -q -r "$REPO_ROOT/requirements.txt"

# Initialize counters
failed_tests=0

# Create output directory for this run
timestamp=$(date +"%Y%m%d-%H%M%S")
output_dir="$REPO_ROOT/reports/_local_verify/$timestamp"
mkdir -p "$output_dir"

echo ""
echo "================================================"
echo "GATE 1: Unit Tests"
echo "================================================"

if "$PYTHON" -m pytest -q tests/unit 2>&1 | tee "$output_dir/unit.txt"; then
    echo "[PASS] Unit tests"
else
    echo "[FAIL] Unit tests"
    ((failed_tests++))
fi

echo ""
echo "================================================"
echo "GATE 2: Integration Tests"
echo "================================================"

if "$PYTHON" -m pytest -q tests/integration 2>&1 | tee "$output_dir/integration.txt"; then
    echo "[PASS] Integration tests"
else
    echo "[FAIL] Integration tests"
    ((failed_tests++))
fi

echo ""
echo "================================================"
echo "GATE 3: E2E Mock Tests"
echo "================================================"

if "$PYTHON" -m pytest -q tests/e2e_mock 2>&1 | tee "$output_dir/e2e_mock.txt"; then
    echo "[PASS] E2E mock tests"
else
    echo "[FAIL] E2E mock tests"
    ((failed_tests++))
fi

echo ""
echo "================================================"
echo "GATE 4: Capability Mock Tests"
echo "================================================"

cap_mock_dir="$output_dir/capability_mock"
if "$PYTHON" "$REPO_ROOT/tools/run_capabilities.py" --mode mock --outdir "$cap_mock_dir" --timeout_seconds 180 2>&1 | tee "$output_dir/capability_mock.txt"; then
    echo "[PASS] Capability mock tests"
else
    echo "[FAIL] Capability mock tests"
    ((failed_tests++))
fi

# Optional: Live mode
if [ "$INCLUDE_LIVE" = true ]; then
    echo ""
    echo "================================================"
    echo "OPTIONAL: Live Tests"
    echo "================================================"

    # Check for required environment variables
    live_ready=true
    for var in ANTHROPIC_API_KEY GOOGLE_API_KEY; do
        if [ -z "${!var}" ]; then
            echo "[SKIP] Missing environment variable: $var"
            live_ready=false
        fi
    done

    if [ "$live_ready" = true ]; then
        echo "[INFO] Running live tests..."
        "$PYTHON" -m pytest -q -m live tests/live 2>&1 | tee "$output_dir/live.txt" || true

        cap_live_dir="$output_dir/capability_live"
        "$PYTHON" "$REPO_ROOT/tools/run_capabilities.py" --mode live --outdir "$cap_live_dir" --timeout_seconds 180 2>&1 | tee "$output_dir/capability_live.txt" || true
    else
        echo "[SKIP] Live tests - missing required environment variables"
    fi
fi

echo ""
echo "================================================"
echo "VERIFICATION SUMMARY"
echo "================================================"
echo "Results saved to: $output_dir"
echo ""

if [ $failed_tests -gt 0 ]; then
    echo "[FAIL] $failed_tests gate(s) failed - DO NOT COMMIT"
    exit 1
else
    echo "[PASS] All gates passed - ready for release"
    exit 0
fi
