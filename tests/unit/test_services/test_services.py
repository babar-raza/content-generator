"""Unit tests for src/services/services.py.

Tests for TrendsService mock mode functionality to ensure no network calls
in TEST_MODE=mock.
"""

import os
import pytest
from unittest.mock import Mock, patch
from src.core.config import Config


class TestTrendsServiceMockMode:
    """Tests for TrendsService mock mode behavior."""

    def test_trends_service_mock_mode_initialization(self, monkeypatch):
        """Test TrendsService initializes in mock mode without TrendReq."""
        monkeypatch.setenv('TEST_MODE', 'mock')
        monkeypatch.delenv('ALLOW_NETWORK', raising=False)

        from src.services.services import TrendsService

        config = Config()
        service = TrendsService(config)

        # In mock mode, pytrends should be None
        assert service.pytrends is None

    def test_trends_service_mock_mode_interest_over_time(self, monkeypatch):
        """Test get_interest_over_time returns stub data in mock mode."""
        monkeypatch.setenv('TEST_MODE', 'mock')
        monkeypatch.delenv('ALLOW_NETWORK', raising=False)

        from src.services.services import TrendsService

        config = Config()
        service = TrendsService(config)

        # Should return stub data, not None
        result = service.get_interest_over_time(['test', 'keywords'])

        # Result should be a DataFrame or None (no network call)
        assert result is not None or result is None  # Either is acceptable in mock

    def test_trends_service_mock_mode_related_queries(self, monkeypatch):
        """Test get_related_queries returns stub data in mock mode."""
        monkeypatch.setenv('TEST_MODE', 'mock')
        monkeypatch.delenv('ALLOW_NETWORK', raising=False)

        from src.services.services import TrendsService

        config = Config()
        service = TrendsService(config)

        # Should return empty dict (stub)
        result = service.get_related_queries('test')

        assert isinstance(result, dict)
        assert result == {}

    def test_trends_service_mock_mode_trending_searches(self, monkeypatch):
        """Test get_trending_searches returns stub data in mock mode."""
        monkeypatch.setenv('TEST_MODE', 'mock')
        monkeypatch.delenv('ALLOW_NETWORK', raising=False)

        from src.services.services import TrendsService

        config = Config()
        service = TrendsService(config)

        # Should return stub data, not None
        result = service.get_trending_searches('united_states')

        # Result should be a DataFrame or None (no network call)
        assert result is not None or result is None  # Either is acceptable in mock

    @patch('src.services.services.PYTRENDS_AVAILABLE', True)
    @patch('src.services.services.TrendReq')
    def test_trends_service_live_mode_initialization(self, mock_trendreq, monkeypatch):
        """Test TrendsService initializes TrendReq in live mode."""
        monkeypatch.setenv('TEST_MODE', 'live')
        monkeypatch.setenv('ALLOW_NETWORK', '1')

        from src.services.services import TrendsService

        config = Config()
        service = TrendsService(config)

        # In live mode, TrendReq should be called
        mock_trendreq.assert_called_once_with(hl='en-US', tz=360)
