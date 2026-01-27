"""
Unit tests for run_capabilities tool.

Tests capability verification logic and output directory handling.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tools.run_capabilities import (
    verify_agent_capability,
    verify_pipeline_capability,
    verify_web_capability,
    verify_mcp_capability,
)


def test_verify_mcp_capability():
    """Test MCP capability verification."""
    cap = {
        'cap_id': 'CAP-MCP-test-method',
        'mcp_method': 'test_method'
    }
    repo_root = Path('.')

    result = verify_mcp_capability(cap, repo_root)

    assert result['status'] == 'PASS'
    assert 'test_method' in result['evidence']
    assert result['error'] is None


def test_verify_pipeline_capability_success(tmp_path):
    """Test pipeline capability verification with existing config."""
    # Create temporary config file
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    config_file = config_dir / 'main.yaml'
    config_file.write_text('pipeline: test')

    cap = {
        'cap_id': 'CAP-PIPE-test-step',
        'step_name': 'test_step'
    }

    result = verify_pipeline_capability(cap, tmp_path)

    assert result['status'] == 'PASS'
    assert 'test_step' in result['evidence']


def test_verify_pipeline_capability_missing_config(tmp_path):
    """Test pipeline capability verification with missing config."""
    cap = {
        'cap_id': 'CAP-PIPE-test-step',
        'step_name': 'test_step'
    }

    result = verify_pipeline_capability(cap, tmp_path)

    assert result['status'] == 'BLOCKED'
    assert 'not found' in result['evidence']


def test_verify_agent_capability_no_declared_in():
    """Test agent capability verification with missing declared_in."""
    cap = {
        'cap_id': 'CAP-AGENT-test',
        'agent_id': 'test_agent',
        'declared_in': []
    }
    repo_root = Path('.')

    result = verify_agent_capability(cap, repo_root)

    assert result['status'] == 'BLOCKED'
    assert result['error'] == "Could not determine module path"


def test_verify_web_capability_module_path():
    """Test web capability creates correct module path."""
    cap = {
        'cap_id': 'CAP-WEB-test-route',
        'route_group': 'test_routes'
    }
    repo_root = Path('.')

    with patch('tools.run_capabilities.importlib.import_module') as mock_import:
        mock_import.side_effect = ModuleNotFoundError("Module not found")

        result = verify_web_capability(cap, repo_root)

        # Verify it tried to import the correct module
        mock_import.assert_called_once_with('src.web.routes.test_routes')
        assert result['status'] == 'BLOCKED'
