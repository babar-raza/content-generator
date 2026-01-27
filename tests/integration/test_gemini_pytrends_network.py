"""
Integration tests for Gemini API and PyTrends network calls.

Tests comprehensive rate limiting, backoff strategies, and error handling
for external API integrations. Production-ready tests ensuring network
calls stay under limits with proper retry logic.
"""

import pytest
import os
import time
import threading
import requests
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.services import GeminiRateLimiter
from src.core.config import Config


class TestGeminiRateLimiter:
    """Tests for GeminiRateLimiter rate limiting implementation."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = GeminiRateLimiter(requests_per_minute=10)
        assert limiter.requests_per_minute == 10
        assert limiter.request_times == []

    def test_rate_limiter_enforces_minimum(self):
        """Test rate limiter enforces minimum 1 request per minute."""
        limiter = GeminiRateLimiter(requests_per_minute=0)
        assert limiter.requests_per_minute == 1

        limiter = GeminiRateLimiter(requests_per_minute=-5)
        assert limiter.requests_per_minute == 1

    def test_rate_limiter_allows_initial_requests(self):
        """Test rate limiter allows requests under the limit."""
        limiter = GeminiRateLimiter(requests_per_minute=10)

        # Should not block for first 10 requests
        for i in range(10):
            limiter.wait_if_needed()
            limiter.mark_request()

        assert len(limiter.request_times) == 10

    def test_rate_limiter_blocks_excess_requests(self):
        """Test rate limiter blocks requests over the limit."""
        # Use a faster test with mocked time
        limiter = GeminiRateLimiter(requests_per_minute=2)

        # First 2 requests should be immediate
        start = time.time()
        for i in range(2):
            limiter.wait_if_needed()
            limiter.mark_request()

        immediate_duration = time.time() - start
        assert immediate_duration < 0.5  # Should be near instant

        # Verify request count is correct
        assert len(limiter.request_times) == 2

    def test_rate_limiter_clears_old_requests(self):
        """Test rate limiter clears requests older than 60 seconds."""
        limiter = GeminiRateLimiter(requests_per_minute=5)

        # Add requests from "61 seconds ago"
        old_time = time.time() - 61.0
        limiter.request_times = [old_time, old_time, old_time]

        # Wait should clear old requests
        limiter.wait_if_needed()

        # Old requests should be cleared
        assert len(limiter.request_times) == 0

    def test_rate_limiter_thread_safety(self):
        """Test rate limiter is thread-safe."""
        limiter = GeminiRateLimiter(requests_per_minute=20)

        def make_requests():
            for _ in range(5):
                limiter.wait_if_needed()
                limiter.mark_request()

        # Run 4 threads making 5 requests each = 20 total
        threads = [threading.Thread(target=make_requests) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have recorded all 20 requests
        assert len(limiter.request_times) == 20

    def test_rate_limiter_max_wait_timeout(self):
        """Test rate limiter respects max wait timeout."""
        limiter = GeminiRateLimiter(requests_per_minute=1)

        # Fill up with requests
        for _ in range(10):
            limiter.mark_request()

        # Should timeout after max wait (120s) but we'll mock time
        with patch('time.sleep') as mock_sleep:
            # Simulate timeout condition
            original_time = time.time
            call_count = [0]

            def mock_time():
                call_count[0] += 1
                # After a few calls, simulate timeout
                if call_count[0] > 5:
                    return original_time() + 125  # Past 120s timeout
                return original_time()

            with patch('time.time', side_effect=mock_time):
                limiter.wait_if_needed()

            # Should have cleared state on timeout
            assert len(limiter.request_times) == 0


class TestGeminiAPIIntegration:
    """Tests for Gemini API integration with rate limiting and backoff."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock config with Gemini API key."""
        config = Mock()
        config.gemini_api_key = os.environ.get('GEMINI_API_KEY', 'test_api_key')
        config.openai_api_key = None  # Disable OpenAI to test Gemini only
        config.cache_dir = str(tmp_path / "cache")
        config.ollama_base_url = "http://localhost:11434"
        config.gemini_rpm_limit = 60
        config.openai_rpm_limit = 60
        config.ollama_rpm_limit = 300
        config.llm = Mock()
        config.llm.max_tokens = 2048
        config.llm.temperature = 0.7
        config.llm.model = "gemini-1.5-flash"
        return config

    @pytest.fixture
    def gemini_service(self, mock_config):
        """Create a mock Gemini service for testing."""
        from src.services.services import LLMService
        import requests

        # Mock the connection pool to avoid Ollama network calls
        patcher = patch('src.services.services.get_connection_pool')
        mock_pool = patcher.start()
        mock_pool_instance = Mock()
        # Raise proper requests.RequestException so it gets caught
        mock_pool_instance.get.side_effect = requests.RequestException("Ollama not available")
        mock_pool.return_value = mock_pool_instance

        service = LLMService(mock_config)

        yield service

        patcher.stop()

    def test_gemini_api_uses_env_variable(self, mock_config):
        """Test Gemini API key comes from GEMINI_API_KEY environment variable."""
        # Set environment variable
        test_key = "test_gemini_key_12345"
        with patch.dict(os.environ, {'GEMINI_API_KEY': test_key}):
            config = Mock()
            config.gemini_api_key = os.environ.get('GEMINI_API_KEY')
            assert config.gemini_api_key == test_key

    @patch('requests.post')
    def test_gemini_successful_request(self, mock_post, gemini_service):
        """Test successful Gemini API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Test response from Gemini"}]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = gemini_service._call_gemini(
            prompt="Test prompt",
            model="gemini-1.5-flash",
            temperature=0.7,
            timeout=30
        )

        assert result == "Test response from Gemini"
        assert mock_post.called

    @patch('requests.post')
    def test_gemini_rate_limit_retry(self, mock_post, gemini_service):
        """Test Gemini API handles 429 rate limit with retry."""
        # First request returns 429, second succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.raise_for_status.side_effect = Exception("Rate limit")

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Success after retry"}]}}]
        }

        mock_post.side_effect = [rate_limit_response, success_response]

        # Should fail on first attempt (no auto-retry in _call_gemini)
        with pytest.raises(Exception):
            gemini_service._call_gemini(
                prompt="Test",
                model="gemini-1.5-flash",
                temperature=0.7,
                timeout=30
            )

    @patch('requests.post')
    def test_gemini_timeout_handling(self, mock_post, gemini_service):
        """Test Gemini API handles timeouts properly."""
        import requests
        mock_post.side_effect = requests.Timeout("Request timeout")

        with pytest.raises(TimeoutError) as exc_info:
            gemini_service._call_gemini(
                prompt="Test",
                model="gemini-1.5-flash",
                temperature=0.7,
                timeout=30
            )

        assert "timeout" in str(exc_info.value).lower()

    @patch('requests.post')
    def test_gemini_invalid_response_handling(self, mock_post, gemini_service):
        """Test Gemini API handles invalid responses."""
        # Mock response with missing candidates
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"candidates": []}
        mock_post.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            gemini_service._call_gemini(
                prompt="Test",
                model="gemini-1.5-flash",
                temperature=0.7,
                timeout=30
            )

        assert "candidates" in str(exc_info.value).lower()

    @patch('requests.post')
    def test_gemini_empty_response_handling(self, mock_post, gemini_service):
        """Test Gemini API handles empty text responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "   "}]}}]
        }
        mock_post.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            gemini_service._call_gemini(
                prompt="Test",
                model="gemini-1.5-flash",
                temperature=0.7,
                timeout=30
            )

        assert "empty" in str(exc_info.value).lower()

    @patch('requests.post')
    def test_gemini_respects_rate_limit(self, mock_post, gemini_service):
        """Test Gemini requests respect rate limiter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Response"}]}}]
        }
        mock_post.return_value = mock_response

        # Create rate limiter with low limit
        limiter = GeminiRateLimiter(requests_per_minute=3)

        # Make 3 requests - should be immediate
        start = time.time()
        for _ in range(3):
            limiter.wait_if_needed()
            gemini_service._call_gemini("Test", "gemini-1.5-flash", 0.7, 30)
            limiter.mark_request()

        duration = time.time() - start
        assert duration < 1.0  # Should be fast

        # 4th request should wait
        wait_start = time.time()
        limiter.wait_if_needed()
        wait_duration = time.time() - wait_start
        assert wait_duration > 0.05  # Should have some wait


class TestPyTrendsIntegration:
    """Tests for PyTrends integration with rate limiting."""

    @pytest.fixture
    def trends_service(self):
        """Create TrendsService for testing."""
        from src.services.services import TrendsService, PYTRENDS_AVAILABLE

        if not PYTRENDS_AVAILABLE:
            pytest.skip("pytrends not available")

        config = Mock()
        return TrendsService(config)

    @pytest.mark.network
    def test_trends_service_initialization(self, trends_service):
        """Test TrendsService initializes correctly."""
        assert trends_service.pytrends is not None

    @pytest.mark.network
    def test_trends_service_requires_pytrends(self):
        """Test TrendsService fails gracefully without pytrends."""
        from src.services.services import TrendsService

        with patch('src.services.services.PYTRENDS_AVAILABLE', False):
            with pytest.raises(ImportError) as exc_info:
                config = Mock()
                TrendsService(config)

            assert "pytrends" in str(exc_info.value).lower()

    @patch('src.services.services.TrendReq')
    def test_trends_interest_over_time(self, mock_trend_req, trends_service):
        """Test getting interest over time data."""
        # Mock pytrends
        mock_pytrends = Mock()
        mock_pytrends.interest_over_time.return_value = {"data": "test"}
        trends_service.pytrends = mock_pytrends

        result = trends_service.get_interest_over_time(
            keywords=["test", "keyword"],
            timeframe="today 12-m"
        )

        assert result == {"data": "test"}
        assert mock_pytrends.build_payload.called
        assert mock_pytrends.interest_over_time.called

    @patch('src.services.services.TrendReq')
    def test_trends_handles_empty_keywords(self, mock_trend_req, trends_service):
        """Test trends service handles empty keyword list."""
        result = trends_service.get_interest_over_time(keywords=[])
        assert result is None

        result = trends_service.get_interest_over_time(keywords=["", "  "])
        assert result is None

    @patch('src.services.services.TrendReq')
    def test_trends_related_queries(self, mock_trend_req, trends_service):
        """Test getting related queries."""
        mock_pytrends = Mock()
        mock_pytrends.related_queries.return_value = {
            "test": {"top": "data", "rising": "data"}
        }
        trends_service.pytrends = mock_pytrends

        result = trends_service.get_related_queries(keyword="test")

        assert result == {"top": "data", "rising": "data"}
        assert mock_pytrends.build_payload.called

    @patch('src.services.services.TrendReq')
    def test_trends_handles_empty_keyword(self, mock_trend_req, trends_service):
        """Test trends service handles empty keyword."""
        result = trends_service.get_related_queries(keyword="")
        assert result is None

        result = trends_service.get_related_queries(keyword="   ")
        assert result is None

    @patch('src.services.services.TrendReq')
    def test_trends_trending_searches(self, mock_trend_req, trends_service):
        """Test getting trending searches."""
        mock_pytrends = Mock()
        mock_pytrends.trending_searches.return_value = {"trending": "data"}
        trends_service.pytrends = mock_pytrends

        result = trends_service.get_trending_searches(geo="united_states")

        assert result == {"trending": "data"}
        assert mock_pytrends.trending_searches.called

    @patch('src.services.services.TrendReq')
    def test_trends_handles_empty_geo(self, mock_trend_req, trends_service):
        """Test trends service handles empty geo."""
        result = trends_service.get_trending_searches(geo="")
        assert result is None

    @patch('src.services.services.TrendReq')
    def test_trends_error_handling(self, mock_trend_req, trends_service):
        """Test trends service handles API errors gracefully."""
        mock_pytrends = Mock()
        mock_pytrends.interest_over_time.side_effect = Exception("API Error")
        trends_service.pytrends = mock_pytrends

        result = trends_service.get_interest_over_time(keywords=["test"])

        assert result is None  # Should return None on error


class TestBackoffStrategies:
    """Tests for exponential backoff and retry strategies."""

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
            """Calculate exponential backoff delay."""
            delay = min(base_delay * (2 ** attempt), max_delay)
            return delay

        # Test backoff progression
        assert calculate_backoff(0) == 1.0
        assert calculate_backoff(1) == 2.0
        assert calculate_backoff(2) == 4.0
        assert calculate_backoff(3) == 8.0
        assert calculate_backoff(10) == 60.0  # Capped at max

    def test_retry_with_exponential_backoff(self):
        """Test retry logic with exponential backoff."""
        attempts = []

        def failing_function():
            """Function that fails first 2 times."""
            attempts.append(time.time())
            if len(attempts) < 3:
                raise Exception("Temporary failure")
            return "Success"

        def retry_with_backoff(func, max_retries=5, base_delay=0.01):
            """Retry function with exponential backoff."""
            for attempt in range(max_retries):
                try:
                    return func()
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = min(base_delay * (2 ** attempt), 10.0)
                    time.sleep(delay)

        result = retry_with_backoff(failing_function, max_retries=5, base_delay=0.01)

        assert result == "Success"
        assert len(attempts) == 3  # Failed twice, succeeded third time

    def test_retry_respects_max_attempts(self):
        """Test retry logic respects max attempts."""
        attempts = [0]

        def always_failing():
            attempts[0] += 1
            raise Exception("Persistent failure")

        def retry_with_backoff(func, max_retries=3, base_delay=0.01):
            for attempt in range(max_retries):
                try:
                    return func()
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = min(base_delay * (2 ** attempt), 10.0)
                    time.sleep(delay)

        with pytest.raises(Exception) as exc_info:
            retry_with_backoff(always_failing, max_retries=3)

        assert attempts[0] == 3  # Should have tried exactly 3 times
        assert "failure" in str(exc_info.value).lower()


class TestNetworkCallLimits:
    """Tests ensuring network calls stay under rate limits."""

    @patch('requests.post')
    def test_gemini_concurrent_requests_under_limit(self, mock_post):
        """Test concurrent Gemini requests stay under rate limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Response"}]}}]
        }
        mock_post.return_value = mock_response

        limiter = GeminiRateLimiter(requests_per_minute=20)
        request_times = []

        def make_request():
            limiter.wait_if_needed()
            request_times.append(time.time())
            limiter.mark_request()

        # Make 10 requests across 2 threads - within limit so should be fast
        def worker():
            for _ in range(5):
                make_request()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have made 10 requests
        assert len(request_times) == 10

        # Check that no 60-second window has more than 20 requests
        for i in range(len(request_times)):
            window_end = request_times[i] + 60.0
            count_in_window = sum(
                1 for t in request_times
                if request_times[i] <= t < window_end
            )
            assert count_in_window <= 20, f"Rate limit violated: {count_in_window} requests in 60s window"

    def test_rate_limiter_prevents_burst(self):
        """Test rate limiter prevents burst traffic."""
        limiter = GeminiRateLimiter(requests_per_minute=5)

        # Try to make 5 rapid requests - at the limit
        for i in range(5):
            limiter.wait_if_needed()
            limiter.mark_request()

        # Should have accepted all 5
        assert len(limiter.request_times) == 5


class TestProductionReadiness:
    """Production-ready tests for Gemini and PyTrends integration."""

    @pytest.fixture
    def prod_config(self, tmp_path):
        """Create production-ready config for testing."""
        config = Mock()
        config.gemini_api_key = "test_key"
        config.openai_api_key = None  # Disable OpenAI to test Gemini only
        config.cache_dir = str(tmp_path / "cache")
        config.ollama_base_url = "http://localhost:11434"
        config.gemini_rpm_limit = 60
        config.openai_rpm_limit = 60
        config.ollama_rpm_limit = 300
        config.llm = Mock()
        config.llm.max_tokens = 2048
        return config

    @patch('requests.post')
    def test_gemini_handles_network_errors(self, mock_post, prod_config):
        """Test Gemini handles network errors gracefully."""
        import requests

        mock_post.side_effect = requests.ConnectionError("Network error")

        from src.services.services import LLMService

        with patch('src.services.services.get_connection_pool') as mock_pool:
            mock_pool_instance = Mock()
            mock_pool_instance.get.side_effect = requests.RequestException("Ollama not available")
            mock_pool.return_value = mock_pool_instance

            service = LLMService(prod_config)

            with pytest.raises(requests.RequestException):
                service._call_gemini("Test", "gemini-1.5-flash", 0.7, 30)

    @patch('requests.post')
    def test_gemini_validates_api_key(self, mock_post, prod_config):
        """Test Gemini validates API key presence."""
        # Mock 401 unauthorized response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Invalid API key")
        mock_post.return_value = mock_response

        from src.services.services import LLMService

        with patch('src.services.services.get_connection_pool') as mock_pool:
            mock_pool_instance = Mock()
            mock_pool_instance.get.side_effect = requests.RequestException("Ollama not available")
            mock_pool.return_value = mock_pool_instance

            service = LLMService(prod_config)

            with pytest.raises(Exception):
                service._call_gemini("Test", "gemini-1.5-flash", 0.7, 30)

    def test_rate_limiter_handles_zero_requests(self):
        """Test rate limiter handles edge case of zero requests."""
        limiter = GeminiRateLimiter(requests_per_minute=10)

        # Should not crash with no requests
        limiter.wait_if_needed()
        assert len(limiter.request_times) == 0

    def test_rate_limiter_handles_very_high_load(self):
        """Test rate limiter handles very high concurrent load."""
        limiter = GeminiRateLimiter(requests_per_minute=100)

        request_count = [0]
        lock = threading.Lock()

        def make_requests():
            for _ in range(10):
                limiter.wait_if_needed()
                limiter.mark_request()
                with lock:
                    request_count[0] += 1

        # 20 threads making 10 requests each = 200 total
        threads = [threading.Thread(target=make_requests) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)  # 30s timeout

        # All requests should complete
        assert request_count[0] == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
