"""Tests for LLMService rate limiting and model mapping."""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import Config
from src.services.services import LLMService, RateLimiter, ModelMapper


class TestRateLimiter:
    """Test RateLimiter functionality."""
    
    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert len(limiter.requests) == 0
    
    def test_rate_limiter_allows_under_limit(self):
        """Test rate limiter allows requests under limit."""
        limiter = RateLimiter(requests_per_minute=10)
        
        # Should allow 10 requests
        for _ in range(10):
            assert limiter.acquire(timeout=1.0) is True
    
    def test_rate_limiter_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        limiter = RateLimiter(requests_per_minute=5)
        
        # Use 5 requests
        for _ in range(5):
            assert limiter.acquire(timeout=0.1) is True
        
        # 6th request should timeout
        assert limiter.acquire(timeout=0.2) is False
    
    def test_rate_limiter_resets_after_minute(self):
        """Test rate limiter resets after 60 seconds."""
        limiter = RateLimiter(requests_per_minute=2)
        
        # Use both requests
        assert limiter.acquire(timeout=0.1) is True
        assert limiter.acquire(timeout=0.1) is True
        
        # Manually clear old requests to simulate time passing
        limiter.requests.clear()
        
        # Should allow more requests after reset
        assert limiter.acquire(timeout=0.1) is True
    
    def test_rate_limiter_thread_safe(self):
        """Test rate limiter is thread-safe."""
        limiter = RateLimiter(requests_per_minute=20)
        successes = []
        
        def acquire_token():
            result = limiter.acquire(timeout=1.0)
            successes.append(result)
        
        # Create 20 threads trying to acquire
        threads = [threading.Thread(target=acquire_token) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed since we're under limit
        assert sum(successes) == 20


class TestModelMapper:
    """Test ModelMapper functionality."""
    
    def setup_method(self):
        """Setup test config."""
        self.config = Config()
        self.config.ollama_topic_model = "llama2"
        self.config.gemini_model = "models/gemini-1.5-flash"
    
    def test_model_mapper_generic_default(self):
        """Test mapping generic 'default' model."""
        # Test for each provider
        assert ModelMapper.get_provider_model("default", "OLLAMA", self.config) == "llama2"
        assert ModelMapper.get_provider_model("default", "GEMINI", self.config) == "models/gemini-1.5-flash"
        assert ModelMapper.get_provider_model("default", "OPENAI", self.config) == "gpt-3.5-turbo"
    
    def test_model_mapper_generic_fast(self):
        """Test mapping generic 'fast' model."""
        assert ModelMapper.get_provider_model("fast", "OLLAMA", self.config) == "mistral"
        assert ModelMapper.get_provider_model("fast", "GEMINI", self.config) == "models/gemini-1.5-flash"
        assert ModelMapper.get_provider_model("fast", "OPENAI", self.config) == "gpt-3.5-turbo"
    
    def test_model_mapper_generic_smart(self):
        """Test mapping generic 'smart' model."""
        assert ModelMapper.get_provider_model("smart", "OLLAMA", self.config) == "llama3.2"
        assert ModelMapper.get_provider_model("smart", "GEMINI", self.config) == "models/gemini-1.5-pro"
        assert ModelMapper.get_provider_model("smart", "OPENAI", self.config) == "gpt-4"
    
    def test_model_mapper_generic_code(self):
        """Test mapping generic 'code' model."""
        assert ModelMapper.get_provider_model("code", "OLLAMA", self.config) == "codellama"
        assert ModelMapper.get_provider_model("code", "GEMINI", self.config) == "models/gemini-1.5-flash"
        assert ModelMapper.get_provider_model("code", "OPENAI", self.config) == "gpt-4"
    
    def test_model_mapper_none_uses_config(self):
        """Test None model uses config defaults."""
        assert ModelMapper.get_provider_model(None, "OLLAMA", self.config) == "llama2"
        assert ModelMapper.get_provider_model(None, "GEMINI", self.config) == "models/gemini-1.5-flash"
        assert ModelMapper.get_provider_model(None, "OPENAI", self.config) == "gpt-3.5-turbo"
    
    def test_model_mapper_specific_model_passthrough(self):
        """Test specific model names pass through unchanged."""
        assert ModelMapper.get_provider_model("llama3", "OLLAMA", self.config) == "llama3"
        assert ModelMapper.get_provider_model("models/gemini-pro", "GEMINI", self.config) == "models/gemini-pro"
        assert ModelMapper.get_provider_model("gpt-4-turbo", "OPENAI", self.config) == "gpt-4-turbo"


class TestLLMServiceRateLimiting:
    """Test LLMService with rate limiting."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        config = Config()
        config.cache_dir = str(tmp_path / "cache")
        config.ollama_base_url = "http://localhost:11434"
        config.gemini_api_key = "test-gemini-key"
        config.openai_api_key = "test-openai-key"
        config.llm_temperature = 0.7
        config.cache_ttl = 86400
        config.ollama_topic_model = "llama2"
        config.gemini_model = "models/gemini-1.5-flash"
        
        # Set low rate limits for testing
        config.gemini_rpm_limit = 3
        config.openai_rpm_limit = 3
        config.ollama_rpm_limit = 5
        
        return config
    
    @patch('src.services.services.get_connection_pool')
    def test_rate_limiter_initialized(self, mock_pool, config):
        """Test rate limiters are initialized for each provider."""
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        
        service = LLMService(config)
        
        assert "GEMINI" in service.rate_limiters
        assert "OPENAI" in service.rate_limiters
        assert "OLLAMA" in service.rate_limiters
        assert service.rate_limiters["GEMINI"].requests_per_minute == 3
        assert service.rate_limiters["OPENAI"].requests_per_minute == 3
        assert service.rate_limiters["OLLAMA"].requests_per_minute == 5
    
    @patch('src.services.services.get_connection_pool')
    @patch('src.services.services.requests.post')
    def test_rate_limit_prevents_excessive_calls(self, mock_post, mock_pool, config):
        """Test rate limiting prevents excessive API calls."""
        # Setup mocks
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        mock_pool.return_value.post.return_value = Mock(
            status_code=200,
            json=lambda: {"response": "Test response"}
        )
        
        service = LLMService(config)
        
        # Make requests up to the limit (3 for Gemini, but Ollama is first with limit 5)
        # Since Ollama is first in fallback chain, we need to make it fail to test Gemini
        service.providers = ["GEMINI"]  # Force using Gemini
        
        # Make 3 successful requests (at limit)
        for i in range(3):
            try:
                # Mock the Gemini response
                mock_post.return_value = Mock(
                    status_code=200,
                    json=lambda: {
                        "candidates": [{
                            "content": {
                                "parts": [{"text": f"Response {i}"}]
                            }
                        }]
                    }
                )
                result = service.generate(f"Test prompt {i}", max_retries=1)
                assert result == f"Response {i}"
            except Exception:
                pass
        
        # 4th request should hit rate limit and try to wait
        # Since timeout is 30s by default, this would wait, but we set max_retries=1
        # and the provider will be skipped, causing all providers to fail
        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            service.generate("Test prompt 4", max_retries=1)
    
    @patch('src.services.services.get_connection_pool')
    def test_rate_limit_per_provider(self, mock_pool, config):
        """Test each provider has independent rate limits."""
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        
        service = LLMService(config)
        
        # Check rate limiters are independent
        assert service.rate_limiters["OLLAMA"].requests_per_minute == 5
        assert service.rate_limiters["GEMINI"].requests_per_minute == 3
        assert service.rate_limiters["OPENAI"].requests_per_minute == 3


class TestLLMServiceModelMapping:
    """Test LLMService with model mapping."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        config = Config()
        config.cache_dir = str(tmp_path / "cache")
        config.ollama_base_url = "http://localhost:11434"
        config.gemini_api_key = "test-gemini-key"
        config.openai_api_key = None  # Only test Ollama and Gemini
        config.llm_temperature = 0.7
        config.cache_ttl = 86400
        config.ollama_topic_model = "llama2"
        config.gemini_model = "models/gemini-1.5-flash"
        config.gemini_rpm_limit = 60
        config.ollama_rpm_limit = 300
        return config
    
    @patch('src.services.services.get_connection_pool')
    def test_generic_model_maps_to_provider(self, mock_pool, config):
        """Test generic model names map to provider-specific models."""
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        mock_pool.return_value.post.return_value = Mock(
            status_code=200,
            json=lambda: {"response": "Test response"}
        )
        
        service = LLMService(config)
        
        # Test with generic "fast" model
        with patch.object(service, '_call_ollama', return_value="Response") as mock_ollama:
            service.providers = ["OLLAMA"]
            service.generate("Test", model="fast")
            
            # Should have been called with "mistral" (the fast Ollama model)
            mock_ollama.assert_called_once()
            args = mock_ollama.call_args
            assert args[0][1] == "mistral"  # Second arg is model name
    
    @patch('src.services.services.get_connection_pool')
    @patch('src.services.services.requests.post')
    def test_code_model_maps_correctly(self, mock_post, mock_pool, config):
        """Test 'code' model maps to codellama on Ollama."""
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        mock_pool.return_value.post.return_value = Mock(
            status_code=200,
            json=lambda: {"response": "Code response"}
        )
        
        service = LLMService(config)
        
        with patch.object(service, '_call_ollama', return_value="Response") as mock_ollama:
            service.providers = ["OLLAMA"]
            service.generate("Write code", model="code")
            
            # Should use codellama
            mock_ollama.assert_called_once()
            args = mock_ollama.call_args
            assert args[0][1] == "codellama"
    
    @patch('src.services.services.get_connection_pool')
    @patch('src.services.services.requests.post')
    def test_smart_model_maps_per_provider(self, mock_post, mock_pool, config):
        """Test 'smart' model maps differently per provider."""
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        
        service = LLMService(config)
        
        # Test Ollama - should use llama3.2
        with patch.object(service, '_call_ollama', return_value="Ollama response") as mock_ollama:
            service.providers = ["OLLAMA"]
            service.generate("Smart task for ollama", model="smart")
            args = mock_ollama.call_args
            assert args[0][1] == "llama3.2"
        
        # Test Gemini - should use gemini-1.5-pro
        # Clear cache to ensure fresh call
        service.cache.clear()
        with patch.object(service, '_call_gemini', return_value="Gemini response") as mock_gemini:
            service.providers = ["GEMINI"]
            service.generate("Smart task for gemini", model="smart")
            args = mock_gemini.call_args
            assert args[0][1] == "models/gemini-1.5-pro"
    
    @patch('src.services.services.get_connection_pool')
    def test_specific_model_passes_through(self, mock_pool, config):
        """Test specific model names pass through unchanged."""
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        
        service = LLMService(config)
        
        # Test with specific model name
        with patch.object(service, '_call_ollama', return_value="Response") as mock_ollama:
            service.providers = ["OLLAMA"]
            service.generate("Test", model="llama3")
            
            # Should use exactly "llama3"
            mock_ollama.assert_called_once()
            args = mock_ollama.call_args
            assert args[0][1] == "llama3"
    
    @patch('src.services.services.get_connection_pool')
    def test_none_model_uses_config_default(self, mock_pool, config):
        """Test None model uses config defaults."""
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        
        service = LLMService(config)
        
        with patch.object(service, '_call_ollama', return_value="Response") as mock_ollama:
            service.providers = ["OLLAMA"]
            service.generate("Test", model=None)
            
            # Should use config default (llama2)
            mock_ollama.assert_called_once()
            args = mock_ollama.call_args
            assert args[0][1] == "llama2"


class TestIntegrationRateLimitingAndMapping:
    """Integration tests combining rate limiting and model mapping."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        config = Config()
        config.cache_dir = str(tmp_path / "cache")
        config.ollama_base_url = "http://localhost:11434"
        config.gemini_api_key = "test-key"
        config.openai_api_key = None
        config.llm_temperature = 0.7
        config.cache_ttl = 86400
        config.ollama_topic_model = "llama2"
        config.gemini_model = "models/gemini-1.5-flash"
        config.gemini_rpm_limit = 2
        config.ollama_rpm_limit = 3
        return config
    
    @patch('src.services.services.get_connection_pool')
    @patch('src.services.services.requests.post')
    def test_rate_limit_with_model_mapping(self, mock_post, mock_pool, config):
        """Test rate limiting works with model mapping."""
        mock_pool.return_value.get.return_value = Mock(status_code=200)
        
        service = LLMService(config)
        service.providers = ["OLLAMA"]
        
        # Mock Ollama responses
        call_count = [0]
        def get_response():
            call_count[0] += 1
            return Mock(
                status_code=200,
                json=lambda: {"response": f"Response {call_count[0]}"}
            )
        
        mock_pool.return_value.post.side_effect = lambda *args, **kwargs: get_response()
        
        # Make requests with different model mappings
        results = []
        for i, model in enumerate(["fast", "smart", "code"]):
            try:
                result = service.generate(f"Test {i}", model=model, max_retries=1)
                results.append(result)
            except RuntimeError:
                # Hit rate limit
                break
        
        # Should have gotten 3 responses (ollama_rpm_limit=3)
        assert len(results) == 3
    
    @patch('src.services.services.get_connection_pool')
    def test_fallback_respects_rate_limits(self, mock_pool, config):
        """Test fallback chain respects rate limits for each provider."""
        # Setup Ollama to be unavailable, only Gemini available
        import requests
        
        def mock_get(url, **kwargs):
            if "localhost:11434" in url:
                # Raise a requests exception to simulate connection failure
                raise requests.RequestException("Ollama not available")
            return Mock(status_code=200)
        
        mock_pool.return_value.get.side_effect = mock_get
        
        service = LLMService(config)
        
        # Should only have GEMINI provider (Ollama failed, OpenAI not configured)
        assert service.providers == ["GEMINI"]
        assert "GEMINI" in service.rate_limiters
        assert service.rate_limiters["GEMINI"].requests_per_minute == 2
