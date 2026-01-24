# verify_all.ps1
# One-command verification script for content-generator
# Runs all mock-mode gates required for release

param(
    [switch]$IncludeLive = $false
)

$ErrorActionPreference = "Stop"
$REPO_ROOT = git rev-parse --show-toplevel
$VENV_DIR = Join-Path $REPO_ROOT ".venv_verify"
$PYTHON = Join-Path $VENV_DIR "Scripts\python.exe"
$PIP = Join-Path $VENV_DIR "Scripts\pip.exe"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Content Generator - Local Verification Suite" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Create or activate virtual environment
if (-not (Test-Path $VENV_DIR)) {
    Write-Host "[SETUP] Creating verification venv..." -ForegroundColor Yellow
    python -m venv $VENV_DIR
} else {
    Write-Host "[SETUP] Using existing verification venv" -ForegroundColor Green
}

# Install dependencies
Write-Host "[SETUP] Installing dependencies..." -ForegroundColor Yellow
& $PIP install -q -r (Join-Path $REPO_ROOT "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Dependency installation failed" -ForegroundColor Red
    exit 1
}

# Initialize counters
$total_tests = 0
$failed_tests = 0
$skipped_tests = 0

# Create output directory for this run
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$output_dir = Join-Path $REPO_ROOT "reports\_local_verify\$timestamp"
New-Item -ItemType Directory -Force -Path $output_dir | Out-Null

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "GATE 1: Unit Tests" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

& $PYTHON -m pytest -q tests/unit 2>&1 | Tee-Object (Join-Path $output_dir "unit.txt")
$unit_exit = $LASTEXITCODE
if ($unit_exit -eq 0) {
    Write-Host "[PASS] Unit tests" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Unit tests" -ForegroundColor Red
    $failed_tests++
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "GATE 2: Integration Tests" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

& $PYTHON -m pytest -q tests/integration 2>&1 | Tee-Object (Join-Path $output_dir "integration.txt")
$integration_exit = $LASTEXITCODE
if ($integration_exit -eq 0) {
    Write-Host "[PASS] Integration tests" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Integration tests" -ForegroundColor Red
    $failed_tests++
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "GATE 3: E2E Mock Tests" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

& $PYTHON -m pytest -q tests/e2e_mock 2>&1 | Tee-Object (Join-Path $output_dir "e2e_mock.txt")
$e2e_exit = $LASTEXITCODE
if ($e2e_exit -eq 0) {
    Write-Host "[PASS] E2E mock tests" -ForegroundColor Green
} else {
    Write-Host "[FAIL] E2E mock tests" -ForegroundColor Red
    $failed_tests++
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "GATE 4: Capability Mock Tests" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$cap_mock_dir = Join-Path $output_dir "capability_mock"
& $PYTHON (Join-Path $REPO_ROOT "tools\run_capabilities.py") --mode mock --outdir $cap_mock_dir --timeout_seconds 180 2>&1 | Tee-Object (Join-Path $output_dir "capability_mock.txt")
$cap_mock_exit = $LASTEXITCODE
if ($cap_mock_exit -eq 0) {
    Write-Host "[PASS] Capability mock tests" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Capability mock tests" -ForegroundColor Red
    $failed_tests++
}

# Optional: Live mode
if ($IncludeLive) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "OPTIONAL: Live Tests" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan

    # Check for required environment variables
    $live_ready = $true
    $required_vars = @("ANTHROPIC_API_KEY", "GOOGLE_API_KEY")
    foreach ($var in $required_vars) {
        if (-not (Test-Path "env:$var")) {
            Write-Host "[SKIP] Missing environment variable: $var" -ForegroundColor Yellow
            $live_ready = $false
        }
    }

    if ($live_ready) {
        Write-Host "[INFO] Running live tests..." -ForegroundColor Yellow
        & $PYTHON -m pytest -q -m live tests/live 2>&1 | Tee-Object (Join-Path $output_dir "live.txt")

        $cap_live_dir = Join-Path $output_dir "capability_live"
        & $PYTHON (Join-Path $REPO_ROOT "tools\run_capabilities.py") --mode live --outdir $cap_live_dir --timeout_seconds 180 2>&1 | Tee-Object (Join-Path $output_dir "capability_live.txt")
    } else {
        Write-Host "[SKIP] Live tests - missing required environment variables" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Unit Tests:        $(if ($unit_exit -eq 0) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($unit_exit -eq 0) { 'Green' } else { 'Red' })
Write-Host "Integration Tests: $(if ($integration_exit -eq 0) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($integration_exit -eq 0) { 'Green' } else { 'Red' })
Write-Host "E2E Mock Tests:    $(if ($e2e_exit -eq 0) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($e2e_exit -eq 0) { 'Green' } else { 'Red' })
Write-Host "Capability Mock:   $(if ($cap_mock_exit -eq 0) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($cap_mock_exit -eq 0) { 'Green' } else { 'Red' })
Write-Host ""
Write-Host "Results saved to: $output_dir" -ForegroundColor Cyan
Write-Host ""

if ($failed_tests -gt 0) {
    Write-Host "[FAIL] $failed_tests gate(s) failed - DO NOT COMMIT" -ForegroundColor Red
    exit 1
} else {
    Write-Host "[PASS] All gates passed - ready for release" -ForegroundColor Green
    exit 0
}
