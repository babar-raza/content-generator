# Live E2E Testing with Ollama + ChromaDB

This guide explains how to run end-to-end live testing of the content generator using real Ollama LLM and ChromaDB vector storage.

## Overview

Live E2E tests validate the complete content generation pipeline:
- **Phase 0**: Preflight checks (Ollama + ChromaDB availability)
- **Phase 1**: Ingestion (8 public docs → embeddings → ChromaDB)
- **Phase 2**: Workflow execution (topic → blog post generation)
- **Phase 3**: REST API validation (POST /api/jobs with output ≥ 1.5KB)
- **Phase 4**: MCP validation (workflow.execute single + batch with output ≥ 1.5KB)

**Important**: Live E2E is **opt-in only** and runs on local or self-hosted infrastructure. CI runners on GitHub Actions do NOT require Ollama/ChromaDB.

## Prerequisites

### 1. Ollama (Local LLM)
- **Install**: Download from [ollama.ai](https://ollama.ai)
- **Start service**: `ollama serve` (runs on http://localhost:11434)
- **Pull model**: `ollama pull phi4-mini`
- **Verify**: `curl http://localhost:11434/api/tags`

### 2. Docker (for ChromaDB)
- **Install**: Docker Desktop or Docker Engine
- **Verify**: `docker --version`

### 3. ChromaDB (Vector Database)
- **Mode**: Persistent client mode (local `./chroma_db` directory)
- **Port**: Default 8000 (if using HTTP mode)
- **Verify**: ChromaDB will be initialized by the test runner

### 4. Disk Space
- **Minimum**: 2GB free for models, embeddings, and outputs
- **Recommended**: 5GB for multiple test runs

### 5. Python Environment
- **Python**: 3.11 or 3.12
- **Dependencies**: `pip install -r requirements.txt`

## Environment Variables

The Live E2E runner automatically sets required environment variables. You can override:

```bash
# Test mode (REQUIRED for live tests)
export TEST_MODE=live

# Ollama configuration
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=phi4-mini:latest

# ChromaDB configuration (if using HTTP mode)
export CHROMA_HOST=localhost
export CHROMA_PORT=8000

# Per-run isolation (auto-generated if not set)
export LIVE_E2E_TIMESTAMP=20260128-1632  # YYYYMMDD-HHmm (Asia/Karachi)
```

## Data Sources

Test data is defined in [config/live_e2e_sources.yaml](../../config/live_e2e_sources.yaml):

- **KB Sources**: 5 public URLs (Python docs, FastAPI tutorial)
- **Reference Sources**: 3 public API references (asyncio, pathlib, FastAPI)
- **Total**: ~1MB extracted text, ~8 documents
- **Constraints**: Public URLs only, 500KB max HTML, 200KB max text per doc

### Dataset Hashing
- Each URL is hashed (MD5) to create a stable slug
- Extracted text and HTML are cached in `.live_e2e_data/` (gitignored)
- Re-running tests reuses cached data if hashes match

## Per-Run Isolation

Each test run uses **timestamp-based collection names** to avoid conflicts:

```python
blog_collection = f"blog_knowledge_{timestamp}"  # e.g., blog_knowledge_20260128_1632
ref_collection = f"api_reference_{timestamp}"    # e.g., api_reference_20260128_1632
```

This ensures:
- Parallel test runs don't collide
- ChromaDB state is clean for each run
- Test results are reproducible and traceable

## Running Live E2E Tests

### One-Command Execution

**Linux/macOS**:
```bash
./scripts/run_live_e2e_ollama_real.sh
```

**Windows PowerShell**:
```powershell
.\scripts\run_live_e2e_ollama_real.ps1
```

### Manual Execution

1. **Ensure Ollama is running**:
   ```bash
   ollama serve
   # In another terminal:
   ollama pull phi4-mini
   ```

2. **Run the Live E2E suite**:
   ```bash
   python tools/live_e2e/run_live_e2e.py
   ```

3. **Check results**:
   ```bash
   ls -la reports/live_e2e_full_v3_gates/<timestamp>/
   cat reports/live_e2e_full_v3_gates/<timestamp>/all_results.json
   ```

## Success Criteria

### Phase 1: Ingestion
- ✅ **8 documents ingested** (5 KB + 3 Reference)
- ✅ **Vectors > 0** in both `blog_knowledge_*` and `api_reference_*` collections
- ✅ **No errors** in ingestion log

### Phase 2: Workflow
- ✅ **Output file exists**: `.live_e2e_data/<timestamp>/outputs/generated_content.md`
- ✅ **Output size ≥ 1.5KB** (realistic for technical blog posts)
- ✅ **No LLM errors** in workflow log

### Phase 3: REST API
- ✅ **POST /api/jobs** returns 200 OK
- ✅ **Output ≥ 1.5KB** in response
- ✅ **Job status = completed**

### Phase 4: MCP
- ✅ **workflow.execute (single)** returns output ≥ 1.5KB
- ✅ **workflow.execute (batch)** processes all topics, each output ≥ 1.5KB
- ✅ **No MCP server errors**

## Troubleshooting

### Ollama Issues

**Problem**: "Ollama not reachable"
- **Fix**: Start Ollama service: `ollama serve`
- **Verify**: `curl http://localhost:11434/api/tags`

**Problem**: "phi4-mini:latest model not found"
- **Fix**: `ollama pull phi4-mini`
- **Verify**: `ollama list` should show `phi4-mini:latest`

**Problem**: "Connection timeout"
- **Fix**: Increase timeout in test runner or check firewall settings

### ChromaDB Issues

**Problem**: "ChromaDB not accessible"
- **Fix**: Ensure `./chroma_db` directory is writable
- **Fix**: If using HTTP mode, start ChromaDB server: `docker-compose up chroma`

**Problem**: "Collections already exist with data"
- **Fix**: Use a new timestamp or delete old collections:
  ```python
  import chromadb
  client = chromadb.PersistentClient(path='./chroma_db')
  client.delete_collection("blog_knowledge_20260128_1632")
  ```

### Timeout Issues

**Problem**: "Ingestion timeout"
- **Fix**: Increase timeout in `run_live_e2e.py` (default: 1200s = 20 min)
- **Cause**: Slow network, large documents, or slow embeddings

**Problem**: "Workflow timeout"
- **Fix**: Use a faster model or reduce chunk size in ingestion

### Output Size Issues

**Problem**: "Output too small: X bytes < 1536 bytes"
- **Fix**: Check LLM output in logs; model may need better prompts
- **Fix**: Verify knowledge base has sufficient context (vectors > 50)

### File Path Issues

**Problem**: "Output file not found"
- **Fix**: Check `.live_e2e_data/<timestamp>/outputs/` directory exists
- **Fix**: Review workflow log for file write errors

## CI Integration

Live E2E tests are **NOT** required for CI to pass. Instead:

1. **live-e2e-skeleton** job (runs on all PRs):
   - Verifies `tools.live_e2e.run_live_e2e` imports successfully
   - Confirms graceful skipping when Ollama/ChromaDB are unavailable
   - **Does NOT** require actual services

2. **live-e2e-selfhosted** workflow (manual dispatch):
   - Runs full Live E2E suite on self-hosted runners
   - Requires runner with Ollama + ChromaDB pre-installed
   - Uploads evidence tarball as artifact

## Directory Structure

```
content-generator/
├── config/
│   └── live_e2e_sources.yaml          # Test data sources (public URLs)
├── tools/
│   ├── live_e2e/
│   │   ├── run_live_e2e.py            # Main runner (5 phases)
│   │   ├── data_fetch.py              # Download + hash test data
│   │   ├── chroma_probe.py            # ChromaDB verification
│   │   ├── rest_phase.py              # REST API test
│   │   ├── mcp_phase.py               # MCP test
│   │   ├── executor_factory.py        # Workflow executor setup
│   │   └── output_validation.py       # Output size validation
│   ├── run_live_ingestion_v2.py       # Ingestion runner
│   ├── run_live_workflow_v2.py        # Workflow runner
│   ├── test_rest_api_phase.py         # REST phase subprocess
│   └── test_mcp_phase.py              # MCP phase subprocess
├── scripts/
│   ├── run_live_e2e_ollama_real.sh    # Linux/macOS runner
│   └── run_live_e2e_ollama_real.ps1   # Windows runner
├── reports/
│   └── live_e2e_full_v3_gates/
│       └── <timestamp>/
│           ├── all_results.json       # Aggregated results
│           ├── ingestion_log.txt      # Phase 1 log
│           ├── workflow_log.txt       # Phase 2 log
│           ├── rest_api_log.txt       # Phase 3 log
│           └── mcp_log.txt            # Phase 4 log
└── .live_e2e_data/                    # Cached data (gitignored)
    └── <timestamp>/
        ├── raw/                       # Downloaded HTML
        ├── extracted/                 # Extracted text
        └── outputs/                   # Generated content
```

## Data Persistence

- **ChromaDB**: Persistent mode stores embeddings in `./chroma_db/` (gitignored)
- **Test data**: Cached in `.live_e2e_data/` (gitignored)
- **Reports**: Saved in `reports/live_e2e_full_v3_gates/<timestamp>/` (NOT gitignored, add to tarball)

**IMPORTANT**: Do NOT commit `.live_e2e_data/` or `reports/` to git. These are excluded in `.gitignore`.

## Staging Deployment

For staging environment deployment, see [docs/release/STAGING_DEPLOY_PROMPT.md](../release/STAGING_DEPLOY_PROMPT.md).

## Related Documentation

- [Operating Manual](../OPERATING_MANUAL.md) - Main operations guide
- [CI/CD Workflows](../../.github/workflows/ci.yml) - GitHub Actions configuration
- [Test Data Sources](../../config/live_e2e_sources.yaml) - Public URLs for testing
