"""State Snapshot Store - Capture and restore execution state.

This module implements the StateSnapshotStore (VIS-003), which:
- Captures execution state at each step
- Stores snapshots in SQLite with job_id indexing
- Provides timeline navigation
- Supports state restoration

Thread Safety:
    All methods are thread-safe for concurrent access.

Author: Migration Implementation Agent
Created: 2025-12-18
Taskcard: VIS-003
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .models import SnapshotType, StateSnapshot

logger = logging.getLogger(__name__)


class StateSnapshotStore:
    """Store for execution state snapshots.

    The StateSnapshotStore provides:
    - Capture state at execution points
    - Store in SQLite for durability
    - Timeline navigation (get snapshots 0-N)
    - State restoration for time travel debugging

    Example:
        >>> store = StateSnapshotStore("debug_snapshots.db")
        >>> snapshot = store.capture(
        ...     job_id="job-123",
        ...     agent="topic_identification",
        ...     snapshot_type="agent_start",
        ...     data={"inputs": {"topic": "Python"}, "context": {}}
        ... )
        >>> # Later...
        >>> timeline = store.get_timeline("job-123")
        >>> assert len(timeline) == 1

    Thread Safety:
        All public methods are thread-safe.
    """

    def __init__(self, db_path: str | Path = "debug_snapshots.db"):
        """Initialize snapshot store.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = Path(db_path)
        self._lock = threading.RLock()
        self._init_database()

        logger.info(f"StateSnapshotStore initialized (db={self._db_path})")

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS snapshots (
                        id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        step_index INTEGER NOT NULL,
                        agent_name TEXT NOT NULL,
                        snapshot_type TEXT NOT NULL,
                        inputs TEXT NOT NULL,
                        outputs TEXT,
                        prompt_template TEXT,
                        prompt_rendered TEXT,
                        llm_response TEXT,
                        context TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        duration_ms REAL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_job_id ON snapshots(job_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_step_index ON snapshots(job_id, step_index)"
                )
                conn.commit()
                logger.debug("Database schema initialized")
            finally:
                conn.close()

    def capture(
        self,
        job_id: str,
        agent: str,
        snapshot_type: str,
        data: dict[str, Any],
    ) -> StateSnapshot:
        """Capture execution state at a point.

        Args:
            job_id: Job identifier
            agent: Agent name
            snapshot_type: Type of snapshot (agent_start, agent_end, llm_start, llm_end)
            data: State data containing inputs, outputs, context, etc.

        Returns:
            Created StateSnapshot

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> snapshot = store.capture(
            ...     job_id="job-123",
            ...     agent="topic_identification",
            ...     snapshot_type="agent_start",
            ...     data={
            ...         "inputs": {"topic": "Python"},
            ...         "context": {},
            ...         "step_index": 0
            ...     }
            ... )
            >>> assert snapshot.agent_name == "topic_identification"
        """
        try:
            snap_type_enum = SnapshotType(snapshot_type)
        except ValueError:
            raise ValueError(f"Invalid snapshot type: {snapshot_type}")

        # Extract data fields
        step_index = data.get("step_index", 0)
        inputs = data.get("inputs", {})
        outputs = data.get("outputs")
        prompt_template = data.get("prompt_template")
        prompt_rendered = data.get("prompt_rendered")
        llm_response = data.get("llm_response")
        context = data.get("context", {})
        duration_ms = data.get("duration_ms")

        # Create snapshot
        snapshot = StateSnapshot(
            job_id=job_id,
            step_index=step_index,
            agent_name=agent,
            snapshot_type=snap_type_enum,
            inputs=inputs,
            outputs=outputs,
            prompt_template=prompt_template,
            prompt_rendered=prompt_rendered,
            llm_response=llm_response,
            context=context,
            timestamp=datetime.utcnow(),
            duration_ms=duration_ms,
        )

        # Store in database
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    INSERT INTO snapshots (
                        id, job_id, step_index, agent_name, snapshot_type,
                        inputs, outputs, prompt_template, prompt_rendered,
                        llm_response, context, timestamp, duration_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.id,
                        snapshot.job_id,
                        snapshot.step_index,
                        snapshot.agent_name,
                        snapshot.snapshot_type,  # Already a string due to use_enum_values=True
                        json.dumps(snapshot.inputs),
                        json.dumps(snapshot.outputs) if snapshot.outputs else None,
                        snapshot.prompt_template,
                        snapshot.prompt_rendered,
                        snapshot.llm_response,
                        json.dumps(snapshot.context),
                        snapshot.timestamp.isoformat(),
                        snapshot.duration_ms,
                    ),
                )
                conn.commit()
                logger.debug(
                    f"Captured snapshot {snapshot.id} for job {job_id} "
                    f"(step {step_index}, {snapshot_type} @ {agent})"
                )
            finally:
                conn.close()

        return snapshot

    def get(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Get a snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            StateSnapshot if found, None otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> snapshot = store.capture("job-123", "agent", "agent_start", {"inputs": {}})
            >>> retrieved = store.get(snapshot.id)
            >>> assert retrieved.id == snapshot.id
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT id, job_id, step_index, agent_name, snapshot_type,
                           inputs, outputs, prompt_template, prompt_rendered,
                           llm_response, context, timestamp, duration_ms
                    FROM snapshots
                    WHERE id = ?
                    """,
                    (snapshot_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                return self._row_to_snapshot(row)
            finally:
                conn.close()

    def list_for_job(self, job_id: str) -> list[StateSnapshot]:
        """List all snapshots for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of snapshots, ordered by step_index

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> store.capture("job-123", "agent1", "agent_start", {"inputs": {}, "step_index": 0})
            >>> store.capture("job-123", "agent2", "agent_start", {"inputs": {}, "step_index": 1})
            >>> snapshots = store.list_for_job("job-123")
            >>> assert len(snapshots) == 2
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT id, job_id, step_index, agent_name, snapshot_type,
                           inputs, outputs, prompt_template, prompt_rendered,
                           llm_response, context, timestamp, duration_ms
                    FROM snapshots
                    WHERE job_id = ?
                    ORDER BY step_index ASC
                    """,
                    (job_id,),
                )

                snapshots = []
                for row in cursor.fetchall():
                    snapshots.append(self._row_to_snapshot(row))

                return snapshots
            finally:
                conn.close()

    def get_at_index(self, job_id: str, index: int) -> Optional[StateSnapshot]:
        """Get snapshot at a specific step index.

        Args:
            job_id: Job identifier
            index: Step index

        Returns:
            StateSnapshot if found, None otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> store.capture("job-123", "agent", "agent_start", {"inputs": {}, "step_index": 5})
            >>> snapshot = store.get_at_index("job-123", 5)
            >>> assert snapshot.step_index == 5
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT id, job_id, step_index, agent_name, snapshot_type,
                           inputs, outputs, prompt_template, prompt_rendered,
                           llm_response, context, timestamp, duration_ms
                    FROM snapshots
                    WHERE job_id = ? AND step_index = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (job_id, index),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                return self._row_to_snapshot(row)
            finally:
                conn.close()

    def get_timeline(self, job_id: str) -> list[StateSnapshot]:
        """Get ordered timeline of snapshots for a job.

        This is an alias for list_for_job() with explicit timeline semantics.

        Args:
            job_id: Job identifier

        Returns:
            List of snapshots ordered by step_index

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> for i in range(5):
            ...     store.capture("job-123", f"agent{i}", "agent_start",
            ...                  {"inputs": {}, "step_index": i})
            >>> timeline = store.get_timeline("job-123")
            >>> assert len(timeline) == 5
            >>> assert [s.step_index for s in timeline] == [0, 1, 2, 3, 4]
        """
        return self.list_for_job(job_id)

    def restore(self, snapshot_id: str) -> dict[str, Any]:
        """Restore state from a snapshot.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            Dictionary containing state to restore

        Raises:
            ValueError: If snapshot not found

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> snapshot = store.capture(
            ...     "job-123", "agent", "agent_start",
            ...     {"inputs": {"topic": "Python"}, "context": {}, "step_index": 0}
            ... )
            >>> state = store.restore(snapshot.id)
            >>> assert state["inputs"]["topic"] == "Python"
        """
        snapshot = self.get(snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        return {
            "job_id": snapshot.job_id,
            "step_index": snapshot.step_index,
            "agent_name": snapshot.agent_name,
            "inputs": snapshot.inputs,
            "outputs": snapshot.outputs,
            "context": snapshot.context,
            "prompt_template": snapshot.prompt_template,
            "prompt_rendered": snapshot.prompt_rendered,
            "llm_response": snapshot.llm_response,
        }

    def cleanup(self, job_id: str) -> int:
        """Delete all snapshots for a job.

        Args:
            job_id: Job identifier

        Returns:
            Number of snapshots deleted

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> store.capture("job-123", "agent", "agent_start", {"inputs": {}, "step_index": 0})
            >>> count = store.cleanup("job-123")
            >>> assert count == 1
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "DELETE FROM snapshots WHERE job_id = ?", (job_id,)
                )
                conn.commit()
                count = cursor.rowcount
                logger.info(f"Cleaned up {count} snapshots for job {job_id}")
                return count
            finally:
                conn.close()

    def get_snapshot_by_step(
        self, job_id: str, step: int
    ) -> Optional[StateSnapshot]:
        """Get snapshot at a specific step index.

        Alias for get_at_index() with clearer naming.

        Args:
            job_id: Job identifier
            step: Step index

        Returns:
            StateSnapshot if found, None otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> store.capture("job-123", "agent", "agent_start", {"inputs": {}, "step_index": 5})
            >>> snapshot = store.get_snapshot_by_step("job-123", 5)
            >>> assert snapshot.step_index == 5
        """
        return self.get_at_index(job_id, step)

    def get_latest(self, job_id: str) -> Optional[StateSnapshot]:
        """Get the latest snapshot for a job.

        Returns the snapshot with the highest step_index for the given job.

        Args:
            job_id: Job identifier

        Returns:
            Latest StateSnapshot if any exist, None otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> for i in range(3):
            ...     store.capture("job-123", f"agent{i}", "agent_start",
            ...                  {"inputs": {}, "step_index": i})
            >>> latest = store.get_latest("job-123")
            >>> assert latest.step_index == 2
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT id, job_id, step_index, agent_name, snapshot_type,
                           inputs, outputs, prompt_template, prompt_rendered,
                           llm_response, context, timestamp, duration_ms
                    FROM snapshots
                    WHERE job_id = ?
                    ORDER BY step_index DESC
                    LIMIT 1
                    """,
                    (job_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                return self._row_to_snapshot(row)
            finally:
                conn.close()

    def clear_job(self, job_id: str) -> int:
        """Delete all snapshots for a job.

        Alias for cleanup() with clearer naming.

        Args:
            job_id: Job identifier

        Returns:
            Number of snapshots deleted

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> store.capture("job-123", "agent", "agent_start", {"inputs": {}, "step_index": 0})
            >>> count = store.clear_job("job-123")
            >>> assert count == 1
        """
        return self.cleanup(job_id)

    def count(self, job_id: str) -> int:
        """Count snapshots for a job.

        Args:
            job_id: Job identifier

        Returns:
            Number of snapshots for this job

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> store = StateSnapshotStore()
            >>> for i in range(5):
            ...     store.capture("job-123", f"agent{i}", "agent_start",
            ...                  {"inputs": {}, "step_index": i})
            >>> count = store.count("job-123")
            >>> assert count == 5
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM snapshots WHERE job_id = ?", (job_id,)
                )
                count = cursor.fetchone()[0]
                return count
            finally:
                conn.close()

    def _row_to_snapshot(self, row: tuple) -> StateSnapshot:
        """Convert database row to StateSnapshot.

        Args:
            row: Database row tuple

        Returns:
            StateSnapshot object
        """
        # Parse timestamp from ISO format string to datetime
        timestamp_str = row[11]
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = timestamp_str

        return StateSnapshot(
            id=row[0],
            job_id=row[1],
            step_index=row[2],
            agent_name=row[3],
            snapshot_type=SnapshotType(row[4]),
            inputs=json.loads(row[5]),
            outputs=json.loads(row[6]) if row[6] else None,
            prompt_template=row[7],
            prompt_rendered=row[8],
            llm_response=row[9],
            context=json.loads(row[10]),
            timestamp=timestamp,
            duration_ms=row[12],
        )


__all__ = ["StateSnapshotStore"]
