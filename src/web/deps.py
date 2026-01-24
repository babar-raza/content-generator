"""FastAPI dependencies for web routes.

Provides shared dependency injection functions for executor and other components.
"""

from typing import Optional
from fastapi import HTTPException

# Global executor reference (set by app initialization)
_executor = None


def set_executor(executor):
    """Set the unified executor instance.

    Args:
        executor: Unified engine executor
    """
    global _executor
    _executor = executor


def get_executor_optional() -> Optional[object]:
    """Get the executor instance (optional).

    Returns executor or None if not initialized.
    This dependency should be used for read-only list endpoints
    that can return safe fallback data when executor is unavailable.

    Returns:
        Executor instance or None
    """
    return _executor


def get_executor_required() -> object:
    """Get the executor instance (required).

    Raises 503 if executor is not initialized.
    This dependency should be used for create/execute endpoints
    that require executor to function.

    Returns:
        Executor instance

    Raises:
        HTTPException: 503 if executor not initialized
    """
    if _executor is None:
        raise HTTPException(
            status_code=503,
            detail="Executor not initialized - service unavailable"
        )
    return _executor
