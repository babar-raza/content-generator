# Dual-Mode Testing Review

Date: 2025-11-19
Author: Codex

## Context
User asked whether tests should rely on mock data vs. real data and if a dual-mode (mock + live) approach is feasible for this project.

## Current State Observations
- Output artifacts in `output/` show pipeline runs emitting `mock_output` for each node, indicating tests currently use mocked agents/pipeline nodes.
- Manifests remain in `status: "running"` with `duration: 0.0`, suggesting incomplete handling of end-to-end success/failure and no persisted live results.
- Sample inputs exist under `tests/fixtures`, but no curated real-output fixtures or live verification steps are defined.
- Production execution uses `ProductionExecutionEngine` and real services (LLM, DB, embeddings), but test harnesses default to synthetic data.

## Recommendation Summary
1. Support an explicit dual-mode test strategy:
   - **Mock mode** (default): deterministic, fast tests using mock agents/services, ideal for CI.
   - **Live mode** (opt-in): small curated scenarios that exercise real agents/services for end-to-end validation.
2. Introduce a configuration switch (env var or CLI flag) to select mode; propagate it through workflow compiler/job engine so pipelines instantiate either mocks or real agents.
3. Encapsulate fixtures:
   - Keep current mock fixtures; ensure outputs are fully deterministic and Windows-safe (open files with `encoding="utf-8"`).
   - Create minimal “live” fixture inputs under `samples/` backed by real content snippets.
4. For live mode, add pytest markers (e.g., `@pytest.mark.live`) and document prerequisites (LLM keys, DB endpoints). CI can skip by default; manual/nightly runs can enable it.
5. Add soft assertions for live outputs (structure, presence of sections/metadata) instead of brittle text matches.
6. Ensure both modes write proper manifest statuses and handle Unicode to avoid `charmap` errors on Windows.

## Next Steps
- Decide on naming (`TEST_MODE=mock|live`) and whether the flag lives in config files or CLI args.
- Define the minimal live dataset (likely reusing curated content from `/content/` as described in the seeding task).
- Update tests to respect the mode flag and add documentation under `/docs/testing/`.

