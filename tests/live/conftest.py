"""Pytest configuration for live tests."""

import os
import pytest


def pytest_configure(config):
    """Register live marker."""
    config.addinivalue_line(
        "markers", "live: mark test as requiring live external services"
    )


def is_live_mode():
    """Check if TEST_MODE is set to 'live'."""
    return os.getenv('TEST_MODE', 'mock').lower() == 'live'


def skip_if_not_live(reason="TEST_MODE not set to 'live'"):
    """Skip test if not in live mode."""
    return pytest.mark.skipif(not is_live_mode(), reason=reason)


def skip_if_no_env(env_var, reason=None):
    """Skip test if environment variable is not set."""
    if reason is None:
        reason = f"{env_var} not set"
    return pytest.mark.skipif(not os.getenv(env_var), reason=reason)
