"""E2E Mock Test Configuration.

Sets TEST_MODE=mock for all E2E mock tests to enable YAML fallbacks
and mock-mode behavior in routes.
"""

import pytest
import os


@pytest.fixture(autouse=True)
def set_mock_mode(monkeypatch):
    """Set TEST_MODE=mock for all E2E mock tests."""
    monkeypatch.setenv("TEST_MODE", "mock")
    yield
