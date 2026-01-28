#!/bin/bash
# Live E2E Full Test Runner (Bash)
set -e

TS=$(date +"%Y%m%d-%H%M")
echo "=== LIVE E2E FULL TEST ==="
echo "Timestamp: $TS"

# Check prerequisites
echo -e "\nChecking prerequisites..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "[OK] Ollama reachable"
else
    echo "[FAIL] Ollama not reachable"
    exit 1
fi

# Phase 2
echo -e "\n=== PHASE 2: WORKFLOW E2E ==="
python tools/run_live_workflow_simple.py --workflow blog_workflow --topic "FastAPI Tutorial" --output-dir ".live_e2e_data/$TS/outputs" --report-dir "reports/live_e2e_full/$TS"
echo "[PASS] Phase 2 completed"

# Phase 3
echo -e "\n=== PHASE 3: WEB + MCP E2E ==="
python tools/run_live_web_mcp_e2e.py --report-dir "reports/live_e2e_full/$TS"
echo "[PASS] Phase 3 completed"

echo -e "\n[SUCCESS] All phases passed"
echo "Reports: reports/live_e2e_full/$TS/"
