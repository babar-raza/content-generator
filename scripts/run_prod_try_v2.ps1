# Production Try Runner V2 - Official Acceptance Gate
# Runs 3 scenarios × 3 topics = 9 validations (Engine, REST, MCP)
# STOP-THE-LINE: Does not declare success unless 9/9 PASS

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Production Try Runner V2 - Acceptance Gate" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Generate timestamp (Asia/Karachi = UTC+5)
if (-not $env:PROD_TRY_TIMESTAMP) {
    $utcNow = [DateTime]::UtcNow
    $karachiTime = $utcNow.AddHours(5)
    $env:PROD_TRY_TIMESTAMP = $karachiTime.ToString("yyyyMMdd-HHmm")
}

$TIMESTAMP = $env:PROD_TRY_TIMESTAMP
$env:TEST_MODE = "live"
$env:LLM_PROVIDER = "OLLAMA"
$env:ALLOW_NETWORK = "1"

$REPORT_DIR = "reports/prod_try_v2/$TIMESTAMP"
New-Item -ItemType Directory -Path $REPORT_DIR -Force | Out-Null

Write-Host "Timestamp: $TIMESTAMP" -ForegroundColor White
Write-Host "Test Mode: $($env:TEST_MODE)" -ForegroundColor White
Write-Host "Report Dir: $REPORT_DIR" -ForegroundColor White
Write-Host ""

# =============================================================================
# PREFLIGHT CHECKS
# =============================================================================
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

Write-Host "Checking ChromaDB..." -ForegroundColor White
if ($env:CHROMA_HOST -and $env:CHROMA_PORT) {
    try {
        $chromaUrl = "http://$($env:CHROMA_HOST):$($env:CHROMA_PORT)/api/v1/heartbeat"
        Invoke-RestMethod -Uri $chromaUrl -Method Get -TimeoutSec 5 -ErrorAction Stop | Out-Null
        Write-Host "ChromaDB HTTP OK at http://$($env:CHROMA_HOST):$($env:CHROMA_PORT)" -ForegroundColor Green
    } catch {
        Write-Host "WARNING: ChromaDB not reachable at $chromaUrl" -ForegroundColor Yellow
        Write-Host "Attempting to start ChromaDB via docker-compose..." -ForegroundColor Yellow
        try {
            docker-compose -f docker-compose.chromadb.yml up -d 2>$null
            Start-Sleep -Seconds 5
            Invoke-RestMethod -Uri $chromaUrl -Method Get -TimeoutSec 5 -ErrorAction Stop | Out-Null
            Write-Host "ChromaDB started successfully" -ForegroundColor Green
        } catch {
            Write-Host "ERROR: ChromaDB still not reachable" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "ChromaDB: Using persistent client mode (./chroma_db)" -ForegroundColor White
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

# =============================================================================
# RUN PRODUCTION TRY MATRIX
# =============================================================================
Write-Host "=== RUNNING PRODUCTION TRY MATRIX V2 ===" -ForegroundColor Yellow
Write-Host "Running: python tools/prod_try_runner.py --ts $TIMESTAMP" -ForegroundColor White
Write-Host ""

try {
    python tools/prod_try_runner.py --ts $TIMESTAMP
    $EXIT_CODE = $LASTEXITCODE
} catch {
    $EXIT_CODE = 1
}

Write-Host ""

# =============================================================================
# VALIDATE 9/9 PASS
# =============================================================================
$RESULTS_JSON = "$REPORT_DIR/matrix_results.json"
if (Test-Path $RESULTS_JSON) {
    $results = Get-Content $RESULTS_JSON | ConvertFrom-Json
    $PASS_COUNT = $results.pass_count
    $TOTAL_RUNS = $results.total_runs

    if ($PASS_COUNT -ne $TOTAL_RUNS -or $TOTAL_RUNS -ne 9) {
        Write-Host "STOP-THE-LINE: Matrix is $PASS_COUNT/$TOTAL_RUNS (expected 9/9)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "ERROR: Results JSON not found at $RESULTS_JSON" -ForegroundColor Red
    exit 1
}

# =============================================================================
# CREATE EVIDENCE TARBALL
# =============================================================================
if ($EXIT_CODE -eq 0) {
    Write-Host "=== PRODUCTION TRY V2: 9/9 PASS ===" -ForegroundColor Green

    $TARBALL_PATH = "$REPORT_DIR/prod_try_v2_${TIMESTAMP}_evidence.tar.gz"

    Write-Host ""
    Write-Host "=== CREATING EVIDENCE TARBALL ===" -ForegroundColor Yellow

    # Use tar (available in Windows 10+)
    try {
        tar -czf "$TARBALL_PATH" `
            "$REPORT_DIR/" `
            "scripts/run_prod_try_v2.sh" `
            "scripts/run_prod_try_v2.ps1" `
            "tools/prod_try_runner.py" `
            2>$null

        if (Test-Path $TARBALL_PATH) {
            Write-Host "Evidence tarball: $TARBALL_PATH" -ForegroundColor Green
        }
    } catch {
        Write-Host "Warning: Could not create tarball (tar may not be available)" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "FINAL SUMMARY" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "1) TS: $TIMESTAMP" -ForegroundColor White
    Write-Host "2) Matrix: $PASS_COUNT/$TOTAL_RUNS PASS" -ForegroundColor White
    Write-Host "3) Evidence: $TARBALL_PATH" -ForegroundColor White
    Write-Host "=========================================" -ForegroundColor Cyan

    exit 0
} else {
    Write-Host "=== PRODUCTION TRY V2: FAIL ===" -ForegroundColor Red
    Write-Host "Results: $REPORT_DIR/" -ForegroundColor White
    Write-Host "Check logs for details" -ForegroundColor Red
    exit $EXIT_CODE
}
