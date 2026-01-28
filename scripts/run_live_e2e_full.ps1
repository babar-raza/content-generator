# Live E2E Full Test Runner (PowerShell)
# Runs Phase 2-3 end-to-end with fail-fast

$ErrorActionPreference = "Stop"

$TS = Get-Date -Format "yyyyMMdd-HHmm"
Write-Host "=== LIVE E2E FULL TEST ===" -ForegroundColor Cyan
Write-Host "Timestamp: $TS" -ForegroundColor Gray

# Check prerequisites
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow
try {
    $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -UseBasicParsing
    Write-Host "[OK] Ollama reachable" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Ollama not reachable at http://localhost:11434" -ForegroundColor Red
    exit 1
}

# Phase 2: Workflow E2E
Write-Host "`n=== PHASE 2: WORKFLOW E2E ===" -ForegroundColor Cyan
python tools/run_live_workflow_simple.py --workflow blog_workflow --topic "FastAPI Tutorial" --output-dir ".live_e2e_data/$TS/outputs" --report-dir "reports/live_e2e_full/$TS"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Phase 2 failed" -ForegroundColor Red
    exit 1
}
Write-Host "[PASS] Phase 2 completed" -ForegroundColor Green

# Phase 3: Web + MCP E2E
Write-Host "`n=== PHASE 3: WEB + MCP E2E ===" -ForegroundColor Cyan
python tools/run_live_web_mcp_e2e.py --report-dir "reports/live_e2e_full/$TS"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Phase 3 failed" -ForegroundColor Red
    exit 1
}
Write-Host "[PASS] Phase 3 completed" -ForegroundColor Green

Write-Host "`n[SUCCESS] All phases passed" -ForegroundColor Green
Write-Host "Reports: reports/live_e2e_full/$TS/" -ForegroundColor Gray
