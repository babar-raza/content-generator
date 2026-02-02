"""Test live executor auto-initialization in create_app.

Regression test for REST jobs 503 issue - ensures that when TEST_MODE=live and
create_app is called without an executor argument, it auto-initializes instead
of failing with 503.
"""
import pytest
import os
from unittest.mock import Mock, patch


def test_live_mode_autoinit_executor():
    """Test that create_app auto-initializes executor when TEST_MODE=live."""

    # Mock the executor factory to avoid needing real Ollama/Chroma
    mock_executor = Mock()
    mock_executor.config = Mock()
    mock_executor.event_bus = Mock()

    with patch.dict(os.environ, {"TEST_MODE": "live"}):
        with patch("tools.live_e2e.executor_factory.create_live_executor", return_value=mock_executor) as mock_factory:
            from src.web.app import create_app

            # Call create_app without executor argument
            app = create_app()

            # Verify executor factory was called (at least once - may be called multiple times in test fixtures)
            assert mock_factory.call_count >= 1, "Executor factory should have been called at least once"

            # Verify app was created successfully
            assert app is not None
            assert app.title == "UCOP API"


def test_live_mode_autoinit_failure_graceful():
    """Test that create_app handles auto-init failure gracefully."""

    with patch.dict(os.environ, {"TEST_MODE": "live"}):
        with patch("tools.live_e2e.executor_factory.create_live_executor", side_effect=Exception("Ollama not available")):
            from src.web.app import create_app

            # Should not raise exception, but create app without executor
            app = create_app()

            assert app is not None
            # Executor will be None, but app should still be created


def test_non_live_mode_no_autoinit():
    """Test that create_app does NOT auto-init when TEST_MODE != live."""

    with patch.dict(os.environ, {"TEST_MODE": "mock"}):
        with patch("tools.live_e2e.executor_factory.create_live_executor") as mock_factory:
            from src.web.app import create_app

            # Call create_app without executor argument
            app = create_app()

            # Verify executor factory was NOT called
            mock_factory.assert_not_called()

            # App should still be created
            assert app is not None


def test_explicit_executor_bypasses_autoinit():
    """Test that providing explicit executor bypasses auto-init."""

    explicit_executor = Mock()
    explicit_executor.config = Mock()
    explicit_executor.event_bus = Mock()

    with patch.dict(os.environ, {"TEST_MODE": "live"}):
        with patch("tools.live_e2e.executor_factory.create_live_executor") as mock_factory:
            from src.web.app import create_app

            # Call create_app WITH executor argument
            app = create_app(executor=explicit_executor)

            # Verify auto-init was NOT called (explicit executor provided)
            mock_factory.assert_not_called()

            assert app is not None


@pytest.mark.parametrize("test_mode", ["live", "mock", None])
def test_create_app_with_various_test_modes(test_mode):
    """Test that create_app works with various TEST_MODE values."""

    env_dict = {"TEST_MODE": test_mode} if test_mode else {}

    with patch.dict(os.environ, env_dict, clear=False):
        with patch("tools.live_e2e.executor_factory.create_live_executor", return_value=Mock(config=Mock(), event_bus=Mock())):
            from src.web.app import create_app

            # Should not crash regardless of TEST_MODE
            app = create_app()
            assert app is not None
            assert app.title == "UCOP API"
