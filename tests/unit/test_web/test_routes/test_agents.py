"""Unit tests for agents routes."""

import pytest


def test_agents_route_import():
    """Test that agents route module can be imported."""
    from src.web.routes import agents
    assert agents is not None


def test_secret_redaction():
    """Test secret redaction function."""
    from src.web.routes.agents import redact_secrets

    # Test API key redaction
    text = "api_key=secret123"
    redacted = redact_secrets(text)
    assert "secret123" not in redacted
    assert "REDACTED" in redacted
