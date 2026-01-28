# Live E2E Full Test Runner - Real Ollama + ChromaDB
# Runs all 5 phases: Preflight, Ingestion, Workflow, REST, MCP
# STOP-THE-LINE: Exit on any phase failure

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Live E2E Test Runner - Ollama + ChromaDB" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Generate timestamp (Asia/Karachi = UTC+5)
if (-not $env:LIVE_E2E_TIMESTAMP) {
    $utcNow = [DateTime]::UtcNow
    $karachiTime = $utcNow.AddHours(5)
    $env:LIVE_E2E_TIMESTAMP = $karachiTime.ToString("yyyyMMdd-HHmm")
}

$TIMESTAMP = $env:LIVE_E2E_TIMESTAMP
$env:TEST_MODE = "live"

Write-Host "Timestamp: $TIMESTAMP" -ForegroundColor White
Write-Host "Test Mode: $($env:TEST_MODE)" -ForegroundColor White
Write-Host ""

# Preflight checks
Write-Host "=== PREFLIGHT CHECKS ===" -ForegroundColor Yellow

Write-Host "Checking Ollama..." -ForegroundColor White
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5 -ErrorAction Stop
    $models = $ollamaResponse.models | ForEach-Object { $_.name }

    if ($models -notcontains "phi4-mini:latest") {
        Write-Host "ERROR: phi4-mini:latest model not found" -ForegroundColor Red
        Write-Host "Please pull model: ollama pull phi4-mini" -ForegroundColor Red
        exit 1
    }
    Write-Host "Ollama OK (phi4-mini:latest found)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Ollama not running on http://localhost:11434" -ForegroundColor Red
    Write-Host "Please start Ollama: ollama serve" -ForegroundColor Red
    exit 1
}

Write-Host "Checking Docker..." -ForegroundColor White
try {
    docker version | Out-Null
    Write-Host "Docker OK" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker not available" -ForegroundColor Red
    Write-Host "Please install Docker and ensure it's running" -ForegroundColor Red
    exit 1
}

Write-Host "Checking Python..." -ForegroundColor White
try {
    python --version | Out-Null
    Write-Host "Python OK" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== PREFLIGHT PASSED ===" -ForegroundColor Green
Write-Host ""

# Run the main Live E2E suite
Write-Host "=== RUNNING LIVE E2E SUITE ===" -ForegroundColor Yellow
Write-Host "Running: python tools/live_e2e/run_live_e2e.py" -ForegroundColor White
Write-Host ""

try {
    python tools/live_e2e/run_live_e2e.py
    $EXIT_CODE = $LASTEXITCODE
} catch {
    $EXIT_CODE = 1
}

Write-Host ""
if ($EXIT_CODE -eq 0) {
    Write-Host "=== LIVE E2E TEST: PASS ===" -ForegroundColor Green
    Write-Host "Results: reports/live_e2e_full_v3_gates/$TIMESTAMP/" -ForegroundColor White

    # Create evidence tarball
    $TARBALL_PATH = "reports/live_e2e_prod/$TIMESTAMP/live_e2e_prod_evidence_$TIMESTAMP.tar.gz"
    New-Item -ItemType Directory -Path "reports/live_e2e_prod/$TIMESTAMP" -Force | Out-Null

    Write-Host ""
    Write-Host "=== CREATING EVIDENCE TARBALL ===" -ForegroundColor Yellow

    # Use tar (available in Windows 10+)
    try {
        tar -czf "$TARBALL_PATH" `
            "reports/live_e2e_full_v3_gates/$TIMESTAMP/" `
            "docs/live_e2e/README.md" `
            "scripts/run_live_e2e_ollama_real.sh" `
            "scripts/run_live_e2e_ollama_real.ps1" `
            2>$null

        if (Test-Path $TARBALL_PATH) {
            Write-Host "Evidence tarball: $TARBALL_PATH" -ForegroundColor Green
        }
    } catch {
        Write-Host "Warning: Could not create tarball (tar may not be available)" -ForegroundColor Yellow
    }

    exit 0
} else {
    Write-Host "=== LIVE E2E TEST: FAIL ===" -ForegroundColor Red
    Write-Host "Results: reports/live_e2e_full_v3_gates/$TIMESTAMP/" -ForegroundColor White
    Write-Host "Check logs for details" -ForegroundColor Red
    exit $EXIT_CODE
}
