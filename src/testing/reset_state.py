"""Global state reset utilities for test isolation.

This module provides functions to reset all global state (singletons, caches,
module-level variables) to ensure test isolation.
"""

import gc
import sys
from typing import Any


def reset_template_registry() -> None:
    """Reset the TemplateRegistry singleton.

    NOTE: Currently disabled because resetting TemplateRegistry breaks tests
    that legitimately need templates to be loaded. The registry depends on
    the templates directory existing, and many tests rely on a properly
    initialized registry from app startup.
    """
    # Do NOT reset TemplateRegistry - it breaks legitimate template tests
    # import src.core.template_registry as template_registry_module
    # template_registry_module._registry_instance = None
    pass


def reset_config_validator() -> None:
    """Reset the ConfigValidator singleton."""
    import src.core.config_validator as config_validator_module

    # Clear the module-level singleton instance
    config_validator_module._validator_instance = None


def reset_visualization_monitor() -> None:
    """Reset the VisualOrchestrationMonitor singleton."""
    try:
        import src.visualization.monitor as monitor_module
        monitor_module._monitor_instance = None
    except (ImportError, AttributeError):
        # Module may not be imported yet or doesn't have the instance
        pass


def reset_agent_registry() -> None:
    """Reset any agent registry caches."""
    try:
        # Import the agent registry module if it exists
        if 'src.orchestration.agent_registry' in sys.modules:
            import src.orchestration.agent_registry as registry
            # If it has a clear method, call it
            if hasattr(registry, 'clear_cache'):
                registry.clear_cache()
    except (ImportError, AttributeError):
        pass


def reset_job_store() -> None:
    """Reset any job store global state."""
    try:
        if 'src.orchestration.job_store' in sys.modules:
            import src.orchestration.job_store as job_store
            if hasattr(job_store, 'reset_for_tests'):
                job_store.reset_for_tests()
    except (ImportError, AttributeError):
        pass


def reset_workflow_state() -> None:
    """Reset workflow serializer/editor global state."""
    try:
        if 'src.orchestration.workflow_serializer' in sys.modules:
            import src.orchestration.workflow_serializer as serializer
            if hasattr(serializer, '_cache'):
                serializer._cache = {}
            if hasattr(serializer, '_locks'):
                serializer._locks = {}
    except (ImportError, AttributeError):
        pass


def reset_health_monitors() -> None:
    """Reset agent health monitoring state."""
    try:
        # Reset the agent health monitor if it exists
        if 'src.orchestration.agent_health_monitor' in sys.modules:
            import src.orchestration.agent_health_monitor as health_monitor
            if hasattr(health_monitor, 'reset_for_tests'):
                health_monitor.reset_for_tests()
            elif hasattr(health_monitor, '_instance'):
                health_monitor._instance = None
    except (ImportError, AttributeError):
        pass


def clear_module_caches() -> None:
    """Clear any module-level caches."""
    # List of modules that might have caches
    cache_modules = [
        'src.core.template_registry',
        'src.core.config_validator',
        'src.visualization.monitor',
        'src.services.services',
    ]

    for module_name in cache_modules:
        if module_name in sys.modules:
            module = sys.modules[module_name]
            # Clear common cache attribute names
            for cache_attr in ['_cache', '_instances', '_registry', '_data']:
                if hasattr(module, cache_attr):
                    cache_obj = getattr(module, cache_attr)
                    if isinstance(cache_obj, dict):
                        cache_obj.clear()


def reset_psutil_mock() -> None:
    """Remove any psutil mocks from sys.modules.

    Some tests mock psutil in sys.modules, which can leak to other tests
    causing Mock/int division errors. This removes the mock and forces
    reimport of real psutil if available.
    """
    if 'psutil' in sys.modules:
        psutil_module = sys.modules['psutil']
        # Check if it's a Mock object
        if hasattr(psutil_module, '_mock_name') or type(psutil_module).__name__ in ('Mock', 'MagicMock'):
            # Remove the mock
            del sys.modules['psutil']


def reset_all() -> None:
    """Reset all global state for test isolation.

    This should be called in a pytest autouse fixture to ensure
    every test starts with clean global state.
    """
    # Reset all singleton instances
    reset_template_registry()
    reset_config_validator()
    reset_visualization_monitor()
    reset_agent_registry()
    reset_job_store()
    reset_workflow_state()
    reset_health_monitors()

    # Clear any module-level caches
    clear_module_caches()

    # Remove any leaked module mocks (like psutil)
    reset_psutil_mock()

    # Force garbage collection to clean up any remaining references
    gc.collect()


def get_isolation_info() -> dict[str, Any]:
    """Get information about current isolation state (for debugging).

    Returns:
        Dictionary with information about singleton instances and caches.
    """
    info = {}

    # Check template registry
    if 'src.core.template_registry' in sys.modules:
        import src.core.template_registry as tr
        info['template_registry_instance'] = tr._registry_instance is not None

    # Check config validator
    if 'src.core.config_validator' in sys.modules:
        import src.core.config_validator as cv
        info['config_validator_instance'] = cv._validator_instance is not None

    # Check visualization monitor
    if 'src.visualization.monitor' in sys.modules:
        import src.visualization.monitor as vm
        info['monitor_instance'] = vm._monitor_instance is not None

    return info
