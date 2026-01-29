# Acceptance Gates - Content Generator

## Overview

This document defines the tiered acceptance gates for the content-generator project. Gates are organized by environment and purpose, from quick CI validation to full production readiness.

## Gate Tiers

| Tier | Gate Name | Environment | Runner | Purpose |
|------|-----------|-------------|--------|---------|
| **Required** | Integration Tests | CI | GitHub-hosted | Component contracts |
| **Required** | E2E Mock Tests | CI | GitHub-hosted | Workflow integrity |
| **Required** | Capability (required tier) | CI | GitHub-hosted | Core functionality |
| **Staging** | prod_try_v2 (9/9 PASS) | Local/Self-hosted | Self-hosted | Real pipeline validation |
| **Production** | live-e2e full | Self-hosted | Self-hosted | Full production readiness |
| **Extended** | Capability (extended tier) | Self-hosted | Self-hosted | Advanced capabilities |

---

## Required CI Gates (Always Run)

These gates run on every push/PR on GitHub-hosted runners. All must pass before merge.

### 1. Integration Tests
**Command:**
```bash
pytest -q tests/integration -m "not (live or network)"
```

**What It Validates:**
- MCP protocol compliance
- HTTP/MCP route parity
- Configuration validation
- Database service operations
- Template registry

**Success Criteria:** All tests pass (exit code 0)

### 2. E2E Mock Tests
**Command:**
```bash
pytest -q tests/e2e_mock
```

**What It Validates:**
- Complete user journeys (mocked externals)
- Cross-component integration
- Error handling paths
- No external dependencies

**Success Criteria:** All tests pass (exit code 0)

### 3. Capability Tests (Required Tier)
**Command:**
```bash
python tools/run_capabilities.py --mode mock --tier required --outdir reports/_ci/mock --timeout_seconds 180
```

**What It Validates:**
- Core agent capabilities
- Workflow orchestration
- Template rendering
- Configuration validation

**Success Criteria:** 100% pass rate on required tier capabilities

---

## Staging Acceptance Gate (Self-Hosted)

This gate validates the pipeline with **real** Ollama and ChromaDB, not mocks. Run before tagging any release.

### prod_try_v2 (9/9 PASS)

**Command (one-liner):**
```bash
# Linux/macOS
./scripts/run_prod_try_v2.sh

# Windows
.\scripts\run_prod_try_v2.ps1
```

**Matrix:**
| Scenario | Description |
|----------|-------------|
| S1: Engine | In-process workflow execution via `run_live_workflow_v2.py` |
| S2: REST API | POST `/api/jobs` via real TestClient |
| S3: MCP | `workflow.execute` via `/mcp/request` |

**Topics (3):**
1. Python Data Structures and Type Hints
2. FastAPI Web Framework Best Practices
3. Async Programming with asyncio

**Total Validations:** 3 scenarios × 3 topics = **9 tests**

**Validation Criteria (per test):**
- Output file exists and size ≥ 2KB
- Contains VALID YAML frontmatter (`---` delimiters, NOT ` ```yaml ` fences)
- Contains ≥ 3 headings
- Retrieval evidence is NON-ZERO (proof RAG worked)

**Prerequisites:**
- Ollama running with `phi4-mini:latest` model
- ChromaDB available (HTTP or persistent mode)
- Ingested knowledge base

**Success Criteria:** **9/9 PASS** - No exceptions.

**STOP-THE-LINE:** Do not tag a release unless this gate passes.

**Evidence Output:**
```
reports/prod_try_v2/<TS>/
├── matrix_results.json
├── matrix_results.md
├── ingestion_summary.json
├── topics.txt
├── runs/
│   ├── S1/
│   ├── S2/
│   └── S3/
└── prod_try_v2_<TS>_evidence.tar.gz
```

---

## Production Acceptance Gates (Optional)

These gates validate full production readiness with all capabilities enabled.

### live-e2e Full
**Command:**
```bash
./scripts/run_live_e2e_ollama_real.sh
```

**What It Validates:**
- Full 5-phase pipeline (Preflight → Ingestion → Workflow → REST → MCP)
- Real LLM generation quality
- Real vector retrieval accuracy
- End-to-end latency

### Capability Tests (Extended Tier)
**Command:**
```bash
python tools/run_capabilities.py --mode live --tier extended --outdir reports/_ci/live --timeout_seconds 300
```

**What It Validates:**
- Advanced capabilities requiring real services
- External API integrations
- Network-dependent operations

---

## Workflow Dispatch (Self-Hosted CI)

For automated staging validation, use the GitHub Actions workflow:

**Trigger:** Manual via GitHub UI (workflow_dispatch)

**Workflow:** `.github/workflows/prod-acceptance.yml`

**Inputs:**
- `model` (default: `phi4-mini:latest`)
- `chroma_port` (default: `9100`)

**Runs On:** `[self-hosted]` only

**Outputs:** Evidence tarball uploaded as artifact

---

## Gate Execution Order

### For Regular PRs
```
1. Integration Tests (GitHub-hosted)     → MUST PASS
2. E2E Mock Tests (GitHub-hosted)        → MUST PASS
3. Capability Required (GitHub-hosted)   → MUST PASS
```

### Before Tagging Release
```
1. All Required CI gates                 → MUST PASS
2. prod_try_v2 9/9 (self-hosted)        → MUST PASS ← NEW
3. [Optional] live-e2e full             → Recommended
```

### For Major Releases
```
1. All Required CI gates                 → MUST PASS
2. prod_try_v2 9/9 (self-hosted)        → MUST PASS
3. live-e2e full (self-hosted)          → MUST PASS
4. Capability Extended (self-hosted)     → MUST PASS
```

---

## Failure Response

### Required Gate Failure
1. **STOP** - Do not merge/tag
2. Reproduce locally: `./scripts/verify_all.sh`
3. Fix the issue
4. Re-run gates
5. Push fix

### Staging Gate Failure (prod_try_v2)
1. **STOP** - Do not tag release
2. Check Ollama/ChromaDB connectivity
3. Review `reports/prod_try_v2/<TS>/` logs
4. Identify failing scenario/topic
5. Fix root cause (not just the test)
6. Re-run: `./scripts/run_prod_try_v2.sh`

### Production Gate Failure
1. Investigate thoroughly
2. Determine if environmental or code issue
3. Document findings
4. Decision: block release or proceed with caveat

---

## Environment Setup

### For Required CI (GitHub-hosted)
- Python 3.11 or 3.12
- `pip install -r requirements.txt`
- No external services needed (all mocked)

### For Staging (prod_try_v2)
```bash
# Ollama
ollama serve
ollama pull phi4-mini

# ChromaDB (pick one)
# Option A: Persistent mode (default)
# No setup needed - uses ./chroma_db

# Option B: HTTP mode via Docker
docker-compose -f docker-compose.chromadb.yml up -d
export CHROMA_HOST=localhost
export CHROMA_PORT=9100
```

### For Production (live-e2e)
Same as staging, plus:
- Ingested dataset manifest at `reports/live_e2e_ollama/*/dataset_manifest.json`
- Sufficient disk space for outputs

---

## Summary Table

| Gate | Blocks Merge? | Blocks Tag? | Runner | Time |
|------|---------------|-------------|--------|------|
| Integration Tests | ✅ Yes | ✅ Yes | GitHub | ~1min |
| E2E Mock | ✅ Yes | ✅ Yes | GitHub | ~2min |
| Capability Required | ✅ Yes | ✅ Yes | GitHub | ~3min |
| **prod_try_v2 9/9** | No | **✅ Yes** | Self-hosted | ~15min |
| live-e2e full | No | Recommended | Self-hosted | ~30min |
| Capability Extended | No | Optional | Self-hosted | ~10min |

---

**Last Updated:** 2026-01-30
**Version:** 1.0.0
**Maintained By:** Release Orchestrator Agent
