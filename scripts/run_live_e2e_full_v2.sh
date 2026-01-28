#!/usr/bin/env bash
# Live E2E Full V2 - Complete End-to-End Test Runner (Bash)
# Runs Phases 0-4 with fail-fast behavior

set -euo pipefail

echo "====================================================================="
echo "LIVE E2E FULL V2 - END-TO-END TEST RUNNER"
echo "====================================================================="

# Get timestamp (Asia/Karachi = UTC+5)
TS=$(date -u +"%Y%m%d-%H%M" -d "+5 hours" 2>/dev/null || date -u -v+5H +"%Y%m%d-%H%M" 2>/dev/null || date -u +"%Y%m%d-%H%M")
echo "Timestamp: $TS (Asia/Karachi)"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
# Windows compatibility: check for Scripts/python.exe
if [[ ! -f "$VENV_PYTHON" ]] && [[ -f "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
    VENV_PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"
fi
REPORT_DIR="$REPO_ROOT/reports/live_e2e_full_v2/$TS"

# Verify venv exists
if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "[FAIL] Virtual environment not found: $VENV_PYTHON"
    exit 1
fi

echo "Using Python: $VENV_PYTHON"

# Create report directory
mkdir -p "$REPORT_DIR"
echo "[OK] Created report directory: $REPORT_DIR"

# PHASE 0: Preflight checks
echo ""
echo "====================================================================="
echo "PHASE 0: PREFLIGHT CHECKS"
echo "====================================================================="
echo ""

# Capture git state
git rev-parse HEAD > "$REPORT_DIR/head.txt"
git status --porcelain > "$REPORT_DIR/status.txt"
echo "[OK] Git state captured"

# Check Ollama
echo ""
echo "Checking Ollama..."
if curl -s http://localhost:11434/api/tags > "$REPORT_DIR/ollama_tags.json"; then
    echo "[OK] Ollama reachable"
else
    echo "[FAIL] Ollama not reachable at http://localhost:11434"
    echo "Please start Ollama and try again"
    exit 1
fi

# Check phi4-mini model
echo ""
echo "Checking phi4-mini:latest model..."
if grep -q "phi4-mini:latest" "$REPORT_DIR/ollama_tags.json"; then
    echo "[OK] phi4-mini:latest found"
else
    echo "[FAIL] phi4-mini:latest not found"
    echo "Please run: ollama pull phi4-mini"
    exit 1
fi

# Check/copy dataset manifest
echo ""
echo "Checking dataset manifest..."
EXISTING_MANIFEST=$(find "$REPO_ROOT/reports/live_e2e_ollama" -name "dataset_manifest.json" -type f 2>/dev/null | head -1)
if [[ -n "$EXISTING_MANIFEST" ]]; then
    cp "$EXISTING_MANIFEST" "$REPORT_DIR/dataset_manifest.json"
    echo "[OK] Dataset manifest copied from: $EXISTING_MANIFEST"
else
    echo "[FAIL] No existing dataset manifest found"
    echo "Please run: python tools/fetch_live_e2e_data.py first"
    exit 1
fi

# PHASE 1: Define collections
echo ""
echo "====================================================================="
echo "PHASE 1: DEFINE PER-RUN COLLECTIONS"
echo "====================================================================="
echo ""

BLOG_COLLECTION="blog_knowledge_${TS//-/_}"
REF_COLLECTION="api_reference_${TS//-/_}"

echo "Blog Collection: $BLOG_COLLECTION"
echo "Reference Collection: $REF_COLLECTION"

cat > "$REPORT_DIR/collections.md" << EOF
# Per-Run Collection Names

Timestamp: $TS

## Collection Names (Unique Per Run)

- **BLOG_COLLECTION**: \`$BLOG_COLLECTION\`
- **REF_COLLECTION**: \`$REF_COLLECTION\`
EOF

echo "[OK] Collections defined"

# PHASE 2: Check counts before
echo ""
echo "====================================================================="
echo "PHASE 2: VERIFY COUNTS BEFORE (MUST BE 0)"
echo "====================================================================="
echo ""

"$VENV_PYTHON" -c "
import chromadb
import json
client = chromadb.PersistentClient(path='./chroma_db')
collections = {c.name: c.count() for c in client.list_collections()}
blog_count = collections.get('$BLOG_COLLECTION', 0)
ref_count = collections.get('$REF_COLLECTION', 0)
print(f'Before ingestion: {blog_count} + {ref_count} = {blog_count + ref_count} vectors')
result = {'blog': blog_count, 'ref': ref_count, 'total': blog_count + ref_count, 'status': 'PASS' if (blog_count == 0 and ref_count == 0) else 'FAIL'}
with open('$REPORT_DIR/chroma_counts_before.json', 'w') as f:
    json.dump(result, f, indent=2)
exit(0 if result['status'] == 'PASS' else 1)
"

echo "[OK] Counts before: 0 vectors (clean state)"

# PHASE 3: Run ingestion
echo ""
echo "====================================================================="
echo "PHASE 3: LIVE INGESTION (8/8 DOCS + VECTORS)"
echo "====================================================================="
echo ""

"$VENV_PYTHON" tools/run_live_ingestion_v2.py \
    --manifest "$REPORT_DIR/dataset_manifest.json" \
    --blog-collection "$BLOG_COLLECTION" \
    --ref-collection "$REF_COLLECTION" \
    --output "$REPORT_DIR/ingestion_results.json" | tee "$REPORT_DIR/ingestion_log.txt"

echo ""
echo "[OK] Ingestion complete"

# Verify counts after
echo ""
echo "Verifying counts after ingestion..."
"$VENV_PYTHON" -c "
import chromadb
import json
client = chromadb.PersistentClient(path='./chroma_db')
collections = {c.name: c.count() for c in client.list_collections()}
blog_count = collections.get('$BLOG_COLLECTION', 0)
ref_count = collections.get('$REF_COLLECTION', 0)
print(f'After ingestion: {blog_count} + {ref_count} = {blog_count + ref_count} vectors')
result = {'blog': blog_count, 'ref': ref_count, 'total': blog_count + ref_count, 'status': 'PASS' if (blog_count > 0 and ref_count > 0) else 'FAIL'}
with open('$REPORT_DIR/chroma_counts_after.json', 'w') as f:
    json.dump(result, f, indent=2)
exit(0 if result['status'] == 'PASS' else 1)
"

echo "[OK] Vectors written successfully"

# PHASE 4: Run workflow
echo ""
echo "====================================================================="
echo "PHASE 4: WORKFLOW E2E WITH OLLAMA"
echo "====================================================================="
echo ""

TOPIC="Python Data Structures and Type Hints"
OUTPUT_DIR=".live_e2e_data/$TS/outputs"

echo "Workflow: blog_workflow"
echo "Topic: $TOPIC"
echo "Output: $OUTPUT_DIR"

"$VENV_PYTHON" tools/run_live_workflow_v2.py \
    --workflow-id blog_workflow \
    --topic "$TOPIC" \
    --output-dir "$OUTPUT_DIR" \
    --report-dir "$REPORT_DIR" \
    --blog-collection "$BLOG_COLLECTION" \
    --ref-collection "$REF_COLLECTION"

echo ""
echo "[OK] Workflow complete"

# Validate output
echo ""
echo "Validating output..."
"$VENV_PYTHON" tools/validate_live_output.py \
    --file "$OUTPUT_DIR/generated_content.md" \
    --output "$REPORT_DIR/output_validation.json"

echo "[OK] Output validated"

# FINAL SUMMARY
echo ""
echo "====================================================================="
echo "TEST COMPLETE - ALL PHASES PASSED"
echo "====================================================================="

echo ""
echo "Timestamp: $TS"
echo "Report Directory: $REPORT_DIR"
echo ""
echo "Phases Completed:"
echo "  [PASS] Phase 0: Preflight"
echo "  [PASS] Phase 1: Collection Definition"
echo "  [PASS] Phase 2: Counts Before (0 vectors)"
echo "  [PASS] Phase 3: Ingestion (8/8 docs)"
echo "  [PASS] Phase 4: Workflow E2E"
echo ""
echo "See report directory for detailed results."

exit 0
