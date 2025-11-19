"""Testing Mode Helper - Single Source of Truth for TEST_MODE.

This module provides a centralized way to determine whether tests/execution
should run in mock mode (default, fast, deterministic) or live mode (opt-in,
using real services and sample data).

Usage:
    from src.utils.testing_mode import get_test_mode, is_live_mode, is_mock_mode

    if is_live_mode():
        # Use real services and samples/ data
        engine = ProductionExecutionEngine(...)
    else:
        # Use mocks and test fixtures
        engine = MockEngine(...)
"""

import os
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TestMode(Enum):
    """Test execution modes."""
    MOCK = "mock"  # Default: fast, deterministic, uses mocks
    LIVE = "live"  # Opt-in: real services, uses samples/ data


# Global cache for test mode
_test_mode: Optional[TestMode] = None


def get_test_mode() -> TestMode:
    """Get the current test mode from environment.

    Reads TEST_MODE environment variable. Defaults to MOCK if not set.
    Result is cached for performance.

    Returns:
        TestMode.MOCK or TestMode.LIVE

    Example:
        >>> os.environ['TEST_MODE'] = 'live'
        >>> get_test_mode()
        <TestMode.LIVE: 'live'>
    """
    global _test_mode

    if _test_mode is not None:
        return _test_mode

    mode_str = os.environ.get('TEST_MODE', 'mock').lower().strip()

    if mode_str == 'live':
        _test_mode = TestMode.LIVE
        logger.info("TEST_MODE=live: Using real services and samples/ data")
    else:
        _test_mode = TestMode.MOCK
        if mode_str != 'mock':
            logger.warning(f"Unknown TEST_MODE='{mode_str}', defaulting to MOCK")

    return _test_mode


def is_live_mode() -> bool:
    """Check if running in live mode (real services, samples/ data).

    Returns:
        True if TEST_MODE=live, False otherwise

    Example:
        >>> if is_live_mode():
        ...     use_real_llm_service()
    """
    return get_test_mode() == TestMode.LIVE


def is_mock_mode() -> bool:
    """Check if running in mock mode (default, fast, mocks).

    Returns:
        True if TEST_MODE=mock or unset, False otherwise

    Example:
        >>> if is_mock_mode():
        ...     use_mock_agents()
    """
    return get_test_mode() == TestMode.MOCK


def reset_test_mode():
    """Reset cached test mode (useful for testing this module).

    This forces the next call to get_test_mode() to re-read the environment.
    """
    global _test_mode
    _test_mode = None


def get_sample_data_path() -> str:
    """Get the path to sample data directory for live mode.

    Returns:
        Path to samples/ directory (relative or absolute based on cwd)

    Example:
        >>> path = get_sample_data_path()
        >>> kb_file = os.path.join(path, 'fixtures/kb/sample-kb-overview.md')
    """
    # Return relative path from project root
    return "samples"


def get_samples_kb_path() -> str:
    """Get path to KB fixtures for live mode."""
    return os.path.join(get_sample_data_path(), "fixtures", "kb")


def get_samples_docs_path() -> str:
    """Get path to docs fixtures for live mode."""
    return os.path.join(get_sample_data_path(), "fixtures", "docs")


def get_samples_templates_path() -> str:
    """Get path to templates for live mode."""
    return os.path.join(get_sample_data_path(), "templates")


def get_samples_workflows_path() -> str:
    """Get path to workflow configs for live mode."""
    return os.path.join(get_sample_data_path(), "config", "workflows")


# Public API
__all__ = [
    'TestMode',
    'get_test_mode',
    'is_live_mode',
    'is_mock_mode',
    'reset_test_mode',
    'get_sample_data_path',
    'get_samples_kb_path',
    'get_samples_docs_path',
    'get_samples_templates_path',
    'get_samples_workflows_path',
]
