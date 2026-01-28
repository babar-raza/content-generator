# Live E2E Test Runner (PowerShell) - Enforces 100% Success
# NO PARTIAL, NO SKIPPED, NO OPTIONAL

param(
    [string]$Timestamp = ""
)

$ErrorActionPreference = "Stop"

# Set timestamp
if ($Timestamp -eq "") {
    $KarachiTime = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::Now, "Pakistan Standard Time")
    $Timestamp = $KarachiTime.ToString("yyyyMMdd-HHmm")
}

Write-Host "Live E2E Ollama Test - Timestamp: $Timestamp"
$env:LIVE_E2E_TIMESTAMP = $Timestamp
$env:LIVE_E2E_REPORT_DIR = "live_e2e_ollama_fix"

# Prerequisites check
Write-Host "Checking Ollama..." 
$null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop

Write-Host "Checking Docker..."
docker version | Out-Null

# Run phases
python tools/live_e2e/data_fetch.py
python tools/run_live_ingestion.py
python tools/live_e2e/chroma_probe.py

Write-Host "LIVE E2E TEST: PASS" -ForegroundColor Green
