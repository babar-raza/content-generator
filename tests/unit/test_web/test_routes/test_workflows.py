"""Unit tests for workflows routes."""

import pytest


def test_workflows_route_import():
    """Test that workflows route module can be imported."""
    from src.web.routes import workflows
    assert workflows is not None


def test_normalize_agents():
    """Test agent normalization function."""
    from src.web.routes.workflows import normalize_agents

    # Test string agents
    agents = ["agent1", "agent2"]
    normalized = normalize_agents(agents)
    assert normalized == ["agent1", "agent2"]

    # Test dict agents
    agents = [{"agent": "agent1"}, {"id": "agent2"}]
    normalized = normalize_agents(agents)
    assert normalized == ["agent1", "agent2"]
