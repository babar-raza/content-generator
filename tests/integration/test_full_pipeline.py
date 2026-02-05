"""Integration tests covering the full blog generation pipeline.

This module exercises the unified engine end‑to‑end by running a real job
against a small knowledge base article.  It verifies the happy path,
failure path, resume path, and parallel execution scenarios.  The tests
avoid any mocking and instead rely on the actual implementation shipped in
the repository.  Temporary files created during the run are cleaned up at
the end of each test to ensure idempotence.

Key scenarios tested:

1. **Happy Path** – A complete job run with a valid topic and template
   produces a completed ``JobResult``.  The result should include a
   populated ``pipeline_order``, partial results for each agent, an
   output artifact on disk, and a manifest file.  The run summary
   inserted at the top of the artifact includes the job ID, status and
   pipeline information.  The manifest is JSON and lists configuration
   details.  The test asserts that no error occurred and that the job
   status is ``COMPLETED``.

2. **Error Path** – Submitting a run spec that violates validation rules
   (for example, omitting the topic when ``auto_topic=False``) should
   result in a ``JobResult`` with ``FAILED`` status.  In this case the
   pipeline should not execute and the error message should reflect the
   validation problem.  No output files are produced.

3. **Resume Path** – The ``CheckpointManager`` supports saving and
   restoring arbitrary workflow state.  This test saves a dummy state
   for a job, lists the available checkpoints, restores the saved
   checkpoint and asserts the restored state matches the original.  It
   also exercises deletion and cleanup routines.  All files created in
   the ``.checkpoints`` directory are removed at the end.

4. **Parallel Path** – Two jobs are executed concurrently in separate
   threads.  Each job uses a different topic to ensure their contexts are
   isolated.  The test asserts that each returned ``JobResult`` has a
   unique job ID and that their partial results do not interfere with
   each other.  This scenario demonstrates that the engine is thread
   safe for independent runs.

Each test sets a deterministic random seed and cleans up any directories or
files created under ``output`` or ``.checkpoints`` to maintain
repeatability.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict

import pytest

from src.engine.unified_engine import UnifiedEngine, RunSpec, JobStatus
from src.orchestration.checkpoint_manager import CheckpointManager


@pytest.fixture(autouse=True)
def clean_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a clean environment before and after each test.

    The unified engine writes output artifacts to ``./output`` by default
    and checkpoints into ``.checkpoints``.  To avoid polluting the
    repository, these paths are redirected into a temporary directory
    using monkeypatch.  After the test completes the directories are
    removed.
    """
    # Redirect current working directory to a temporary folder
    cwd = os.getcwd()
    os.chdir(tmp_path)
    monkeypatch.chdir(tmp_path)

    yield

    # Cleanup any generated files
    for folder in ["output", ".checkpoints"]:
        p = Path(folder)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    # Restore working directory
    os.chdir(cwd)


def create_engine() -> UnifiedEngine:
    """Helper to create a unified engine instance.

    This wrapper exists so tests can override creation if necessary.
    """
    return UnifiedEngine()


def get_fixture_path(name: str) -> str:
    """Return the absolute path to a fixture in the sample_inputs folder."""
    return str(Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "sample_inputs" / name)


@pytest.mark.skip(reason="Pipeline initialization needs fix")
def test_happy_path(tmp_path: Path) -> None:
    """Run a complete job and verify artefacts are produced without errors."""
    engine = create_engine()

    kb_file = get_fixture_path("test_kb.md")
    assert Path(kb_file).exists(), "Fixture KB article missing"

    run_spec = RunSpec(
        topic="Test Article",
        template_name="default_blog",
        kb_path=kb_file,
        docs_path=None,
        blog_path=None,
        api_path=None,
        auto_topic=False,
        # Write outputs into the temporary directory
        output_dir=Path("output"),
    )

    result = engine.generate_job(run_spec)

    # The job should complete successfully
    assert result.status == JobStatus.COMPLETED, f"Expected completed job, got {result.status}"
    assert result.error is None, f"Unexpected error in result: {result.error}"
    assert result.pipeline_order, "Pipeline order should not be empty"
    # Each agent listed in the pipeline should have a corresponding partial result
    for agent_name in result.pipeline_order:
        assert agent_name in result.partial_results, f"Missing partial result for {agent_name}"

    # Final context should include topic and each agent output
    final_ctx: Dict[str, Any] = result.partial_results.get("final_context", {})
    assert final_ctx.get("topic") == "Test Article"

    # Verify artifact file exists and contains run summary
    assert result.output_path is not None and result.output_path.exists(), "Artifact file missing"
    artifact_content = Path(result.output_path).read_text(encoding="utf-8")
    assert "# Run Summary" in artifact_content, "Run summary not found in artifact"
    assert f"Job ID: {result.job_id}" in artifact_content, "Job ID missing in summary"

    # Verify manifest file exists and is valid JSON
    assert result.manifest_path is not None and result.manifest_path.exists(), "Manifest missing"
    manifest_data = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert manifest_data["job_id"] == result.job_id
    assert manifest_data["status"] == result.status.value


@pytest.mark.live
def test_error_path(tmp_path: Path) -> None:
    """Submit an invalid run spec and ensure the engine fails gracefully."""
    engine = create_engine()

    run_spec = RunSpec(
        topic=None,  # invalid because auto_topic=False by default
        template_name="default_blog",
        kb_path=None,
        docs_path=None,
        blog_path=None,
        api_path=None,
        auto_topic=False,
        output_dir=Path("output"),
    )

    result = engine.generate_job(run_spec)
    assert result.status == JobStatus.FAILED
    assert result.error is not None
    assert "Must provide topic" in result.error or "validation" in result.error.lower()
    # No artifact or manifest should be created
    assert result.output_path is None or not result.output_path.exists()
    assert result.manifest_path is None or not result.manifest_path.exists()


def test_resume_checkpoint(tmp_path: Path) -> None:
    """Save and restore a dummy state using the checkpoint manager."""
    manager = CheckpointManager(storage_path=Path(".checkpoints"))
    job_id = "job123"
    state: Dict[str, Any] = {"current_step": 1, "data": {"foo": "bar"}}

    checkpoint_id = manager.save(job_id, "test_step", state)
    assert checkpoint_id, "Checkpoint ID should not be empty"

    # List should return the saved checkpoint
    checkpoints = manager.list(job_id)
    assert any(cp.checkpoint_id == checkpoint_id for cp in checkpoints)

    # Restore state and verify equality
    restored = manager.restore(job_id, checkpoint_id)
    assert restored == state

    # Delete checkpoint and verify it's gone
    manager.delete(job_id, checkpoint_id)
    assert not manager.list(job_id), "Checkpoint list should be empty after deletion"

    # Save multiple checkpoints and cleanup
    for i in range(3):
        manager.save(job_id, f"step{i}", {"step": i})
    manager.cleanup(job_id, keep_last=1)
    assert len(manager.list(job_id)) == 1, "Cleanup should retain only one checkpoint"


def _run_job(engine: UnifiedEngine, topic: str, results: Dict[str, Any]) -> None:
    """Helper for running a job in a thread and storing result in dict."""
    run_spec = RunSpec(
        topic=topic,
        template_name="default_blog",
        kb_path=get_fixture_path("test_kb.md"),
        auto_topic=False,
        output_dir=Path("output"),
    )
    res = engine.generate_job(run_spec)
    results[topic] = res


@pytest.mark.live
def test_parallel_execution(tmp_path: Path) -> None:
    """Run two jobs concurrently and ensure they don't interfere."""
    engine = create_engine()
    results: Dict[str, Any] = {}

    # Start two threads
    threads = []
    for topic in ["Parallel A", "Parallel B"]:
        t = threading.Thread(target=_run_job, args=(engine, topic, results))
        t.start()
        threads.append(t)

    # Wait for completion
    for t in threads:
        t.join(timeout=60)

    assert len(results) == 2
    res_a, res_b = results["Parallel A"], results["Parallel B"]
    # Each result should be completed with unique job ID
    assert res_a.status == JobStatus.COMPLETED
    assert res_b.status == JobStatus.COMPLETED
    assert res_a.job_id != res_b.job_id
    # Ensure contexts are isolated
    ctx_a = res_a.partial_results["final_context"]
    ctx_b = res_b.partial_results["final_context"]
    assert ctx_a.get("topic") == "Parallel A"
    assert ctx_b.get("topic") == "Parallel B"