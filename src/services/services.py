"""External service integrations.

Implements LLMService, EmbeddingService, DatabaseService, GistService,
LinkChecker, and TrendsService with fallback chains and production-ready error handling.
"""

import time
import logging
import hashlib
import json
import os
import requests
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    TrendReq = None

from src.core.config import Config
from src.optimization.cache import cached
from src.optimization.connection_pool import ConnectionPool
from src.services.vectorstore import VectorStore
from src.utils.llm_response_validator import validate_llm_response, ValidationResult

logger = logging.getLogger(__name__)

# Global connection pool instance
_connection_pool: Optional[ConnectionPool] = None


def get_connection_pool() -> ConnectionPool:
    """Get or create global connection pool."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(pool_size=20, max_retries=3, timeout=30)
    return _connection_pool


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests: deque = deque()
        self._lock = threading.Lock()
        logger.debug(f"RateLimiter initialized: {requests_per_minute} req/min")
    
    def acquire(self, timeout: float = 30.0) -> bool:
        """Acquire permission to make a request.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                now = time.time()
                # Remove requests older than 1 minute
                while self.requests and self.requests[0] < now - 60:
                    self.requests.popleft()
                
                # Check if under limit
                if len(self.requests) < self.requests_per_minute:
                    self.requests.append(now)
                    return True
            
            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Rate limit acquisition timeout after {timeout}s")
                return False
            
            # Wait before retry
            time.sleep(0.1)


@dataclass
class LLMResponse:
    """LLM generation response with metadata."""
    text: str
    provider: str
    model: str
    tokens_used: int = 0
    latency_ms: int = 0
    cached: bool = False


class ModelMapper:
    """Maps generic model names to provider-specific models."""
    
    # Model mapping: generic_name -> {provider: provider_model}
    MODEL_MAP = {
        "default": {
            "OLLAMA": "llama2",
            "GEMINI": "models/gemini-1.5-flash",
            "OPENAI": "gpt-3.5-turbo"
        },
        "fast": {
            "OLLAMA": "mistral",
            "GEMINI": "models/gemini-1.5-flash",
            "OPENAI": "gpt-3.5-turbo"
        },
        "smart": {
            "OLLAMA": "llama3.2",
            "GEMINI": "models/gemini-1.5-pro",
            "OPENAI": "gpt-4"
        },
        "code": {
            "OLLAMA": "codellama",
            "GEMINI": "models/gemini-1.5-flash",
            "OPENAI": "gpt-4"
        }
    }
    
    @classmethod
    def get_provider_model(cls, generic_model: Optional[str], provider: str, config: Config) -> str:
        """Get provider-specific model name.
        
        Args:
            generic_model: Generic model name (e.g., "default", "fast", "smart", "code")
            provider: Provider name (OLLAMA, GEMINI, OPENAI)
            config: Configuration object with provider-specific model settings
            
        Returns:
            Provider-specific model name
        """
        # If no generic model specified, use provider defaults from config
        if not generic_model:
            if provider == "OLLAMA":
                return config.ollama_topic_model
            elif provider == "GEMINI":
                return config.gemini_model
            elif provider == "OPENAI":
                return "gpt-3.5-turbo"
        
        # If generic model in map, return mapped model
        if generic_model in cls.MODEL_MAP:
            return cls.MODEL_MAP[generic_model].get(provider, generic_model)
        
        # Otherwise, assume it's already a provider-specific model
        return generic_model


class LLMService:
    """Service for interacting with various LLM providers with fallback chain.
    
    Provider priority: Ollama → Gemini → OpenAI
    Each provider is tried in order with exponential backoff.
    Includes rate limiting and model mapping.
    """

    def __init__(self, config: Config):
        """Initialize LLM service with provider configuration.
        
        Args:
            config: Configuration object with LLM settings
            
        Raises:
            ValueError: If no providers are available
        """
        self.config = config
        self.cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_lock = threading.Lock()
        cache_dir = Path(config.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = cache_dir / "responses.jsonl"
        
        # Initialize rate limiters per provider
        self.rate_limiters: Dict[str, RateLimiter] = {
            "GEMINI": RateLimiter(requests_per_minute=getattr(config, 'gemini_rpm_limit', 60)),
            "OPENAI": RateLimiter(requests_per_minute=getattr(config, 'openai_rpm_limit', 60)),
            "OLLAMA": RateLimiter(requests_per_minute=getattr(config, 'ollama_rpm_limit', 300))
        }
        
        # Load existing cache
        self._load_cache()
        
        # Setup provider priority
        self.providers = self._get_provider_list()
        if not self.providers:
            raise ValueError("No LLM providers available. Check API keys and Ollama connection.")
        
        logger.info(f"LLMService initialized with providers: {', '.join(self.providers)}")
        logger.info(f"Rate limits: {', '.join([f'{p}={self.rate_limiters[p].requests_per_minute}/min' for p in self.providers if p in self.rate_limiters])}")

    def _get_provider_list(self) -> List[str]:
        """Get list of available providers based on configuration.
        
        Returns:
            List of provider names in priority order
        """
        providers = []
        pool = get_connection_pool()
        
        # Check Ollama
        try:
            response = pool.get(
                f"{self.config.ollama_base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            providers.append("OLLAMA")
            logger.info("✓ Ollama available")
        except (requests.RequestException, requests.Timeout, ConnectionError) as e:
            logger.warning(f"Ollama not available: {e}")
        
        # Check Gemini
        if self.config.gemini_api_key:
            providers.append("GEMINI")
            logger.info("✓ Gemini API key configured")
        else:
            logger.debug("Gemini API key not configured")
        
        # Check OpenAI
        if self.config.openai_api_key:
            providers.append("OPENAI")
            logger.info("✓ OpenAI API key configured")
        else:
            logger.debug("OpenAI API key not configured")
        
        return providers

    def _load_cache(self):
        """Load response cache from disk."""
        if not self.cache_path.exists():
            logger.debug(f"Cache file not found: {self.cache_path}")
            return
        
        try:
            loaded = 0
            expired = 0
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        key = entry['input_hash']
                        text = entry['output']
                        timestamp_str = entry['timestamp']
                        
                        # Parse timestamp
                        ts = datetime.fromisoformat(timestamp_str)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        
                        # Check expiry
                        age = datetime.now(timezone.utc) - ts
                        if age < timedelta(seconds=self.config.cache_ttl):
                            self.cache[key] = (text, ts)
                            loaded += 1
                        else:
                            expired += 1
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Invalid cache entry: {e}")
                        continue
            
            if loaded > 0:
                logger.info(f"Loaded {loaded} cached responses ({expired} expired)")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            self.cache = {}

    def _save_to_cache(self, input_hash: str, output: str):
        """Save response to cache.
        
        Args:
            input_hash: Hash of input prompt
            output: Generated text
        """
        timestamp = datetime.now(timezone.utc)
        
        with self._cache_lock:
            self.cache[input_hash] = (output, timestamp)
        
        try:
            # File write doesn't need lock (append is atomic on most systems)
            with open(self.cache_path, 'a', encoding='utf-8') as f:
                entry = {
                    'input_hash': input_hash,
                    'output': output,
                    'timestamp': timestamp.isoformat()
                }
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.warning(f"Failed to write to cache: {e}")

    def _get_cache_key(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate cache key for prompt.
        
        Args:
            prompt: Input prompt
            model: Optional model override
            **kwargs: Additional parameters
            
        Returns:
            MD5 hash of normalized inputs
        """
        # Normalize inputs
        normalized = {
            'prompt': prompt,
            'model': model or 'default',
            'temperature': kwargs.get('temperature', self.config.llm_temperature),
            'deterministic': self.config.deterministic
        }
        
        key_str = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    @cached(ttl=3600, max_size=1000)
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """Generate text using LLM with fallback chain (cached).
        
        Args:
            prompt: Input prompt text
            model: Optional model override (generic or provider-specific)
            temperature: Optional temperature override
            max_retries: Retries per provider
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
            
        Raises:
            RuntimeError: If all providers fail
        """
        # Check cache first
        cache_key = self._get_cache_key(prompt, model, temperature=temperature, **kwargs)
        with self._cache_lock:
            if cache_key in self.cache:
                cached_text, cached_time = self.cache[cache_key]
                age = datetime.now(timezone.utc) - cached_time
                if age < timedelta(seconds=self.config.cache_ttl):
                    logger.debug(f"Cache hit (age: {age.seconds}s)")
                    return cached_text
        
        # Determine effective temperature
        if self.config.deterministic:
            temp = 0.0
        elif temperature is not None:
            temp = temperature
        else:
            temp = self.config.llm_temperature
        
        # Try each provider in order
        errors = []
        for provider in self.providers:
            logger.info(f"Attempting provider: {provider}")
            
            # Acquire rate limit before attempting
            if provider in self.rate_limiters:
                if not self.rate_limiters[provider].acquire(timeout=30.0):
                    error_msg = f"{provider} rate limit exceeded"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue
            
            for attempt in range(max_retries):
                try:
                    result = self._call_provider(
                        provider=provider,
                        prompt=prompt,
                        model=model,
                        temperature=temp,
                        **kwargs
                    )

                    # Validate LLM response before returning
                    validation = validate_llm_response(
                        content=result,
                        content_type=kwargs.get('content_type', 'unknown'),
                        allow_partial=kwargs.get('allow_partial', False)
                    )

                    if not validation.is_valid:
                        logger.warning(
                            f"LLM response validation failed (attempt {attempt+1}/{max_retries}): {', '.join(validation.errors[:3])}",
                            extra={
                                "layer": "llm_validation",
                                "provider": provider,
                                "attempt": attempt + 1,
                                "errors_count": len(validation.errors),
                                "will_retry": attempt < max_retries - 1
                            }
                        )

                        if attempt < max_retries - 1:
                            # Enhance prompt for retry
                            prompt = self._enhance_prompt_for_retry(prompt, validation.errors)
                            logger.info(f"Retrying with enhanced prompt (attempt {attempt+2}/{max_retries})")
                            continue  # Retry with enhanced prompt
                        else:
                            # Max retries reached - log but allow to proceed
                            # (Layer 2 markdown validator will attempt auto-fix)
                            logger.error(
                                f"LLM validation failed after {max_retries} attempts",
                                extra={
                                    "layer": "llm_validation",
                                    "provider": provider,
                                    "max_retries": max_retries,
                                    "errors": validation.errors
                                }
                            )
                    else:
                        logger.info(
                            f"LLM response validation passed (attempt {attempt+1})",
                            extra={
                                "layer": "llm_validation",
                                "validation_duration_ms": validation.validation_duration_ms
                            }
                        )

                    # Validation passed or max retries reached - proceed
                    logger.info(f"✓ Success with {provider} (attempt {attempt + 1})")
                    self._save_to_cache(cache_key, result)
                    return result
                    
                except Exception as e:
                    error_msg = f"{provider} attempt {attempt + 1} failed: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    
                    if attempt < max_retries - 1:
                        delay = (2 ** attempt) * 1.0  # Exponential backoff
                        time.sleep(delay)
        
        # All providers failed
        error_summary = "\n".join(errors)
        raise RuntimeError(
            f"All LLM providers failed after {max_retries} retries each:\n{error_summary}"
        )

    def _enhance_prompt_for_retry(self, prompt: str, errors: List[str]) -> str:
        """Enhance prompt with formatting instructions based on validation errors.

        Args:
            prompt: Original prompt
            errors: List of validation error messages

        Returns:
            Enhanced prompt with additional instructions
        """
        enhancements = []

        if any('code block' in e.lower() or 'fence' in e.lower() for e in errors):
            enhancements.append(
                "IMPORTANT: Do NOT wrap your entire response in a code block. "
                "Use code blocks (```) only for code examples, not for the whole document."
            )

        if any('frontmatter' in e.lower() for e in errors):
            enhancements.append(
                "IMPORTANT: Do NOT include YAML frontmatter (---). "
                "It will be added automatically by the system."
            )

        if any('truncated' in e.lower() or 'incomplete' in e.lower() or 'too short' in e.lower() for e in errors):
            enhancements.append(
                "IMPORTANT: Complete your response fully. "
                "End with a proper conclusion, not mid-sentence."
            )

        if any('prose' in e.lower() or 'heading' in e.lower() for e in errors):
            enhancements.append(
                "IMPORTANT: Generate proper markdown with headings (##) and well-structured paragraphs."
            )

        if not enhancements:
            # Generic enhancement for unknown errors
            enhancements.append(
                "IMPORTANT: Ensure your response is well-formatted markdown "
                "with balanced code blocks and complete sentences."
            )

        enhancement_text = "\n".join(enhancements)
        return f"{enhancement_text}\n\n{prompt}"

    def _call_provider(
        self,
        provider: str,
        prompt: str,
        model: Optional[str],
        temperature: float,
        **kwargs
    ) -> str:
        """Call specific LLM provider.
        
        Args:
            provider: Provider name (OLLAMA, GEMINI, OPENAI)
            prompt: Input prompt
            model: Model override (generic or provider-specific)
            temperature: Temperature value
            **kwargs: Additional parameters
            
        Returns:
            Generated text
            
        Raises:
            Exception: Provider-specific errors
        """
        timeout = kwargs.get('timeout', 30)
        
        # Map model to provider-specific name
        provider_model = ModelMapper.get_provider_model(model, provider, self.config)
        logger.debug(f"Using model '{provider_model}' for {provider}")
        
        if provider == "OLLAMA":
            return self._call_ollama(prompt, provider_model, temperature, timeout)
        elif provider == "GEMINI":
            return self._call_gemini(prompt, provider_model, temperature, timeout)
        elif provider == "OPENAI":
            return self._call_openai(prompt, provider_model, temperature, timeout)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _call_ollama(
        self,
        prompt: str,
        model: str,
        temperature: float,
        timeout: int
    ) -> str:
        """Call Ollama API using connection pool.
        
        Args:
            prompt: Input prompt
            model: Model name
            temperature: Temperature value
            timeout: Request timeout
            
        Returns:
            Generated text
            
        Raises:
            requests.RequestException: On API errors
        """
        url = f"{self.config.ollama_base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        }
        
        pool = get_connection_pool()
        
        try:
            response = pool.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            result = data.get("response", "").strip()
            
            if not result:
                raise ValueError("Empty response from Ollama")
            
            return result
            
        except requests.Timeout:
            raise TimeoutError(f"Ollama request timeout after {timeout}s")
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            raise requests.RequestException(f"Ollama API error (status: {status}): {e}")

    def _call_gemini(
        self,
        prompt: str,
        model: str,
        temperature: float,
        timeout: int
    ) -> str:
        """Call Google Gemini API.
        
        Args:
            prompt: Input prompt
            model: Model name
            temperature: Temperature value
            timeout: Request timeout
            
        Returns:
            Generated text
            
        Raises:
            requests.RequestException: On API errors
            ValueError: On invalid response structure
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": self.config.llm.max_tokens,
            }
        }
        
        params = {"key": self.config.gemini_api_key}
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in Gemini response")
            
            # Check if content exists
            content = candidates[0].get("content")
            if not content or "parts" not in content:
                raise ValueError("Invalid content structure in Gemini response")
            
            parts = content.get("parts", [])
            if not parts or "text" not in parts[0]:
                raise ValueError("No text in Gemini response parts")
            
            text = parts[0]["text"]
            result = text.strip()
            
            if not result:
                raise ValueError("Empty response from Gemini")
            
            return result
            
        except requests.Timeout:
            raise TimeoutError(f"Gemini request timeout after {timeout}s")
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            raise requests.RequestException(f"Gemini API error (status: {status}): {e}")

    def _call_openai(
        self,
        prompt: str,
        model: str,
        temperature: float,
        timeout: int
    ) -> str:
        """Call OpenAI API.
        
        Args:
            prompt: Input prompt
            model: Model name
            temperature: Temperature value
            timeout: Request timeout
            
        Returns:
            Generated text
            
        Raises:
            requests.RequestException: On API errors
            ValueError: On invalid response structure
        """
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.openai_api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": self.config.llm.max_tokens
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices in OpenAI response")
            
            message = choices[0].get("message", {})
            result = message.get("content", "").strip()
            
            if not result:
                raise ValueError("Empty response from OpenAI")
            
            return result
            
        except requests.Timeout:
            raise TimeoutError(f"OpenAI request timeout after {timeout}s")
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            raise requests.RequestException(f"OpenAI API error (status: {status}): {e}")

    def check_health(self) -> Dict[str, bool]:
        """Check health status of all configured providers.

        Returns:
            Dict mapping provider names to health status
        """
        health = {}

        # Check Ollama
        if "OLLAMA" in self.providers:
            try:
                pool = get_connection_pool()
                response = pool.get(
                    f"{self.config.ollama_base_url}/api/tags",
                    timeout=5
                )
                health["OLLAMA"] = response.status_code == 200
            except Exception:
                health["OLLAMA"] = False

        # Check Gemini
        if "GEMINI" in self.providers:
            health["GEMINI"] = bool(self.config.gemini_api_key)

        # Check OpenAI
        if "OPENAI" in self.providers:
            health["OPENAI"] = bool(self.config.openai_api_key)

        return health


def _coerce_text(output) -> str:
    """Coerce various SDK/mock outputs to a plain string."""
    try:
        import json as _json
        if output is None:
            return ""
        if isinstance(output, str):
            return output
        if isinstance(output, bytes):
            return output.decode('utf-8', errors='ignore')
        if isinstance(output, dict):
            for k in ('text','content','output','message'):
                if k in output and isinstance(output[k], (str, bytes)):
                    return output[k] if isinstance(output[k], str) else output[k].decode('utf-8','ignore')
            return _json.dumps(output, ensure_ascii=False)
        if isinstance(output, (list, tuple)):
            return ''.join(str(x) for x in output)
        return str(output)
    except Exception:
        return str(output)


class GeminiRateLimiter:
    """Rate limiter for Gemini API."""

    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = max(1, int(requests_per_minute))
        self.request_times: List[float] = []
        self._lock = threading.Lock()

    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        max_wait_seconds = 120  # Never wait more than 2 minutes
        wait_start = time.time()

        while True:
            # Timeout check
            if time.time() - wait_start > max_wait_seconds:
                logger.error("Rate limiter wait timeout, clearing state")
                with self._lock:
                    self.request_times = []  # Reset
                return

            with self._lock:
                now = time.time()
                # Keep only last 60s
                self.request_times = [t for t in self.request_times if (now - t) < 60.0]

                if len(self.request_times) < self.requests_per_minute:
                    return

                oldest = self.request_times[0]
                wait_time = max(0.0, 60.0 - (now - oldest) + 0.1)

            # Sleep outside lock
            time.sleep(min(wait_time, 10.0))  # Cap individual sleeps

    def mark_request(self):
        """Mark that a request was made."""
        with self._lock:
            self.request_times.append(time.time())

class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""

    def __init__(self, config: Config):
        """Initialize embedding service with GPU support."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not available. "
                "Install with: pip install sentence-transformers"
            )

        self.config = config
        model_name = getattr(config, 'embedding_model', 'sentence-transformers/all-MiniLM-L6-v2')
        device = getattr(config, 'device', 'cpu')

        # Initialize model with device
        self.model = SentenceTransformer(
            model_name,
            device=device
        )

        self.cache: Dict[str, List[float]] = {}

        logger.info(f"Embedding model loaded on {device}")
        if device == "cuda":
            batch_size = getattr(config, 'embedding_batch_size', 32)
            logger.info(f"Batch size for GPU: {batch_size}")

    def encode(self, texts: Union[str, List[str]], normalize: bool = True, batch_size: int = 32, show_progress_bar: bool = False) -> Union[List[float], List[List[float]]]:
        """Encode texts to embeddings with GPU acceleration and caching.

        Args:
            texts: Single text or list of texts to embed
            normalize: Whether to normalize embeddings
            batch_size: Batch size for encoding
            show_progress_bar: Whether to show progress

        Returns:
            Single embedding for str input, list of embeddings for list input
        """
        # Handle single text
        if isinstance(texts, str):
            if not texts:
                logger.warning("Empty text provided for embedding")
                return []

            embedding = self.model.encode(
                [texts],
                normalize_embeddings=normalize,
                batch_size=batch_size,
                show_progress_bar=show_progress_bar,
                convert_to_numpy=True
            )
            return embedding[0].tolist()

        # Handle list of texts
        if not texts:
            return []

        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)

        # Check cache
        for i, text in enumerate(texts):
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            if text_hash in self.cache:
                results[i] = self.cache[text_hash]
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        if uncached_texts:
            # Use larger batch size for GPU
            effective_batch_size = getattr(self.config, 'embedding_batch_size', batch_size) if self.config.device == "cuda" else 8
            embeddings = self.model.encode(
                uncached_texts,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress_bar or len(uncached_texts) > 100,
                batch_size=effective_batch_size,
                convert_to_numpy=True
            )

            # Cache results
            for i, embedding in zip(uncached_indices, embeddings):
                text = texts[i]
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                emb_list = embedding.tolist()
                self.cache[text_hash] = emb_list
                results[i] = emb_list

        return results

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between embeddings."""
        import numpy as np
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        # Normalize vectors to unit length
        vec1 = vec1 / np.linalg.norm(vec1)
        vec2 = vec2 / np.linalg.norm(vec2)
        return float(np.dot(vec1, vec2))

    def get_dimension(self) -> int:
        """Get embedding vector dimension.

        Returns:
            Dimension of embedding vectors
        """
        return self.model.get_sentence_embedding_dimension()


class DatabaseService:
    """Service for vector database operations using ChromaDB."""

    def __init__(self, config: Config):
        """Initialize database service.

        Args:
            config: Configuration object

        Raises:
            ImportError: If chromadb not available
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "chromadb not available. "
                "Install with: pip install chromadb"
            )

        self.config = config

        # Check if we should use HTTP client (for live E2E testing)
        chroma_host = os.getenv('CHROMA_HOST')
        chroma_port = os.getenv('CHROMA_PORT')

        if chroma_host and chroma_port:
            # Use HTTP client for remote Chroma
            self.client = chromadb.HttpClient(
                host=chroma_host,
                port=int(chroma_port),
                settings=ChromaSettings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )
            logger.info(f"✓ Using Chroma HTTP client: {chroma_host}:{chroma_port}")
        else:
            # Use persistent client for local database
            db_path = getattr(config.database, 'chroma_db_path', './chroma_db')
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            logger.info(f"✓ Using Chroma Persistent client: {db_path}")

        # Get collection name from config
        self.collection_name = getattr(config.database, 'collection_name', 'default')

        # Initialize VectorStore with the same client
        self.vectorstore = VectorStore(config, collection_name=self.collection_name, client=self.client)

        logger.info(f"✓ Database service initialized (collection: {self.collection_name})")

    def get_or_create_collection(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Get or create a collection.
        
        Args:
            name: Collection name (uses default if None)
            metadata: Optional collection metadata
            
        Returns:
            ChromaDB collection object
        """
        collection_name = name or self.collection_name

        # Ensure metadata is not empty (required by newer Chroma versions)
        collection_metadata = metadata if metadata else {"created_by": "content_generator"}

        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata=collection_metadata
            )
            logger.info(f"✓ Collection ready: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection '{collection_name}': {e}")
            raise

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        collection_name: Optional[str] = None
    ):
        """Add documents to collection.

        Args:
            documents: List of document texts
            metadatas: Optional list of metadata dicts
            ids: Optional list of document IDs
            embeddings: Optional pre-computed embeddings
            collection_name: Optional collection name
        """
        # Switch vectorstore collection if different collection specified
        if collection_name and collection_name != self.vectorstore.collection.name:
            self.vectorstore.switch_collection(collection_name)

        collection = self.get_or_create_collection(collection_name)

        # Generate IDs if not provided (required by newer Chroma versions)
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]

        try:
            # If embeddings provided, use them directly
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            logger.info(f"✓ Added {len(documents)} documents to {collection.name}")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    def query(
        self,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query collection for similar documents.

        Args:
            query_texts: List of query texts
            n_results: Number of results per query
            where: Optional metadata filter
            collection_name: Optional collection name

        Returns:
            Query results dict

        Raises:
            RuntimeError: If vectorstore not initialized
        """
        if self.vectorstore is None:
            raise RuntimeError("VectorStore not initialized")

        collection = self.get_or_create_collection(collection_name)
        
        try:
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where
            )
            logger.debug(f"Query returned {len(results.get('ids', [[]])[0])} results")
            return results
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    def get_all_documents(
        self,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get all documents from collection.
        
        Args:
            collection_name: Optional collection name
            limit: Optional result limit
            offset: Result offset
            
        Returns:
            All documents dict
        """
        collection = self.get_or_create_collection(collection_name)
        
        try:
            all_results = collection.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas", "embeddings"]
            )
            logger.debug(f"Retrieved {len(all_results.get('ids', []))} documents")
            return all_results
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            raise

    def delete_collection(self, name: Optional[str] = None):
        """Delete a collection.
        
        Args:
            name: Collection name (uses default if None)
        """
        collection_name = name or self.collection_name
        
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
            raise


class GistService:
    """Service for uploading content to GitHub Gists with full CRUD operations."""

    def __init__(self, config: Config):
        """Initialize Gist service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.token = config.github_gist_token
        self.enabled = config.gist_upload_enabled and bool(self.token)
        
        if not self.enabled:
            logger.warning("Gist upload disabled (missing token or disabled in config)")
        else:
            logger.info("✓ Gist service enabled")

    def create_gist(
        self,
        filename: str,
        content: str,
        description: str = "",
        public: bool = False
    ) -> Optional[str]:
        """Create a new Gist.
        
        Args:
            filename: Name of the file
            content: File content
            description: Gist description
            public: Whether gist is public
            
        Returns:
            Gist URL if successful, None otherwise
        """
        if not self.enabled:
            logger.debug("Gist upload skipped (disabled)")
            return None
        
        if not filename or not filename.strip():
            logger.error("Gist creation failed: filename is required")
            return None
        
        if not content or not content.strip():
            logger.error("Gist creation failed: content is required")
            return None
        
        url = "https://api.github.com/gists"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        payload = {
            "description": description,
            "public": public,
            "files": {
                filename: {"content": content}
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            gist_url = data.get("html_url")
            
            if not gist_url:
                logger.error("Gist creation failed: no URL in response")
                return None
            
            logger.info(f"✓ Created Gist: {gist_url}")
            return gist_url
            
        except requests.Timeout:
            logger.error("Gist creation failed: request timeout")
            return None
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            logger.error(f"Failed to create Gist (status: {status}): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create Gist: {e}")
            return None

    def get_gist(self, gist_id: str) -> Optional[Dict[str, Any]]:
        """Get an existing Gist by ID.
        
        Args:
            gist_id: The Gist ID
            
        Returns:
            Dict with Gist data or None on error
        """
        if not self.enabled:
            logger.debug("Gist retrieval skipped (disabled)")
            return None
        
        if not gist_id or not gist_id.strip():
            logger.error("Gist retrieval failed: gist_id is required")
            return None
        
        url = f"https://api.github.com/gists/{gist_id}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✓ Retrieved Gist: {gist_id}")
            return data
            
        except requests.Timeout:
            logger.error(f"Gist retrieval failed: request timeout for {gist_id}")
            return None
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            if status == 404:
                logger.error(f"Gist not found: {gist_id}")
            else:
                logger.error(f"Failed to get Gist {gist_id} (status: {status}): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get Gist {gist_id}: {e}")
            return None

    def update_gist(
        self,
        gist_id: str,
        filename: str,
        content: str,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an existing Gist.
        
        Args:
            gist_id: The Gist ID to update
            filename: Name of the file to update
            content: New file content
            description: Optional new description
            
        Returns:
            Dict with updated Gist data or None on error
        """
        if not self.enabled:
            logger.debug("Gist update skipped (disabled)")
            return None
        
        if not gist_id or not gist_id.strip():
            logger.error("Gist update failed: gist_id is required")
            return None
        
        if not filename or not filename.strip():
            logger.error("Gist update failed: filename is required")
            return None
        
        url = f"https://api.github.com/gists/{gist_id}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        payload: Dict[str, Any] = {
            "files": {
                filename: {"content": content}
            }
        }
        
        if description is not None:
            payload["description"] = description
        
        try:
            response = requests.patch(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✓ Updated Gist: {gist_id}")
            return data
            
        except requests.Timeout:
            logger.error(f"Gist update failed: request timeout for {gist_id}")
            return None
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            if status == 404:
                logger.error(f"Gist not found: {gist_id}")
            else:
                logger.error(f"Failed to update Gist {gist_id} (status: {status}): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to update Gist {gist_id}: {e}")
            return None

    def delete_gist(self, gist_id: str) -> bool:
        """Delete a Gist.
        
        Args:
            gist_id: The Gist ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Gist deletion skipped (disabled)")
            return False
        
        if not gist_id or not gist_id.strip():
            logger.error("Gist deletion failed: gist_id is required")
            return False
        
        url = f"https://api.github.com/gists/{gist_id}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✓ Deleted Gist: {gist_id}")
            return True
            
        except requests.Timeout:
            logger.error(f"Gist deletion failed: request timeout for {gist_id}")
            return False
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            if status == 404:
                logger.error(f"Gist not found: {gist_id}")
            else:
                logger.error(f"Failed to delete Gist {gist_id} (status: {status}): {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete Gist {gist_id}: {e}")
            return False


class TrendsService:
    """Service for Google Trends data using pytrends."""

    def __init__(self, config: Config):
        """Initialize Trends service.

        In mock mode (default), returns stub data without network calls.
        In live mode (TEST_MODE=live + ALLOW_NETWORK=1), creates real TrendReq.

        Args:
            config: Configuration object

        Raises:
            ImportError: If pytrends not available in live mode
        """
        self.config = config

        # Check if we should use real network
        test_mode = os.getenv('TEST_MODE', 'mock').lower()
        allow_network = os.getenv('ALLOW_NETWORK', '0') == '1'

        if test_mode == 'live' and allow_network:
            # Live mode: create real TrendReq
            if not PYTRENDS_AVAILABLE:
                raise ImportError(
                    "pytrends not available. "
                    "Install with: pip install pytrends"
                )
            self.pytrends = TrendReq(hl='en-US', tz=360)
            logger.info("✓ Trends service initialized (LIVE mode)")
        else:
            # Mock mode: use stub (no network)
            self.pytrends = None
            logger.info("✓ Trends service initialized (MOCK mode - stub data)")

    def get_interest_over_time(
        self,
        keywords: List[str],
        timeframe: str = 'today 12-m'
    ) -> Optional[Any]:
        """Get interest over time for keywords.

        Args:
            keywords: List of keywords to query
            timeframe: Time frame for data

        Returns:
            DataFrame with interest data or None on error
        """
        if not keywords:
            logger.warning("No keywords provided for trends query")
            return None

        # Filter out empty keywords
        keywords = [k.strip() for k in keywords if k and k.strip()]
        if not keywords:
            logger.warning("No valid keywords after filtering")
            return None

        # Mock mode: return deterministic stub
        if self.pytrends is None:
            logger.debug("Mock mode: returning stub interest data")
            return self._stub_interest_data(keywords)

        # Live mode: real network call
        try:
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            data = self.pytrends.interest_over_time()
            return data
        except Exception as e:
            logger.error(f"Failed to get trends data for {keywords}: {e}")
            return None

    def get_related_queries(self, keyword: str) -> Optional[Dict[str, Any]]:
        """Get related queries for a keyword.

        Args:
            keyword: Keyword to query

        Returns:
            Dict with top and rising queries or None on error
        """
        if not keyword or not keyword.strip():
            logger.warning("Empty keyword provided for related queries")
            return None

        # Mock mode: return deterministic stub
        if self.pytrends is None:
            logger.debug("Mock mode: returning stub related queries")
            return self._stub_related_queries(keyword)

        # Live mode: real network call
        try:
            self.pytrends.build_payload([keyword.strip()])
            data = self.pytrends.related_queries()
            return data.get(keyword.strip(), {})
        except Exception as e:
            logger.error(f"Failed to get related queries for '{keyword}': {e}")
            return None

    def get_trending_searches(self, geo: str = 'united_states') -> Optional[Any]:
        """Get current trending searches for a region.

        Args:
            geo: Geographic region (default: 'united_states')

        Returns:
            DataFrame with trending searches or None on error
        """
        if not geo or not geo.strip():
            logger.warning("Empty geo provided for trending searches")
            return None

        # Mock mode: return deterministic stub
        if self.pytrends is None:
            logger.debug("Mock mode: returning stub trending searches")
            return self._stub_trending_searches(geo)

        # Live mode: real network call
        try:
            data = self.pytrends.trending_searches(pn=geo)
            logger.info(f"✓ Retrieved trending searches for {geo}")
            return data
        except Exception as e:
            logger.error(f"Failed to get trending searches for '{geo}': {e}")
            return None

    def _stub_interest_data(self, keywords: List[str]) -> Any:
        """Return deterministic stub data for interest_over_time in mock mode."""
        try:
            import pandas as pd
            # Return empty DataFrame (mimics no-data response from PyTrends)
            return pd.DataFrame()
        except ImportError:
            # If pandas not available, return None
            return None

    def _stub_related_queries(self, keyword: str) -> Dict[str, Any]:
        """Return deterministic stub data for related_queries in mock mode."""
        # Return empty dict (mimics no related queries)
        return {}

    def _stub_trending_searches(self, geo: str) -> Any:
        """Return deterministic stub data for trending_searches in mock mode."""
        try:
            import pandas as pd
            # Return empty DataFrame
            return pd.DataFrame()
        except ImportError:
            # If pandas not available, return None
            return None


class LinkChecker:
    """Service for validating HTTP links with parallel execution and GET fallback."""

    def __init__(self, config: Config):
        """Initialize link checker.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.timeout = getattr(config, 'link_check_timeout', 10)
        self.max_workers = getattr(config, 'link_check_workers', 10)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; BlogLinkChecker/1.0)'
        }
        logger.info("✓ Link checker initialized")

    def check_url(self, url: str, method: str = 'HEAD') -> Tuple[bool, int, str]:
        """Check if URL is accessible with GET fallback.
        
        Args:
            url: URL to check
            method: HTTP method to use ('HEAD' or 'GET')
            
        Returns:
            Tuple of (is_valid, status_code, message)
        """
        if not url or not url.strip():
            return False, 0, "Empty URL"
        
        url = url.strip()
        
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            return False, 0, "Invalid URL scheme"
        
        # Try HEAD first
        if method == 'HEAD':
            try:
                response = requests.head(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    headers=self.headers
                )
                
                # If HEAD works and status is good, return success
                if response.status_code < 400:
                    return True, response.status_code, "OK"
                
                # If HEAD returns 405 (Method Not Allowed), fall back to GET
                if response.status_code == 405:
                    logger.debug(f"HEAD not allowed for {url}, trying GET")
                    return self.check_url(url, method='GET')
                
                # Other 4xx/5xx errors
                return False, response.status_code, "Error"
                
            except (requests.Timeout, requests.ConnectionError, requests.RequestException):
                # If HEAD fails, fall back to GET
                logger.debug(f"HEAD failed for {url}, trying GET")
                return self.check_url(url, method='GET')
            except Exception:
                # Any other exception during HEAD, try GET
                logger.debug(f"HEAD exception for {url}, trying GET")
                return self.check_url(url, method='GET')
        
        # GET method
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers=self.headers
            )
            
            is_valid = response.status_code < 400
            return is_valid, response.status_code, "OK" if is_valid else "Error"
            
        except requests.Timeout:
            return False, 0, "Timeout"
        except requests.ConnectionError:
            return False, 0, "Connection Error"
        except requests.RequestException as e:
            return False, 0, f"Request Error: {str(e)[:50]}"
        except Exception as e:
            return False, 0, f"Error: {str(e)[:50]}"

    def check_urls(
        self,
        urls: List[str],
        parallel: bool = True,
        max_workers: Optional[int] = None
    ) -> Dict[str, Tuple[bool, int, str]]:
        """Check multiple URLs with optional parallel execution.
        
        Args:
            urls: List of URLs to check
            parallel: Whether to check URLs in parallel
            max_workers: Number of worker threads (uses config default if None)
            
        Returns:
            Dict mapping URLs to check results
        """
        if not urls:
            return {}
        
        # Filter empty URLs
        urls = [url for url in urls if url and url.strip()]
        if not urls:
            return {}
        
        # Use parallel execution if enabled
        if parallel:
            workers = max_workers or self.max_workers
            results = {}
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # Submit all URL checks
                future_to_url = {
                    executor.submit(self.check_url, url): url
                    for url in urls
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        results[url] = result
                    except Exception as e:
                        logger.error(f"Exception checking {url}: {e}")
                        results[url] = (False, 0, f"Exception: {str(e)[:50]}")
            
            return results
        else:
            # Sequential execution
            results = {}
            for url in urls:
                results[url] = self.check_url(url)
                time.sleep(0.1)  # Rate limiting
            
            return results
