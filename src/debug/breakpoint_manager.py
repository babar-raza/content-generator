"""Breakpoint Manager - CRUD operations and condition evaluation.

This module implements the BreakpointManager (VIS-002), which:
- CRUD operations for breakpoints
- Breakpoint matching by agent/type
- Condition evaluation using safe AST parser
- SQLite persistence for durability

Thread Safety:
    All methods are thread-safe for concurrent access.

Author: Migration Implementation Agent
Created: 2025-12-18
Taskcard: VIS-002
"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from .condition_parser import ConditionEvaluationError, ConditionParser
from .models import Breakpoint, BreakpointType

logger = logging.getLogger(__name__)


class BreakpointManager:
    """Manager for breakpoint CRUD and evaluation.

    The BreakpointManager provides:
    - Create, read, update, delete breakpoints
    - Persistent storage in SQLite
    - Condition evaluation using safe AST parser
    - Breakpoint matching for agent execution

    Example:
        >>> manager = BreakpointManager("debug.db")
        >>> bp = Breakpoint(
        ...     job_id="job-123",
        ...     type=BreakpointType.AGENT_BEFORE,
        ...     target="topic_identification",
        ...     condition="inputs.topic == 'Python'"
        ... )
        >>> bp_id = manager.create(bp)
        >>> # Later...
        >>> context = {"inputs": {"topic": "Python"}}
        >>> matched = manager.check("job-123", "topic_identification", "agent_before", context)
        >>> assert matched is not None

    Thread Safety:
        All public methods are thread-safe.
    """

    def __init__(self, db_path: str | Path = "debug_breakpoints.db"):
        """Initialize breakpoint manager.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = Path(db_path)
        self._condition_parser = ConditionParser()
        self._lock = threading.RLock()
        self._init_database()

        logger.info(f"BreakpointManager initialized (db={self._db_path})")

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS breakpoints (
                        id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        target TEXT NOT NULL,
                        condition TEXT,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        hit_count INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_job_id ON breakpoints(job_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_enabled ON breakpoints(enabled)"
                )
                conn.commit()
                logger.debug("Database schema initialized")
            finally:
                conn.close()

    def create(self, breakpoint: Breakpoint) -> str:
        """Create a new breakpoint.

        Args:
            breakpoint: Breakpoint to create

        Returns:
            Breakpoint ID

        Raises:
            ValueError: If condition is invalid

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> manager = BreakpointManager()
            >>> bp = Breakpoint(
            ...     job_id="job-123",
            ...     type=BreakpointType.AGENT_BEFORE,
            ...     target="*",
            ... )
            >>> bp_id = manager.create(bp)
            >>> assert bp_id == bp.id
        """
        # Validate condition if provided
        if breakpoint.condition:
            try:
                self._condition_parser.parse(breakpoint.condition)
            except ConditionEvaluationError as e:
                raise ValueError(f"Invalid condition: {e}")

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    INSERT INTO breakpoints (id, job_id, type, target, condition, enabled, hit_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        breakpoint.id,
                        breakpoint.job_id,
                        breakpoint.type,  # Already a string due to use_enum_values=True
                        breakpoint.target,
                        breakpoint.condition,
                        1 if breakpoint.enabled else 0,
                        breakpoint.hit_count,
                        breakpoint.created_at.isoformat(),
                    ),
                )
                conn.commit()
                logger.info(
                    f"Created breakpoint {breakpoint.id} for job {breakpoint.job_id} "
                    f"({breakpoint.type} @ {breakpoint.target})"
                )
            finally:
                conn.close()

        return breakpoint.id

    def delete(self, breakpoint_id: str) -> bool:
        """Delete a breakpoint.

        Args:
            breakpoint_id: Breakpoint ID to delete

        Returns:
            True if deleted, False if not found

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> manager = BreakpointManager()
            >>> bp = Breakpoint(job_id="job-123", type=BreakpointType.AGENT_BEFORE, target="*")
            >>> bp_id = manager.create(bp)
            >>> assert manager.delete(bp_id) is True
            >>> assert manager.delete(bp_id) is False
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "DELETE FROM breakpoints WHERE id = ?", (breakpoint_id,)
                )
                conn.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted breakpoint {breakpoint_id}")
                else:
                    logger.warning(f"Breakpoint {breakpoint_id} not found for deletion")
                return deleted
            finally:
                conn.close()

    def enable(self, breakpoint_id: str) -> None:
        """Enable a breakpoint.

        Args:
            breakpoint_id: Breakpoint ID to enable

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> manager = BreakpointManager()
            >>> bp = Breakpoint(job_id="job-123", type=BreakpointType.AGENT_BEFORE, target="*")
            >>> bp_id = manager.create(bp)
            >>> manager.disable(bp_id)
            >>> manager.enable(bp_id)
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    "UPDATE breakpoints SET enabled = 1 WHERE id = ?", (breakpoint_id,)
                )
                conn.commit()
                logger.info(f"Enabled breakpoint {breakpoint_id}")
            finally:
                conn.close()

    def disable(self, breakpoint_id: str) -> None:
        """Disable a breakpoint.

        Args:
            breakpoint_id: Breakpoint ID to disable

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> manager = BreakpointManager()
            >>> bp = Breakpoint(job_id="job-123", type=BreakpointType.AGENT_BEFORE, target="*")
            >>> bp_id = manager.create(bp)
            >>> manager.disable(bp_id)
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    "UPDATE breakpoints SET enabled = 0 WHERE id = ?", (breakpoint_id,)
                )
                conn.commit()
                logger.info(f"Disabled breakpoint {breakpoint_id}")
            finally:
                conn.close()

    def list(self, job_id: str) -> list[Breakpoint]:
        """List all breakpoints for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of breakpoints

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> manager = BreakpointManager()
            >>> bp = Breakpoint(job_id="job-123", type=BreakpointType.AGENT_BEFORE, target="*")
            >>> manager.create(bp)
            >>> breakpoints = manager.list("job-123")
            >>> assert len(breakpoints) == 1
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT id, job_id, type, target, condition, enabled, hit_count, created_at
                    FROM breakpoints
                    WHERE job_id = ?
                    ORDER BY created_at DESC
                    """,
                    (job_id,),
                )

                breakpoints = []
                for row in cursor.fetchall():
                    bp = Breakpoint(
                        id=row[0],
                        job_id=row[1],
                        type=row[2],  # Already a string due to use_enum_values=True
                        target=row[3],
                        condition=row[4],
                        enabled=bool(row[5]),
                        hit_count=row[6],
                        created_at=row[7],
                    )
                    breakpoints.append(bp)

                return breakpoints
            finally:
                conn.close()

    def get(self, breakpoint_id: str) -> Optional[Breakpoint]:
        """Get a breakpoint by ID.

        Args:
            breakpoint_id: Breakpoint ID

        Returns:
            Breakpoint if found, None otherwise

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT id, job_id, type, target, condition, enabled, hit_count, created_at
                    FROM breakpoints
                    WHERE id = ?
                    """,
                    (breakpoint_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                return Breakpoint(
                    id=row[0],
                    job_id=row[1],
                    type=row[2],  # Already a string due to use_enum_values=True
                    target=row[3],
                    condition=row[4],
                    enabled=bool(row[5]),
                    hit_count=row[6],
                    created_at=row[7],
                )
            finally:
                conn.close()

    def check(
        self,
        job_id: str,
        agent_name: str,
        breakpoint_type: str,
        context: dict[str, Any],
    ) -> Optional[Breakpoint]:
        """Check if any breakpoint matches the current execution point.

        Args:
            job_id: Job identifier
            agent_name: Name of agent being executed
            breakpoint_type: Type of breakpoint to check (agent_before, agent_after, etc.)
            context: Execution context for condition evaluation

        Returns:
            Matched Breakpoint if any, None otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> manager = BreakpointManager()
            >>> bp = Breakpoint(
            ...     job_id="job-123",
            ...     type=BreakpointType.AGENT_BEFORE,
            ...     target="topic_identification",
            ...     condition="inputs.topic == 'Python'"
            ... )
            >>> manager.create(bp)
            >>> context = {"inputs": {"topic": "Python"}}
            >>> matched = manager.check("job-123", "topic_identification", "agent_before", context)
            >>> assert matched is not None
        """
        try:
            bp_type_enum = BreakpointType(breakpoint_type)
        except ValueError:
            logger.warning(f"Invalid breakpoint type: {breakpoint_type}")
            return None

        # Get all enabled breakpoints for this job
        breakpoints = [bp for bp in self.list(job_id) if bp.enabled]

        for bp in breakpoints:
            # Check if breakpoint matches
            if not bp.matches(agent_name, bp_type_enum):
                continue

            # If no condition, match immediately
            if not bp.condition:
                logger.debug(
                    f"Breakpoint {bp.id} matched (no condition) "
                    f"at {agent_name} ({breakpoint_type})"
                )
                return bp

            # Evaluate condition
            try:
                if self._condition_parser.evaluate(bp.condition, context):
                    logger.debug(
                        f"Breakpoint {bp.id} matched (condition satisfied) "
                        f"at {agent_name} ({breakpoint_type})"
                    )
                    return bp
            except ConditionEvaluationError as e:
                logger.error(f"Condition evaluation failed for {bp.id}: {e}")
                continue

        return None

    def increment_hit_count(self, breakpoint_id: str) -> None:
        """Increment hit count for a breakpoint.

        Args:
            breakpoint_id: Breakpoint ID

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> manager = BreakpointManager()
            >>> bp = Breakpoint(job_id="job-123", type=BreakpointType.AGENT_BEFORE, target="*")
            >>> bp_id = manager.create(bp)
            >>> manager.increment_hit_count(bp_id)
            >>> bp = manager.get(bp_id)
            >>> assert bp.hit_count == 1
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    "UPDATE breakpoints SET hit_count = hit_count + 1 WHERE id = ?",
                    (breakpoint_id,),
                )
                conn.commit()
                logger.debug(f"Incremented hit count for breakpoint {breakpoint_id}")
            finally:
                conn.close()

    def clear_job_breakpoints(self, job_id: str) -> int:
        """Remove all breakpoints for a job.

        Args:
            job_id: Job identifier

        Returns:
            Number of breakpoints deleted

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "DELETE FROM breakpoints WHERE job_id = ?", (job_id,)
                )
                conn.commit()
                count = cursor.rowcount
                logger.info(f"Cleared {count} breakpoints for job {job_id}")
                return count
            finally:
                conn.close()


__all__ = ["BreakpointManager"]
