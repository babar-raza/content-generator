# Staging Deployment Prompt - Live E2E Validation

**Purpose**: This document provides exact, copy-paste commands for deploying to staging and running Live E2E validation with Ollama + ChromaDB.

**CRITICAL**: This is a STOP-THE-LINE process. Do NOT proceed to production unless all Live E2E phases pass.

---

## Pre-Deployment Checklist

- [ ] Staging environment accessible
- [ ] Ollama installed and running (`ollama serve`)
- [ ] Docker installed and running
- [ ] Git credentials configured
- [ ] At least 5GB free disk space

---

## Phase 1: Pull and Verify

### 1.1 Navigate to Staging Directory

```bash
cd /path/to/staging/content-generator
# Or create new staging directory:
# mkdir -p ~/staging && cd ~/staging
# git clone https://github.com/babar-raza/content-generator.git
# cd content-generator
```

### 1.2 Pull Latest Main

```bash
git fetch origin
git checkout main
git pull origin main
```

### 1.3 Verify Commit

```bash
# Capture current commit
git rev-parse HEAD > /tmp/staging_deploy_commit.txt
cat /tmp/staging_deploy_commit.txt

# Verify commit is expected (compare with GitHub)
git log -1 --oneline
```

---

## Phase 2: Environment Setup

### 2.1 Create Virtual Environment

```bash
# Create clean venv
python3.12 -m venv .venv_staging

# Activate (Linux/macOS)
source .venv_staging/bin/activate

# Activate (Windows PowerShell)
# .venv_staging\Scripts\Activate.ps1
```

### 2.2 Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3 Verify Installation

```bash
python -c "import src; print('✓ Installation OK')"
python -c "import tools.live_e2e.run_live_e2e; print('✓ Live E2E module OK')"
```

---

## Phase 3: Ollama + Model Setup

### 3.1 Verify Ollama Running

```bash
# Check Ollama service
curl -s http://localhost:11434/api/tags | python -m json.tool

# Expected: JSON with "models" array
```

### 3.2 Pull Required Model

```bash
# Pull phi4-mini (if not already present)
ollama pull phi4-mini

# Verify model installed
ollama list | grep phi4-mini
```

### 3.3 Test Model

```bash
# Quick inference test
ollama run phi4-mini "What is Python?" --verbose
```

---

## Phase 4: ChromaDB Setup

### 4.1 Verify ChromaDB Directory

```bash
# Create ChromaDB persistent directory (if needed)
mkdir -p ./chroma_db

# Set permissions
chmod 755 ./chroma_db
```

### 4.2 Clean Old Test Collections (Optional)

**WARNING**: Only do this if you want to clear ALL previous test collections.

```bash
# List current collections
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma_db')
collections = client.list_collections()
for c in collections:
    print(f'{c.name}: {c.count()} vectors')
"

# Delete old test collections (if needed)
# python -c "
# import chromadb
# client = chromadb.PersistentClient(path='./chroma_db')
# for c in client.list_collections():
#     if 'blog_knowledge_' in c.name or 'api_reference_' in c.name:
#         client.delete_collection(c.name)
#         print(f'Deleted: {c.name}')
# "
```

---

## Phase 5: Run Live E2E Full Suite

### 5.1 Run Live E2E Script

**Linux/macOS**:
```bash
bash scripts/run_live_e2e_ollama_real.sh
```

**Windows PowerShell**:
```powershell
.\scripts\run_live_e2e_ollama_real.ps1
```

### 5.2 Monitor Progress

The script will run all 5 phases:
- **Phase 0**: Preflight (Ollama + ChromaDB checks)
- **Phase 1**: Ingestion (8 docs → embeddings)
- **Phase 2**: Workflow (LLM content generation)
- **Phase 3**: REST API (POST /api/jobs)
- **Phase 4**: MCP (workflow.execute)

Expected runtime: **5-15 minutes** depending on network and LLM speed.

### 5.3 Check Results

```bash
# Find latest timestamp directory
LATEST_TS=$(ls -1t reports/live_e2e_full_v3_gates/ | head -1)
echo "Latest run: $LATEST_TS"

# View aggregated results
cat reports/live_e2e_full_v3_gates/$LATEST_TS/all_results.json | python -m json.tool

# Check overall status
cat reports/live_e2e_full_v3_gates/$LATEST_TS/all_results.json | grep -A 1 '"overall_status"'
```

---

## Phase 6: Capture Evidence

### 6.1 Locate Evidence Tarball

```bash
# Find evidence tarball
LATEST_TS=$(ls -1t reports/live_e2e_full_v3_gates/ | head -1)
TARBALL_PATH="reports/live_e2e_prod/$LATEST_TS/live_e2e_prod_evidence_$LATEST_TS.tar.gz"

if [ -f "$TARBALL_PATH" ]; then
    echo "✓ Evidence tarball found: $TARBALL_PATH"
    ls -lh "$TARBALL_PATH"
else
    echo "⚠ Evidence tarball not found. Creating manually..."
    mkdir -p "reports/live_e2e_prod/$LATEST_TS"
    tar -czf "$TARBALL_PATH" \
        "reports/live_e2e_full_v3_gates/$LATEST_TS/" \
        "docs/live_e2e/README.md" \
        "scripts/run_live_e2e_ollama_real.sh" \
        "scripts/run_live_e2e_ollama_real.ps1"
fi
```

### 6.2 Extract Key Metrics

```bash
# Extract success criteria
cat reports/live_e2e_full_v3_gates/$LATEST_TS/all_results.json | python -c "
import sys, json
data = json.load(sys.stdin)
print('=== LIVE E2E RESULTS ===')
print(f\"Overall Status: {data.get('overall_status', 'UNKNOWN')}\")
print(f\"Timestamp: {data.get('timestamp', 'N/A')}\")
print(f\"\\nPhase Results:\")
for phase, result in data.get('phases', {}).items():
    status = result.get('status', 'UNKNOWN')
    print(f\"  {phase}: {status}\")
    if 'vectors' in result:
        print(f\"    Vectors: {result['vectors']}\")
    if 'output_size' in result:
        print(f\"    Output Size: {result['output_size']} bytes\")
"
```

### 6.3 Save Logs for Review

```bash
# Copy logs to accessible location
LATEST_TS=$(ls -1t reports/live_e2e_full_v3_gates/ | head -1)
cp -r reports/live_e2e_full_v3_gates/$LATEST_TS /tmp/live_e2e_staging_$LATEST_TS
echo "Logs copied to: /tmp/live_e2e_staging_$LATEST_TS"
```

---

## Phase 7: Validation Criteria

### 7.1 Required Checks

All of the following MUST be TRUE:

- [ ] **Overall Status**: `"overall_status": "PASS"`
- [ ] **Phase 0 (Preflight)**: `"status": "PASS"`
- [ ] **Phase 1 (Ingestion)**: `"status": "PASS"`, vectors > 0
- [ ] **Phase 2 (Workflow)**: `"status": "PASS"`, output_size ≥ 1536 bytes
- [ ] **Phase 3 (REST)**: `"status": "PASS"`, output ≥ 1536 bytes
- [ ] **Phase 4 (MCP)**: `"status": "PASS"`, all tests ≥ 1536 bytes

### 7.2 If Any Phase Fails

**STOP-THE-LINE**: Do NOT proceed to production.

1. Review phase-specific log:
   ```bash
   LATEST_TS=$(ls -1t reports/live_e2e_full_v3_gates/ | head -1)
   cat reports/live_e2e_full_v3_gates/$LATEST_TS/ingestion_log.txt
   cat reports/live_e2e_full_v3_gates/$LATEST_TS/workflow_log.txt
   cat reports/live_e2e_full_v3_gates/$LATEST_TS/rest_api_log.txt
   cat reports/live_e2e_full_v3_gates/$LATEST_TS/mcp_log.txt
   ```

2. Identify root cause (network, Ollama, ChromaDB, code bug)

3. Fix and re-run:
   ```bash
   bash scripts/run_live_e2e_ollama_real.sh
   ```

4. Repeat until all phases pass

---

## Phase 8: Deployment Sign-Off

### 8.1 Generate Sign-Off Report

```bash
LATEST_TS=$(ls -1t reports/live_e2e_full_v3_gates/ | head -1)
COMMIT=$(git rev-parse HEAD)

cat > /tmp/staging_signoff_$LATEST_TS.txt << EOF
=== STAGING DEPLOYMENT SIGN-OFF ===

Timestamp: $LATEST_TS
Commit: $COMMIT
Branch: $(git branch --show-current)

Live E2E Results:
$(cat reports/live_e2e_full_v3_gates/$LATEST_TS/all_results.json | python -m json.tool)

Evidence Tarball:
$(ls -lh reports/live_e2e_prod/$LATEST_TS/live_e2e_prod_evidence_$LATEST_TS.tar.gz 2>/dev/null || echo "Not found")

Sign-Off: [APPROVED/REJECTED]
Signed By: [Name]
Date: $(date)
EOF

cat /tmp/staging_signoff_$LATEST_TS.txt
```

### 8.2 Archive Evidence

```bash
# Move evidence to permanent storage
LATEST_TS=$(ls -1t reports/live_e2e_full_v3_gates/ | head -1)
mkdir -p ~/staging_evidence
cp reports/live_e2e_prod/$LATEST_TS/live_e2e_prod_evidence_$LATEST_TS.tar.gz \
   ~/staging_evidence/
cp /tmp/staging_signoff_$LATEST_TS.txt ~/staging_evidence/

echo "Evidence archived to: ~/staging_evidence/"
ls -lh ~/staging_evidence/
```

---

## Rollback Instructions

If Live E2E fails or issues are discovered post-deployment:

### Rollback Steps

```bash
# 1. Stop any running services
pkill -f uvicorn
pkill -f "python.*web.*app"

# 2. Checkout previous stable tag
git tag -l | tail -5  # List recent tags
git checkout wave5.4-green  # Replace with known good tag

# 3. Reinstall dependencies
pip install -r requirements.txt

# 4. Restart services
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 &

# 5. Verify rollback
curl -s http://localhost:8000/api/health | python -m json.tool
```

### Post-Rollback

1. Document rollback reason in incident log
2. File GitHub issue with failure details
3. Attach evidence tarball and logs
4. Schedule fix and retry

---

## Security Warnings

### ⚠️ CRITICAL: No Secrets in Logs

- **DO NOT** echo API keys, tokens, or credentials
- **DO NOT** commit evidence tarballs with secrets to git
- **DO NOT** share logs publicly without redacting sensitive data

### Safe Commands

✅ **SAFE**:
```bash
echo "ANTHROPIC_API_KEY is set: ${ANTHROPIC_API_KEY:+YES}"
```

❌ **UNSAFE**:
```bash
echo "ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY"  # NEVER DO THIS
```

### Redacting Logs

```bash
# Before sharing logs, redact secrets
sed -i 's/sk-ant-[a-zA-Z0-9-]*/REDACTED/g' /tmp/staging_logs.txt
sed -i 's/AIza[a-zA-Z0-9-]*/REDACTED/g' /tmp/staging_logs.txt
```

---

## Troubleshooting Quick Reference

| Issue | Fix |
|-------|-----|
| Ollama not running | `ollama serve` |
| Model not found | `ollama pull phi4-mini` |
| ChromaDB permission | `chmod 755 ./chroma_db` |
| Python import error | `source .venv_staging/bin/activate && pip install -r requirements.txt` |
| Timeout | Increase timeout in `run_live_e2e.py` |
| Output too small | Check LLM output in logs, verify vectors > 50 |

---

## Next Steps After Successful Validation

1. ✅ All Live E2E phases passed
2. ✅ Evidence tarball created
3. ✅ Sign-off report generated
4. → Proceed to production deployment (follow production runbook)
5. → Monitor production health for 24 hours
6. → Archive staging evidence for audit trail

---

**End of Staging Deployment Prompt**

**Maintained By**: Live E2E Productionization Agent
**Last Updated**: 2026-01-28
