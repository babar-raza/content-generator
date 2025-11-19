# Execution Engine Duplication Analysis

Date: 2025-11-19

## Scope
Investigated possible duplication across these modules:
- src/orchestration/production_execution_engine.py
- src/orchestration/job_execution_engine.py
- src/orchestration/job_execution_engine_enhanced.py
- src/core/job_execution_engine.py

## Findings
- Active job orchestrator: src/orchestration/job_execution_engine.py (class JobExecutionEngine) is instantiated by the unified executor, API dependencies, and initialization flow; it manages queueing, persistence (JobStorage), and checkpoints (CheckpointManager).
- Production agent orchestrator: src/orchestration/production_execution_engine.py (class ProductionExecutionEngine) wires real agents/services, NoMockGate, MeshExecutor. Used by CLI commands, LangGraph executor, and validation tools. Also imported as a fallback from the enhanced engine.
- Legacy/unused enhanced engine: src/orchestration/job_execution_engine_enhanced.py defines JobExecutionEngineEnhanced and AsyncJobExecutionEngine plus a JobExecution dataclass. No in-tree imports reference this module today; only self-contained factory code and a conditional import of ProductionExecutionEngine remain.
- Disconnected core engine: src/core/job_execution_engine.py is a minimal standalone runner with its own Job/JobState enums. Not exported from src/core/__init__.py and not imported anywhere else.
- Console import mismatch: src/orchestration/ops_console.py imports JobExecution/JobStatus from job_execution_engine, but those symbols are defined in job_state.py and the legacy enhanced engine, not in the active engine. Console code is likely stale until imports are corrected.

## Implications
- Multiple engines overlap in purpose, but runtime code uses only the orchestration job engine and the production engine. The enhanced and core engines are dead code and can cause confusion or drift.
- Ops console currently would fail at import/run without fixing the job status imports or pointing it to the intended legacy engine.

## Recommended Next Steps
1) Decide on the canonical job engine (likely src/orchestration/job_execution_engine.py) and either archive/remove or explicitly deprecate job_execution_engine_enhanced.py and src/core/job_execution_engine.py.
2) Fix src/orchestration/ops_console.py imports to reference the actual job state/status definitions (e.g., from job_state.py) or intentionally use the legacy enhanced engine if that is the target.
3) Align CLI/Web/tooling on a single execution-engine surface to prevent further divergence; adjust wrappers accordingly.
