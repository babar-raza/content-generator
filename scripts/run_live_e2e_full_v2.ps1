#!/usr/bin/env pwsh
# Live E2E Full V2 - Complete End-to-End Test Runner (PowerShell)
# Runs Phases 0-4 with fail-fast behavior

$ErrorActionPreference = "Stop"

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "LIVE E2E FULL V2 - END-TO-END TEST RUNNER" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

# Get timestamp
$TS = (Get-Date).ToUniversalTime().AddHours(5).ToString("yyyyMMdd-HHmm")
Write-Host "Timestamp: $TS (Asia/Karachi)" -ForegroundColor Green

$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$VENV_PYTHON = "$REPO_ROOT\.venv\Scripts\python.exe"
$REPORT_DIR = "$REPO_ROOT\reports\live_e2e_full_v2\$TS"

# Verify venv exists
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "[FAIL] Virtual environment not found: $VENV_PYTHON" -ForegroundColor Red
    exit 1
}

Write-Host "`nUsing Python: $VENV_PYTHON" -ForegroundColor Yellow

# Create report directory
New-Item -ItemType Directory -Force -Path $REPORT_DIR | Out-Null
Write-Host "[OK] Created report directory: $REPORT_DIR" -ForegroundColor Green

# PHASE 0: Preflight checks
Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "PHASE 0: PREFLIGHT CHECKS" -ForegroundColor Cyan
Write-Host "=====================================================================`n" -ForegroundColor Cyan

# Capture git state
git rev-parse HEAD | Out-File -FilePath "$REPORT_DIR\head.txt" -Encoding utf8
git status --porcelain | Out-File -FilePath "$REPORT_DIR\status.txt" -Encoding utf8
Write-Host "[OK] Git state captured" -ForegroundColor Green

# Check Ollama
Write-Host "`nChecking Ollama..."
try {
    curl.exe -s http://localhost:11434/api/tags | Out-File -FilePath "$REPORT_DIR\ollama_tags.json" -Encoding utf8
    Write-Host "[OK] Ollama reachable" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Ollama not reachable at http://localhost:11434" -ForegroundColor Red
    Write-Host "Please start Ollama and try again" -ForegroundColor Yellow
    exit 1
}

# Check phi4-mini model
Write-Host "`nChecking phi4-mini:latest model..."
$tags = Get-Content "$REPORT_DIR\ollama_tags.json" | ConvertFrom-Json
$hasModel = $tags.models | Where-Object { $_.name -eq "phi4-mini:latest" }
if ($hasModel) {
    Write-Host "[OK] phi4-mini:latest found" -ForegroundColor Green
} else {
    Write-Host "[FAIL] phi4-mini:latest not found" -ForegroundColor Red
    Write-Host "Please run: ollama pull phi4-mini" -ForegroundColor Yellow
    exit 1
}

# Check/copy dataset manifest
Write-Host "`nChecking dataset manifest..."
$existingManifest = Get-ChildItem -Path "$REPO_ROOT\reports\live_e2e_ollama" -Filter "dataset_manifest.json" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existingManifest) {
    Copy-Item $existingManifest.FullName -Destination "$REPORT_DIR\dataset_manifest.json"
    Write-Host "[OK] Dataset manifest copied from: $($existingManifest.FullName)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] No existing dataset manifest found" -ForegroundColor Red
    Write-Host "Please run: python tools/fetch_live_e2e_data.py first" -ForegroundColor Yellow
    exit 1
}

# PHASE 1: Define collections
Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "PHASE 1: DEFINE PER-RUN COLLECTIONS" -ForegroundColor Cyan
Write-Host "=====================================================================`n" -ForegroundColor Cyan

$BLOG_COLLECTION = "blog_knowledge_$($TS.Replace('-', '_'))"
$REF_COLLECTION = "api_reference_$($TS.Replace('-', '_'))"

Write-Host "Blog Collection: $BLOG_COLLECTION" -ForegroundColor Yellow
Write-Host "Reference Collection: $REF_COLLECTION" -ForegroundColor Yellow

@"
# Per-Run Collection Names

Timestamp: $TS

## Collection Names (Unique Per Run)

- **BLOG_COLLECTION**: ``$BLOG_COLLECTION``
- **REF_COLLECTION**: ``$REF_COLLECTION``
"@ | Out-File -FilePath "$REPORT_DIR\collections.md" -Encoding utf8

Write-Host "[OK] Collections defined" -ForegroundColor Green

# PHASE 2: Check counts before
Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "PHASE 2: VERIFY COUNTS BEFORE (MUST BE 0)" -ForegroundColor Cyan
Write-Host "=====================================================================`n" -ForegroundColor Cyan

& $VENV_PYTHON -c @"
import chromadb
import json
client = chromadb.PersistentClient(path='./chroma_db')
collections = {c.name: c.count() for c in client.list_collections()}
blog_count = collections.get('$BLOG_COLLECTION', 0)
ref_count = collections.get('$REF_COLLECTION', 0)
print(f'Before ingestion: {blog_count} + {ref_count} = {blog_count + ref_count} vectors')
result = {'blog': blog_count, 'ref': ref_count, 'total': blog_count + ref_count, 'status': 'PASS' if (blog_count == 0 and ref_count == 0) else 'FAIL'}
with open('$REPORT_DIR/chroma_counts_before.json'.replace('\\', '/'), 'w') as f:
    json.dump(result, f, indent=2)
exit(0 if result['status'] == 'PASS' else 1)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Collections already exist with data" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Counts before: 0 vectors (clean state)" -ForegroundColor Green

# PHASE 3: Run ingestion
Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "PHASE 3: LIVE INGESTION (8/8 DOCS + VECTORS)" -ForegroundColor Cyan
Write-Host "=====================================================================`n" -ForegroundColor Cyan

& $VENV_PYTHON tools/run_live_ingestion_v2.py `
    --manifest "$REPORT_DIR\dataset_manifest.json" `
    --blog-collection $BLOG_COLLECTION `
    --ref-collection $REF_COLLECTION `
    --output "$REPORT_DIR\ingestion_results.json" | Tee-Object -FilePath "$REPORT_DIR\ingestion_log.txt"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[FAIL] Ingestion failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n[OK] Ingestion complete" -ForegroundColor Green

# Verify counts after
Write-Host "`nVerifying counts after ingestion..."
& $VENV_PYTHON -c @"
import chromadb
import json
client = chromadb.PersistentClient(path='./chroma_db')
collections = {c.name: c.count() for c in client.list_collections()}
blog_count = collections.get('$BLOG_COLLECTION', 0)
ref_count = collections.get('$REF_COLLECTION', 0)
print(f'After ingestion: {blog_count} + {ref_count} = {blog_count + ref_count} vectors')
result = {'blog': blog_count, 'ref': ref_count, 'total': blog_count + ref_count, 'status': 'PASS' if (blog_count > 0 and ref_count > 0) else 'FAIL'}
with open('$REPORT_DIR/chroma_counts_after.json'.replace('\\', '/'), 'w') as f:
    json.dump(result, f, indent=2)
exit(0 if result['status'] == 'PASS' else 1)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Vector counts verification failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Vectors written successfully" -ForegroundColor Green

# PHASE 4: Run workflow
Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "PHASE 4: WORKFLOW E2E WITH OLLAMA" -ForegroundColor Cyan
Write-Host "=====================================================================`n" -ForegroundColor Cyan

$TOPIC = "Python Data Structures and Type Hints"
$OUTPUT_DIR = ".live_e2e_data\$TS\outputs"

Write-Host "Workflow: blog_workflow" -ForegroundColor Yellow
Write-Host "Topic: $TOPIC" -ForegroundColor Yellow
Write-Host "Output: $OUTPUT_DIR" -ForegroundColor Yellow

& $VENV_PYTHON tools/run_live_workflow_v2.py `
    --workflow-id blog_workflow `
    --topic $TOPIC `
    --output-dir $OUTPUT_DIR `
    --report-dir $REPORT_DIR `
    --blog-collection $BLOG_COLLECTION `
    --ref-collection $REF_COLLECTION

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[FAIL] Workflow execution failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n[OK] Workflow complete" -ForegroundColor Green

# Validate output
Write-Host "`nValidating output..."
& $VENV_PYTHON tools/validate_live_output.py `
    --file "$OUTPUT_DIR\generated_content.md" `
    --output "$REPORT_DIR\output_validation.json"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Output validation failed" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Output validated" -ForegroundColor Green

# FINAL SUMMARY
Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "TEST COMPLETE - ALL PHASES PASSED" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

Write-Host "`nTimestamp: $TS" -ForegroundColor Green
Write-Host "Report Directory: $REPORT_DIR" -ForegroundColor Green
Write-Host "`nPhases Completed:" -ForegroundColor Yellow
Write-Host "  [PASS] Phase 0: Preflight" -ForegroundColor Green
Write-Host "  [PASS] Phase 1: Collection Definition" -ForegroundColor Green
Write-Host "  [PASS] Phase 2: Counts Before (0 vectors)" -ForegroundColor Green
Write-Host "  [PASS] Phase 3: Ingestion (8/8 docs)" -ForegroundColor Green
Write-Host "  [PASS] Phase 4: Workflow E2E" -ForegroundColor Green
Write-Host "`nSee report directory for detailed results." -ForegroundColor Yellow

exit 0
