<<<<<<< Updated upstream
"""Web UI module for UCOP."""

from .app import app, set_execution_engine

__all__ = ['app', 'set_execution_engine']
=======
"""Web API package for UCOP."""

from .app import create_app, set_global_executor, get_jobs_store, get_agent_logs

__all__ = [
    'create_app',
    'set_global_executor',
    'get_jobs_store',
    'get_agent_logs',
]
>>>>>>> Stashed changes
