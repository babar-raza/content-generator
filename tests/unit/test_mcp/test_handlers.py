"""Unit tests for MCP handlers."""

import pytest


def test_handlers_import():
    """Test that MCP handlers module can be imported."""
    from src.mcp import handlers
    assert handlers is not None


def test_set_dependencies():
    """Test set_dependencies function."""
    from src.mcp.handlers import set_dependencies
    from unittest.mock import Mock

    mock_executor = Mock()
    set_dependencies(mock_executor)
    # Basic smoke test - dependencies can be set without errors
    assert True
