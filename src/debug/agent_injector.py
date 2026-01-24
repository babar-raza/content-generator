"""Agent Injector - Hot-inject agents into running workflows.

This module implements the AgentInjector (VIS-005), which:
- Inject agents before/after existing agents
- Inject agents at specific step indices
- Reroute workflow connections
- Remove injections
- Persistent storage in SQLite

Thread Safety:
    All methods are thread-safe for concurrent access.

Author: Migration Implementation Agent
Created: 2025-12-19
Taskcard: VIS-005
"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from .models import Injection

logger = logging.getLogger(__name__)


class AgentInjector:
    """Manager for dynamic agent injection into running workflows.

    The AgentInjector provides hot-injection capabilities:
    - Inject agents before/after existing agents
    - Inject agents at specific step indices
    - Modify workflow routing on-the-fly
    - Remove injections
    - Persistent storage for injection records

    Example:
        >>> injector = AgentInjector("debug_injections.db")
        >>> injection_id = injector.inject_before(
        ...     job_id="job-123",
        ...     target_agent="section_writer",
        ...     new_agent="api_search",
        ...     config={"search_query": "Python tutorials"}
        ... )
        >>> # Workflow now executes: ... → api_search → section_writer → ...
        >>> injector.remove("job-123", injection_id)

    Thread Safety:
        All public methods are thread-safe.
    """

    def __init__(self, db_path: str | Path = "debug_injections.db"):
        """Initialize agent injector.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = Path(db_path)
        self._lock = threading.RLock()
        self._init_database()

        logger.info(f"AgentInjector initialized (db={self._db_path})")

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS injections (
                        id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        agent_name TEXT NOT NULL,
                        position TEXT NOT NULL,
                        target TEXT NOT NULL,
                        config TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_job_id ON injections(job_id)"
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reroutes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        source_agent TEXT NOT NULL,
                        original_target TEXT NOT NULL,
                        new_target TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reroute_job ON reroutes(job_id)"
                )
                conn.commit()
                logger.debug("Database schema initialized")
            finally:
                conn.close()

    def inject_before(
        self, job_id: str, target_agent: str, new_agent: str, config: dict[str, Any]
    ) -> str:
        """Inject agent before an existing agent.

        The new agent will execute immediately before the target agent.
        Output from the previous agent goes to the new agent, then to the target.

        Args:
            job_id: Job identifier
            target_agent: Name of existing agent to inject before
            new_agent: Name of agent to inject
            config: Configuration for the new agent

        Returns:
            Injection ID (for removal)

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> # Workflow: A → B → C
            >>> injection_id = injector.inject_before("job-123", "B", "D", {})
            >>> # New workflow: A → D → B → C
        """
        injection = Injection(
            job_id=job_id,
            agent_name=new_agent,
            position="before",
            target=target_agent,
            config=config,
        )

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                import json

                conn.execute(
                    """
                    INSERT INTO injections (id, job_id, agent_name, position, target, config, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        injection.id,
                        injection.job_id,
                        injection.agent_name,
                        injection.position,
                        str(injection.target),
                        json.dumps(injection.config),
                        injection.created_at.isoformat(),
                    ),
                )
                conn.commit()
                logger.info(
                    f"Injected agent {new_agent} before {target_agent} "
                    f"in job {job_id} (injection_id={injection.id})"
                )
            finally:
                conn.close()

        return injection.id

    def inject_after(
        self, job_id: str, target_agent: str, new_agent: str, config: dict[str, Any]
    ) -> str:
        """Inject agent after an existing agent.

        The new agent will execute immediately after the target agent.
        Output from the target agent goes to the new agent, then to the next agent.

        Args:
            job_id: Job identifier
            target_agent: Name of existing agent to inject after
            new_agent: Name of agent to inject
            config: Configuration for the new agent

        Returns:
            Injection ID (for removal)

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> # Workflow: A → B → C
            >>> injection_id = injector.inject_after("job-123", "B", "E", {})
            >>> # New workflow: A → B → E → C
        """
        injection = Injection(
            job_id=job_id,
            agent_name=new_agent,
            position="after",
            target=target_agent,
            config=config,
        )

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                import json

                conn.execute(
                    """
                    INSERT INTO injections (id, job_id, agent_name, position, target, config, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        injection.id,
                        injection.job_id,
                        injection.agent_name,
                        injection.position,
                        str(injection.target),
                        json.dumps(injection.config),
                        injection.created_at.isoformat(),
                    ),
                )
                conn.commit()
                logger.info(
                    f"Injected agent {new_agent} after {target_agent} "
                    f"in job {job_id} (injection_id={injection.id})"
                )
            finally:
                conn.close()

        return injection.id

    def inject_at_index(
        self, job_id: str, index: int, new_agent: str, config: dict[str, Any]
    ) -> str:
        """Inject agent at a specific step index.

        The new agent will execute at the specified step index.
        All subsequent agents are shifted forward.

        Args:
            job_id: Job identifier
            index: Step index where agent should be inserted (0-based)
            new_agent: Name of agent to inject
            config: Configuration for the new agent

        Returns:
            Injection ID (for removal)

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> # Workflow: A (step 0) → B (step 1) → C (step 2)
            >>> injection_id = injector.inject_at_index("job-123", 1, "D", {})
            >>> # New workflow: A (step 0) → D (step 1) → B (step 2) → C (step 3)
        """
        injection = Injection(
            job_id=job_id,
            agent_name=new_agent,
            position="at_index",
            target=index,
            config=config,
        )

        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                import json

                conn.execute(
                    """
                    INSERT INTO injections (id, job_id, agent_name, position, target, config, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        injection.id,
                        injection.job_id,
                        injection.agent_name,
                        injection.position,
                        str(injection.target),
                        json.dumps(injection.config),
                        injection.created_at.isoformat(),
                    ),
                )
                conn.commit()
                logger.info(
                    f"Injected agent {new_agent} at index {index} "
                    f"in job {job_id} (injection_id={injection.id})"
                )
            finally:
                conn.close()

        return injection.id

    def remove(self, job_id: str, injection_id: str) -> bool:
        """Remove an injection.

        Args:
            job_id: Job identifier
            injection_id: ID of injection to remove

        Returns:
            True if removed, False if not found

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> injection_id = injector.inject_before("job-123", "B", "D", {})
            >>> assert injector.remove("job-123", injection_id) is True
            >>> assert injector.remove("job-123", injection_id) is False
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "DELETE FROM injections WHERE id = ? AND job_id = ?",
                    (injection_id, job_id),
                )
                conn.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(
                        f"Removed injection {injection_id} from job {job_id}"
                    )
                else:
                    logger.warning(
                        f"Injection {injection_id} not found in job {job_id}"
                    )
                return deleted
            finally:
                conn.close()

    def reroute(self, job_id: str, source_agent: str, new_target: str) -> None:
        """Reroute output from source agent to new target.

        Changes the workflow graph so that the output of source_agent
        goes to new_target instead of its original next agent.

        Args:
            job_id: Job identifier
            source_agent: Name of agent whose output to reroute
            new_target: Name of new target agent

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> # Workflow: A → B → C
            >>> injector.reroute("job-123", "B", "F")
            >>> # New workflow: A → B → F (C is skipped)

        Note:
            This stores reroute information but does not modify the
            workflow directly. The execution engine must check for
            reroutes when determining the next agent.
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                from datetime import datetime

                conn.execute(
                    """
                    INSERT INTO reroutes (job_id, source_agent, original_target, new_target, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        source_agent,
                        "",  # Original target would need to be looked up from workflow
                        new_target,
                        datetime.utcnow().isoformat(),
                    ),
                )
                conn.commit()
                logger.info(
                    f"Rerouted {source_agent} → {new_target} in job {job_id}"
                )
            finally:
                conn.close()

    def list_injections(self, job_id: str) -> list[Injection]:
        """List all injections for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of Injection objects

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> injector.inject_before("job-123", "B", "D", {})
            >>> injector.inject_after("job-123", "B", "E", {})
            >>> injections = injector.list_injections("job-123")
            >>> assert len(injections) == 2
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT id, job_id, agent_name, position, target, config, created_at
                    FROM injections
                    WHERE job_id = ?
                    ORDER BY created_at ASC
                    """,
                    (job_id,),
                )

                injections = []
                for row in cursor.fetchall():
                    import json

                    # Parse target (might be str or int)
                    target_raw = row[4]
                    try:
                        target = int(target_raw)
                    except ValueError:
                        target = target_raw

                    injection = Injection(
                        id=row[0],
                        job_id=row[1],
                        agent_name=row[2],
                        position=row[3],
                        target=target,
                        config=json.loads(row[5]),
                        created_at=row[6],
                    )
                    injections.append(injection)

                return injections
            finally:
                conn.close()

    def get_reroutes(self, job_id: str) -> list[dict[str, str]]:
        """Get all reroutes for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of reroute dicts with source_agent and new_target

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> injector.reroute("job-123", "B", "F")
            >>> reroutes = injector.get_reroutes("job-123")
            >>> assert len(reroutes) == 1
            >>> assert reroutes[0]["source_agent"] == "B"
            >>> assert reroutes[0]["new_target"] == "F"
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT source_agent, new_target
                    FROM reroutes
                    WHERE job_id = ?
                    ORDER BY created_at ASC
                    """,
                    (job_id,),
                )

                reroutes = []
                for row in cursor.fetchall():
                    reroutes.append(
                        {"source_agent": row[0], "new_target": row[1]}
                    )

                return reroutes
            finally:
                conn.close()

    def clear_job_injections(self, job_id: str) -> int:
        """Remove all injections for a job.

        Args:
            job_id: Job identifier

        Returns:
            Number of injections deleted

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> injector.inject_before("job-123", "B", "D", {})
            >>> injector.inject_after("job-123", "B", "E", {})
            >>> count = injector.clear_job_injections("job-123")
            >>> assert count == 2
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "DELETE FROM injections WHERE job_id = ?", (job_id,)
                )
                conn.commit()
                count = cursor.rowcount
                logger.info(f"Cleared {count} injections for job {job_id}")
                return count
            finally:
                conn.close()

    def clear_job_reroutes(self, job_id: str) -> int:
        """Remove all reroutes for a job.

        Args:
            job_id: Job identifier

        Returns:
            Number of reroutes deleted

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> injector = AgentInjector()
            >>> injector.reroute("job-123", "B", "F")
            >>> count = injector.clear_job_reroutes("job-123")
            >>> assert count == 1
        """
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    "DELETE FROM reroutes WHERE job_id = ?", (job_id,)
                )
                conn.commit()
                count = cursor.rowcount
                logger.info(f"Cleared {count} reroutes for job {job_id}")
                return count
            finally:
                conn.close()


__all__ = ["AgentInjector"]
