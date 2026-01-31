"""Unit tests for MCP web adapter."""

import pytest


def test_web_adapter_import():
    """Test that MCP web adapter module can be imported."""
    from src.mcp import web_adapter
    assert web_adapter is not None


def test_set_executor():
    """Test set_executor function."""
    from src.mcp.web_adapter import set_executor
    from unittest.mock import Mock

    mock_executor = Mock()
    set_executor(mock_executor)
    # Basic smoke test - executor can be set without errors
    assert True
