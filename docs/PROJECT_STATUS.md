# Project Status Overview

**Last Updated:** 2026-01-29
**Current Release:** wave5.4-green
**Repository:** [content-generator](https://github.com/babar-raza/content-generator)

---

## What is Guaranteed Green (Required Gates)

The following test suites and capability gates are **mandatory** and verified on every CI run:

### 1. Integration Test Suite
- **Status:** ✅ PASS
- **Coverage:** 813 tests passing (830 total, 14 skipped, 3 soft failures in network tests)
- **Exit Code:** 0
- **Skip Policy:** Skips are allowed for tests requiring external dependencies not available in CI
- **Location:** `tests/integration/`
- **CI Matrix:** Python 3.11 and Python 3.12

### 2. End-to-End Mock Tests
- **Status:** ✅ PASS (43/43)
- **Coverage:** Full smoke testing of MCP HTTP endpoints and Web routes
- **Location:** `tests/e2e_mock/`
- **Purpose:** Verifies core API contracts without external dependencies

### 3. Required Capability Tier
- **Status:** ✅ PASS (88/88)
- **Coverage:**
  - All agent capabilities (code, content, ingestion, search, quality)
  - All pipeline capabilities (extraction, frontmatter, assembly, writing)
  - All workflow capabilities (blog, enhancement, research, publishing)
  - All workflow engine capabilities
  - All web API capabilities (agents, batch, checkpoints, config, debug, flows, ingestion, jobs, MCP, templates, topics, validation, visualization, workflows)
  - All MCP protocol capabilities
- **Command:** `python tools/run_capabilities.py --mode mock --tier required --outdir <dir> --timeout_seconds 180`
- **Verification Time:** ~15 minutes

### 4. CI Matrix
- **Platforms:** Ubuntu Latest (GitHub-hosted)
- **Python Versions:** 3.11, 3.12
- **Latest Run:** [#21449845266](https://github.com/babar-raza/content-generator/actions/runs/21449845266)
- **Status:** ✅ SUCCESS (all jobs green)

---

## What is Optional/Extended

The following tests and capabilities are **opt-in** and do not block CI:

### 1. Extended Capability Tier
- **Count:** 6 capabilities
- **Purpose:** Advanced features requiring external services or heavy compute
- **Verification:** `python tools/run_capabilities.py --mode mock --tier extended`
- **Not required for release**

### 2. Live End-to-End Tests (Ollama + Chroma)
- **Status:** Opt-in (self-hosted runners only)
- **Purpose:** Full integration testing with real LLM and vector database
- **Requirements:**
  - Self-hosted runner with Ollama installed
  - ChromaDB running locally
  - GitHub environment: `self-hosted-ollama`
- **Trigger:** Manual workflow dispatch or push to main (if runner available)
- **Documentation:** `docs/live_e2e.md`
- **Operating Manual:** `docs/operating_manual.md`

### 3. Security Gates (Soft Gates)
- **Status:** ✅ Run but do not fail build
- **Tools:**
  - Bandit (SAST for Python)
  - pip-audit (dependency vulnerability scanning)
  - detect-secrets (credential scanning)
- **Policy:** Results are logged and reviewed, but do not block CI
- **Artifacts:** Uploaded to CI run artifacts as `security-reports`

---

## How to Verify in One Command

### Required Gates (Local)
Use the verification scripts to run all required gates locally:

**Windows:**
```powershell
.\scripts\verify_all.bat
```

**Linux/macOS:**
```bash
./scripts/verify_all.sh
```

These scripts will:
1. Run integration tests
2. Run e2e_mock tests
3. Run required capability tier tests
4. Report pass/fail status for each gate

### Live End-to-End (Ollama + Chroma)
**Self-hosted only:**

**Windows:**
```powershell
.\scripts\run_live_e2e_ollama_real.bat
```

**Linux/macOS:**
```bash
./scripts/run_live_e2e_ollama_real.sh
```

---

## Release State

### Current Release
- **Tag:** `wave5.4-green`
- **Commit:** `ecd9fa7f4a51e60ae5ec5c937264031217fa3806`
- **Release URL:** [GitHub Release](https://github.com/babar-raza/content-generator/releases/tag/wave5.4-green)
- **Date:** 2026-01-29

### What's Included
- All 88 required capabilities verified and passing
- Full integration test suite (813 tests)
- Complete e2e_mock coverage (43 tests)
- CI pipeline with Python 3.11 and 3.12 support
- Security gate infrastructure (soft gates)
- Live e2e skeleton (import verification only, full tests opt-in)

### Stability Commitment
All capabilities marked as `tier: required` in `capabilities/*.json` are **guaranteed to pass** on every push to main. The CI pipeline will fail if any required gate fails.

---

## Documentation References

- **Operating Manual:** `docs/operating_manual.md`
- **Live E2E Documentation:** `docs/live_e2e.md`
- **Capability System:** `docs/capabilities.md`
- **CI Configuration:** `.github/workflows/`
- **Rollout Plan:** `docs/security_gates_rollout.md`

---

## Maintenance Notes

### Adding New Capabilities
1. Define capability in `capabilities/<area>/<name>.json`
2. Set `tier: "required"` or `tier: "extended"`
3. Implement verification function in `tools/run_capabilities.py`
4. Test locally with `--tier required` before pushing
5. CI will automatically include new required capabilities

### Updating CI Matrix
- Edit `.github/workflows/ci.yml`
- Test changes on a feature branch first
- Ensure all jobs complete successfully before merging

### Security Gate Policy
- Security gates are **informational** and do not fail builds
- Review security reports in CI artifacts after each run
- Address critical/high vulnerabilities promptly
- See `docs/security_gates_rollout.md` for migration to hard gates

---

**For questions or issues, see the [operating manual](docs/operating_manual.md) or open a GitHub issue.**
