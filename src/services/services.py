# services.py

"""External service integrations.

Implements LLMService, EmbeddingService, DatabaseService, GistService,

LinkChecker, and TrendsService."""

import time
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone, timedelta
import threading
import os
import json
import hashlib
import logging
from pathlib import Path
import subprocess
import requests
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    class SentenceTransformer:
        def __init__(self, *args, **kwargs):
            raise ImportError("sentence-transformers not available. Install with: pip install sentence-transformers")
        def encode(self, *args, **kwargs):
            raise ImportError("sentence-transformers not available")
import chromadb
from chromadb.config import Settings
from pytrends.request import TrendReq
from src.core.config import Config
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

# Import Ollama Model Router
try:
    from src.services.model_router import OllamaModelRouter
    from src.utils.model_helper import initialize_model_helper
except ImportError:
    logger.warning("OllamaModelRouter not available, smart routing disabled")
    OllamaModelRouter = None
    initialize_model_helper = None

# Provider priority: ollama (free) > gemini (free tier) > openai (paid)
DEFAULT_PROVIDER_PRIORITY = ["OLLAMA", "GEMINI", "OPENAI"]

class LLMService:

    """Service for interacting with various LLM providers."""

    def _normalize_schema(self, schema: Any) -> Any:
        """Recursively rename unsupported JSON Schema keys.
        Converts ``maxLength`` keys to ``max_length`` to avoid provider errors."""
        if isinstance(schema, dict):
            normalized: Dict[str, Any] = {}
            for key, value in schema.items():
                new_key = 'max_length' if key == 'maxLength' else key
                normalized[new_key] = self._normalize_schema(value)
            return normalized
        if isinstance(schema, list):
            return [self._normalize_schema(item) for item in schema]
        return schema

    def __init__(self, config: Config):

        """Initialize LLM service with API key validation."""

        self.config = config

        self.cache: Dict[str, Tuple[str, datetime]] = {}

        self.cache_path = Path(config.cache_dir) / "responses.jsonl"

        self._load_cache()

        self.gemini_rate_limiter = GeminiRateLimiter(
            requests_per_minute=config.gemini_rpm_limit
        )

        # Provider priority: ollama (free) > gemini (free tier) > openai (paid)
        self.provider_priority = DEFAULT_PROVIDER_PRIORITY.copy()
        
        if config.llm_provider:
            if config.llm_provider in self.provider_priority:
                self.provider_priority.remove(config.llm_provider)
                self.provider_priority.insert(0, config.llm_provider)

        # Initialize Ollama Model Router
        enable_routing = getattr(config, 'enable_smart_routing', True)
        default_model = getattr(config, 'ollama_topic_model', 'llama2')
        
        if OllamaModelRouter and config.llm_provider == "OLLAMA":
            try:
                self.model_router = OllamaModelRouter(
                    enable_smart_routing=enable_routing,
                    default_model=default_model
                )
                logger.info("✓ Ollama Model Router initialized")
                
                # Initialize global model helper for agents
                if initialize_model_helper:
                    initialize_model_helper(self.model_router)
                    logger.info("✓ Model helper initialized for agents")
            except Exception as e:
                logger.warning(f"Could not initialize model router: {e}")
                self.model_router = None
        else:
            self.model_router = None

        # Validate API keys based on provider

        if config.llm_provider == "GEMINI":

            if not config.gemini_api_key:

                raise ValueError("GEMINI_API_KEY environment variable required but not set")

        if config.llm_provider == "OPENAI":

            if not config.openai_api_key:

                raise ValueError("OPENAI_API_KEY environment variable required but not set")

        if config.llm_provider == "OLLAMA":

            try:

                requests.get("http://localhost:11434/api/tags", timeout=5)

            except Exception as e:

                raise ConnectionError(f"Ollama not reachable at localhost:11434: {e}")

        # Provider priority

        self.provider_priority = ["OLLAMA", "GEMINI", "OPENAI"]

        if config.llm_provider:

            if config.llm_provider in self.provider_priority:

                self.provider_priority.remove(config.llm_provider)

                self.provider_priority.insert(0, config.llm_provider)

    def _effective_sampling(self, temperature: Optional[float]) -> float:

        if self.config.deterministic:

            return 0.0

        return temperature if temperature is not None else self.config.llm_temperature

    def _parse_ts(self, s: str) -> datetime:

        """Parse timestamp string and ensure it's timezone-aware.

        Args:

            s: ISO format timestamp string

        Returns:

            Timezone-aware datetime object"""

        ts = datetime.fromisoformat(s)

        # If naive (no timezone info), assume UTC

        if ts.tzinfo is None:

            ts = ts.replace(tzinfo=timezone.utc)

        return ts

    def _load_cache(self):

        """Load response cache from disk with proper datetime handling."""

        if not self.cache_path.exists():

            logger.debug(f"LLM cache not found at {self.cache_path}, starting fresh")

            return

        try:

            loaded_count = 0

            expired_count = 0

            with open(self.cache_path, 'r', encoding='utf-8', errors='replace') as f:

                for line_num, line in enumerate(f, 1):

                    try:

                        entry = json.loads(line)

                        cache_key = entry['input_hash']

                        output = entry['output']

                        # FIXED: Use helper method to parse timestamp correctly

                        timestamp = self._parse_ts(entry['timestamp'])

                        # Check if entry is still valid

                        now = datetime.now(timezone.utc)

                        age = now - timestamp

                        if age < timedelta(seconds=self.config.cache_ttl):

                            self.cache[cache_key] = (output, timestamp)

                            loaded_count += 1

                        else:

                            expired_count += 1

                    except (json.JSONDecodeError, KeyError, ValueError) as e:

                        logger.warning(f"Skipping invalid cache entry at line {line_num}: {e}")

                        continue

            if loaded_count > 0:

                logger.info(

                    f"Loaded {loaded_count} LLM cache entries "

                    f"({expired_count} expired entries skipped)"

                )

        except Exception as e:

            logger.error(f"Failed to load cache from {self.cache_path}: {e}")

            # Don't fail initialization, just start with empty cache

            self.cache = {}

    def _save_to_cache(self, input_hash: str, output: str):

        """Save response to cache with timezone-aware timestamp."""

        timestamp = datetime.now(timezone.utc)

        self.cache[input_hash] = (output, timestamp)

        try:

            # Ensure cache directory exists

            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_path, 'a', encoding='utf-8') as f:

                entry = {

                    'input_hash': input_hash,

                    'output': output,

                    'timestamp': timestamp.isoformat()

                }

                f.write(json.dumps(entry) + '\n')

        except Exception as e:

            logger.error(f"Failed to save to cache: {e}")

    def _compute_input_hash(self, prompt: str, schema: Optional[Dict] = None,

                           context: Optional[str] = None) -> str:

        """Compute SHA-256 hash of input."""

        hash_input = prompt

        if schema:

            hash_input += json.dumps(schema, sort_keys=True)

        if context:

            hash_input += context

        return hashlib.sha256(hash_input.encode()).hexdigest()

    def _map_model_for_provider(self, model: Optional[str], provider: str) -> str:

        """Map model names to provider-specific equivalents.

        Args:

            model: Original model name (possibly Ollama-specific)

            provider: Target provider (OLLAMA, GEMINI, OPENAI)

        Returns:

            Provider-appropriate model name"""

        if not model:

            # Use provider defaults

            if provider == "GEMINI":

                return "models/gemini-1.5-flash"

            elif provider == "OPENAI":

                return "gpt-4"

            else:  # OLLAMA

                return self.config.ollama_topic_model

        # If provider is OLLAMA, use as-is

        if provider == "OLLAMA":

            return model

        if provider == "GEMINI":

            return self.config.gemini_model

        # Map Ollama models to Gemini/OpenAI equivalents

        model_lower = model.lower()

        # Code models

        if "devstral" in model_lower or "code" in model_lower or "starcoder" in model_lower:

            if provider == "GEMINI":

                return "models/gemini-1.5-flash"  # Gemini's best for code

            else:  # OPENAI

                return "gpt-4"

        # Content/writing models

        if "qwen" in model_lower or "llama" in model_lower:

            if provider == "GEMINI":

                return "models/gemini-2.5-flash"

            else:  # OPENAI

                return "gpt-4o-mini"

        # Topic/general models

        if "mistral" in model_lower:

            if provider == "GEMINI":

                return "models/gemini-2.5-flash"

            else:  # OPENAI

                return "gpt-3.5-turbo"

        # SEO-specific: use gemini-2.5-flash if available

        if "gemini-2.5-flash" in model_lower:

            if provider == "GEMINI":

                return "models/gemini-2.0-flash-exp"  # Latest available

            else:  # OPENAI

                return "gpt-4"

        # Default fallback

        if provider == "GEMINI":

            return "models/gemini-1.5-flash"

        else:  # OPENAI

            return "gpt-4"

    def generate(

        self,

        prompt: str,

        system_prompt: Optional[str] = None,

        json_mode: bool = False,

        json_schema: Optional[Dict] = None,

        temperature: Optional[float] = None,

        model: Optional[str] = None,

        provider: Optional[str] = None,

        timeout: int = 60,
        
        task_context: Optional[str] = None,
        
        agent_name: Optional[str] = None

    ) -> str:

        """Generate text from LLM with provider fallback and model mapping.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            json_mode: Whether to request JSON output
            json_schema: Optional JSON schema for structured output
            temperature: Sampling temperature
            model: Specific model to use (optional)
            provider: Specific provider to use (optional)
            timeout: Request timeout in seconds
            task_context: Task description for smart model routing (NEW)
            agent_name: Name of calling agent for context (NEW)
            
        Returns:
            Generated text from the LLM
        """
        
        # Track call count for monitoring
        if not hasattr(self, '_call_count'):
            self._call_count = 0
        self._call_count += 1

        # Smart Model Routing for Ollama
        # If using Ollama and no specific model requested, use router
        if (not model and provider == "OLLAMA" and self.model_router and 
            task_context):
            try:
                routed_model = self.model_router.recommend_model(
                    task_description=task_context,
                    agent_name=agent_name
                )
                if routed_model:
                    model = routed_model
                    logger.debug(f"Router selected model: {routed_model} for task: {task_context[:50]}...")
            except Exception as e:
                logger.warning(f"Model routing failed: {e}, using default")

        # Normalize schema to remove unsupported keywords
        if json_schema:
            json_schema = self._normalize_schema(json_schema)
        # Enhanced cache key that includes schema and system prompt

        cache_components = [prompt]

        if system_prompt:

            cache_components.append(system_prompt)

        if json_schema:

            cache_components.append(json.dumps(json_schema, sort_keys=True))

        if json_mode:

            cache_components.append("JSON_MODE")

        cache_input = "||".join(cache_components)

        cache_key = self._compute_input_hash(cache_input)

        # Check cache FIRST

        if cache_key in self.cache:

            cached_output, cached_time = self.cache[cache_key]

            age = (datetime.now(timezone.utc) - cached_time).total_seconds()

            logger.info(f"✓ Cache HIT (age: {age:.0f}s, provider: {provider or 'default'})")

            return cached_output

        logger.debug(f"Cache MISS, generating with {provider or 'default'}")

        # Determine providers to try

        if provider:

            providers_to_try = [provider]

        else:

            providers_to_try = self.provider_priority

        # Try providers in order

        last_error = None

        for prov in providers_to_try:

            try:

                # Map model to provider-specific equivalent

                mapped_model = self._map_model_for_provider(model, prov)

                if prov == "OLLAMA":

                    try:

                        output = self._generate_ollama(

                            prompt, system_prompt, json_mode, temperature, mapped_model, timeout

                        )

                    except Exception as e:

                        logger.warning(f"Ollama failed, trying fallback provider: {e}")

                        # Try next provider in priority list

                        continue

                # Add this to LLMService.generate() in the GEMINI section:

                elif prov == "GEMINI":

                    try:

                        # Ensure genai is available for import

                        if not hasattr(genai, 'GenerativeModel'):

                            raise ImportError("google.generativeai module incomplete")

                        # Configure with retry logic

                        generation_config = {

                            "temperature": 0.7,

                            "top_p": 0.95,

                            "top_k": 40,

                            "max_output_tokens": 2048,

                        }

                        if json_mode:

                            generation_config["response_mime_type"] = "application/json"

                            if json_schema:

                                generation_config["response_schema"] = json_schema

                        # Build full prompt

                        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

                        # Log prompt length for debugging

                        logger.info(f"Gemini prompt length: {len(full_prompt)} chars")

                        # Try generation with exponential backoff

                        max_attempts = 3

                        for attempt in range(max_attempts):

                            try:

                                model = genai.GenerativeModel(model_name=mapped_model,

                                    generation_config=generation_config

                                )

                                response = model.generate_content(full_prompt)

                                # Validate response

                                if not response:

                                    logger.warning(f"Gemini returned None (attempt {attempt + 1})")

                                    if attempt < max_attempts - 1:

                                        import time

                                        time.sleep(2 ** attempt)  # Exponential backoff

                                        continue

                                    raise ValueError("Gemini returned None after all attempts")

                                if not hasattr(response, 'text'):

                                    logger.warning(f"Gemini response has no text attribute (attempt {attempt + 1})")

                                    if attempt < max_attempts - 1:

                                        import time

                                        time.sleep(2 ** attempt)

                                        continue

                                    raise ValueError("Gemini response has no text")

                                text = response.text

                                if not text or not text.strip():

                                    logger.warning(f"Gemini returned empty text (attempt {attempt + 1})")

                                    if attempt < max_attempts - 1:

                                        import time

                                        time.sleep(2 ** attempt)

                                        continue

                                    raise ValueError("Gemini returned empty text after all attempts")

                                # Log successful generation

                                logger.info(f"Gemini generated {len(text)} chars (attempt {attempt + 1})")

                                return text

                            except Exception as e:

                                logger.warning(f"Gemini generation error (attempt {attempt + 1}/{max_attempts}): {e}")

                                # Check for rate limiting

                                if "429" in str(e) or "quota" in str(e).lower():

                                    logger.warning("Gemini rate limit detected, increasing backoff")

                                    if attempt < max_attempts - 1:

                                        import time

                                        time.sleep(5 * (attempt + 1))  # Longer wait for rate limits

                                        continue

                                # Check for content filtering

                                if "safety" in str(e).lower() or "blocked" in str(e).lower():

                                    logger.error("Gemini content safety filter triggered")

                                    raise ValueError(f"Content blocked by Gemini safety filter: {e}")

                                if attempt == max_attempts - 1:

                                    raise

                                import time

                                time.sleep(2 ** attempt)

                        raise ValueError("Gemini generation failed after all retries")

                    except Exception as e:

                        logger.error(f"Gemini provider error: {e}")

                        raise RuntimeError(f"Gemini generation failed: {e}")

                elif prov == "OPENAI" and self.config.openai_api_key:

                    output = self._generate_openai(

                        prompt, system_prompt, json_mode, temperature, mapped_model

                    )

                else:

                    continue

                # Cache and return

                self._save_to_cache(cache_key, output)

                return _coerce_text(output)

            except Exception as e:

                logger.warning(f"Provider {prov} failed: {e}")

                last_error = e

                continue

        # All providers failed

        if last_error:

            raise last_error

        raise RuntimeError("All LLM providers failed")

    def _generate_ollama(

        self,

        prompt: str,

        system_prompt: Optional[str],

        json_mode: bool,

        temperature: Optional[float],

        model: Optional[str],

        timeout: int

    ) -> str:

        """Generate using Ollama."""

        if not model:

            model = self.config.ollama_topic_model

        temp = self._effective_sampling(temperature)

        messages = []

        if system_prompt:

            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {

            "model": model,

            "messages": messages,

            "stream": False,

            "options": {

                "temperature": temp,

                "top_p": self.config.llm_top_p if not self.config.deterministic else 1.0,

                "seed": self.config.global_seed

            }

        }

        if json_mode:

            payload["format"] = "json"

        response = requests.post(

            "http://localhost:11434/api/chat",

            json=payload,

            timeout=timeout

        )

        response.raise_for_status()

        result = response.json()

        return result["message"]["content"]

    def _generate_gemini(

        self,

        prompt: str,

        system_prompt: Optional[str],

        json_mode: bool,

        temperature: Optional[float],

        model: Optional[str]

    ) -> str:

        """Generate using Gemini with rate limiting."""

        try:
            import google.generativeai as genai
            GENAI_AVAILABLE = True
        except ImportError:
            GENAI_AVAILABLE = False
            class genai:
                @staticmethod
                def configure(*args, **kwargs):
                    pass
                class GenerativeModel:
                    def __init__(self, *args, **kwargs):
                        raise ImportError("google-generativeai not available")

        from google.generativeai.types import HarmCategory, HarmBlockThreshold

        if not model:

            model = "models/gemini-1.5-flash"

        # Apply rate limiting

        self.gemini_rate_limiter.wait_if_needed()

        genai.configure(api_key=self.config.gemini_api_key)

        # Configure safety settings

        safety_settings = {

            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,

            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,

            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,

            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,

        }

        gemini_model = genai.GenerativeModel(

            model_name=model,

            safety_settings=safety_settings

        )

        temp = self._effective_sampling(temperature)

        generation_config = genai.GenerationConfig(

            temperature=temp,

            top_p=self.config.llm_top_p,

        )

        # Build prompt with system context

        full_prompt = prompt

        if system_prompt:

            full_prompt = f"{system_prompt}\n\n{prompt}"

        try:

            # Record request

            self.gemini_rate_limiter.mark_request()

            # Synchronous call

            response = gemini_model.generate_content(

                contents=[full_prompt],

                generation_config=generation_config

            )

            # VALIDATE response

            if not hasattr(response, 'text'):

                raise ValueError("Gemini response missing 'text' attribute")

            response_text = response.text

            if not response_text or not response_text.strip():

                logger.warning("Gemini returned empty response, retrying once...")

                # Retry ONCE

                import time

                time.sleep(2)

                response = gemini_model.generate_content(

                    contents=[full_prompt],

                    generation_config=generation_config

                )

                if not hasattr(response, 'text') or not response.text or not response.text.strip():

                    raise ValueError(

                        f"Gemini returned empty response after retry. "

                        f"Prompt length: {len(full_prompt)}, "

                        f"Model: {model}"

                    )

                response_text = response.text

            logger.debug(f"Gemini response length: {len(response_text)} chars")

            return response_text

        except Exception as e:

            logger.error(f"Gemini generation failed: {type(e).__name__}: {e}")

            raise

    def _generate_openai(

        self,

        prompt: str,

        system_prompt: Optional[str],

        json_mode: bool,

        temperature: Optional[float],

        model: Optional[str]

    ) -> str:

        """Generate using OpenAI."""

        from openai import OpenAI

        client = OpenAI(api_key=self.config.openai_api_key)

        if not model:

            model = "gpt-4"

        temp = self._effective_sampling(temperature)

        messages = []

        if system_prompt:

            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        kwargs = {

            "model": model,

            "messages": messages,

            "temperature": temp,

            "top_p": self.config.llm_top_p,

            "seed": self.config.global_seed

        }

        if json_mode:

            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)

        return response.choices[0].message.content

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

        max_wait_seconds = 120  # ADD: Never wait more than 2 minutes

        wait_start = time.time()

        while True:

            # ADD: Timeout check

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

            time.sleep(min(wait_time, 10.0))  # ADD: Cap individual sleeps

    def mark_request(self):

        """Mark that a request was made."""

        with self._lock:

            self.request_times.append(time.time())

class EmbeddingService:

    """Service for generating embeddings with GPU support."""

    def __init__(self, config: Config):

        """Initialize embedding service with GPU support."""

        self.config = config

        # Initialize model with device

        self.model = SentenceTransformer(

            'sentence-transformers/all-MiniLM-L6-v2',

            device=config.device

        )

        self.cache: Dict[str, List[float]] = {}

        logger.info(f"Embedding model loaded on {config.device}")

        if config.device == "cuda":

            logger.info(f"Batch size for GPU: {config.embedding_batch_size}")

    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:

        # FIXED: Ensure return value is always a list of lists, never None

        if not texts:

            return []

        """Encode texts to embeddings with GPU acceleration."""

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

            batch_size = self.config.embedding_batch_size if self.config.device == "cuda" else 8

            embeddings = self.model.encode(

                uncached_texts,

                normalize_embeddings=normalize,

                show_progress_bar=len(uncached_texts) > 100,

                batch_size=batch_size,

                device=self.config.device

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

class DatabaseService:

    """Service for vector database operations using ChromaDB with semantic folder names."""

    def __init__(self, config: Config, embedding_service: EmbeddingService):
        """Initialize database service with semantic folder structure."""
        
        self.config = config
        self.embedding_service = embedding_service
        
        # Get family (defaults to 'general' if not set)
        family = getattr(config, 'family', 'general')
        
        db_base_path = Path(config.chroma_db_path)
        
        # Add batch method wrapper
        self.embedding_service.batch = lambda texts: self.embedding_service.encode(texts)
        
        # Create separate database directories for each section-family combination
        self.db_paths = {
            "kb": db_base_path / f"kb-{family}",
            "blog": db_base_path / f"blog-{family}",
            "api": db_base_path / f"api-{family}",
            "tutorial": db_base_path / f"tutorial-{family}",
            "docs": db_base_path / f"docs-{family}"
        }
        
        # Create all directories
        for path in self.db_paths.values():
            path.mkdir(parents=True, exist_ok=True)
        
        # Create separate ChromaDB clients for each section
        self.clients = {}
        self.collections = {}
        
        for section, path in self.db_paths.items():
            self.clients[section] = self._create_client(path)
            collection_name = f"{section}-{family}"
            self.collections[section] = self._get_or_create_collection(
                section, collection_name
            )
        
        logger.info(f"ChromaDB initialized for family: {family}")
        for section, path in self.db_paths.items():
            logger.info(f"  {section}: {path}")
            
    def _create_client(self, path: Path):

        """Create a ChromaDB client."""

        return chromadb.PersistentClient(

            path=str(path),

            settings=Settings(anonymized_telemetry=False)

        )

    def _get_or_create_collection(self, section: str, name: str):

        """Get or create a collection with semantic naming."""

        client = self.clients[section]

        try:

            collection = client.get_collection(name=name)

            logger.info(f"Loaded existing collection: {name} in {section}")

            return collection

        except KeyError as e:

            # Chroma 0.6.x reading an older sysdb emits KeyError: '_type'

            if "_type" in str(e):

                db_path = self.db_paths[section]

                logger.error(

                    f"Incompatible ChromaDB metadata for '{section}' at {db_path}. "

                    f"Run with --force-reingest to reset the database."

                )

                raise RuntimeError(

                    f"ChromaDB version mismatch detected.\n"

                    f"Solution: Delete '{db_path}' or run:\n"

                    f"  python main.py generate --kb-path <path> --force-reingest"

                ) from e

            raise

        except ValueError:

            # Collection doesn't exist, create it

            pass

        except Exception as e:

            if "does not exist" in str(e).lower():

                pass  # Expected, create new collection

            else:

                raise

        # Create new collection with compatible metadata

        try:

            collection = client.create_collection(

                name=name,

                metadata={

                    "hnsw:space": "cosine",

                    "family": self.config.family,

                    "section": section,

                    "created_at": datetime.now(timezone.utc).isoformat(),

                    "version": "0.6.0"  # ADD version tracking

                }

            )

            logger.info(f"Created new collection: {name} in {section}")

            return collection

        except Exception as e:

            logger.error(f"Failed to create collection {name}: {e}")

            raise

    def add_documents(

        self,

        source: str,

        documents: List[str],

        metadatas: Optional[List[Dict]] = None,

        ids: Optional[List[str]] = None

    ):

        """Add documents to a collection."""

        if source not in self.collections:

            self._ensure_collection(source)  # allow known aliases lazily

            # continue

        collection = self.collections[source]

        embeddings = self.embedding_service.encode(documents)

        if ids is None:

            ids = []

            for i, doc in enumerate(documents):

                # Create deterministic ID from content + metadata + index

                id_parts = [doc]

                if metadatas and i < len(metadatas):

                    id_parts.append(json.dumps(metadatas[i], sort_keys=True))

                id_parts.append(str(i))

                combined = "||".join(id_parts)

                doc_id = hashlib.sha256(combined.encode()).hexdigest()[:16]

                ids.append(doc_id)

        # Get existing IDs

        try:

            existing = collection.get(ids=ids)

            existing_ids = set(existing['ids']) if existing and 'ids' in existing else set()

            # Filter out existing documents

            new_docs = []

            new_embeddings = []

            new_metadatas = []

            new_ids = []

            for i, doc_id in enumerate(ids):

                if doc_id not in existing_ids:

                    new_docs.append(documents[i])

                    new_embeddings.append(embeddings[i])

                    new_metadatas.append((metadatas or [{}])[i])

                    new_ids.append(doc_id)

            if not new_docs:

                logger.info(f"All {len(documents)} documents already exist in {source} (skipped)")

                return

            # Add in batches

            batch_size = 40000

            total_added = 0

            for i in range(0, len(new_docs), batch_size):

                batch_docs = new_docs[i:i+batch_size]

                batch_embeddings = new_embeddings[i:i+batch_size]

                batch_metadatas = new_metadatas[i:i+batch_size]

                batch_ids = new_ids[i:i+batch_size]

                collection.add(

                    embeddings=batch_embeddings,

                    documents=batch_docs,

                    metadatas=batch_metadatas,

                    ids=batch_ids

                )

                total_added += len(batch_docs)

            skipped = len(documents) - len(new_docs)

            logger.info(f"Added {total_added} documents to {source} at {self.db_paths[source]} ({skipped} duplicates skipped)")

        except Exception as e:

            logger.error(f"Error adding documents to {source}: {e}")

            raise

    def query(

        self,

        source: str,

        query_text: str,

        top_k: int = 8,

        where: Optional[Dict] = None

    ) -> Dict[str, Any]:

        """Query a collection."""

        if source not in self.collections:

            self._ensure_collection(source)  # allow known aliases lazily

            # continue

        collection = self.collections[source]

        query_embedding = self.embedding_service.encode([query_text])[0]

        results = collection.query(

            query_embeddings=[query_embedding],

            n_results=top_k,

            where=where

        )

        return results

    def check_duplicate(

        self,

        source: str,

        query_text: str,

        threshold: float = 0.25

    ) -> Tuple[bool, float]:

        """Check if query is duplicate of existing document."""

        results = self.query(source, query_text, top_k=1)

        if not results['distances'] or not results['distances'][0]:

            return False, 0.0

        distance = results['distances'][0][0]

        similarity = 1.0 - distance

        is_duplicate = distance < threshold

        return is_duplicate, similarity

    def has_document(self, source: str, doc_id: str) -> bool:

        """Check if a document exists in collection.

        Args:

            source: Collection source (kb, blog, api, tutorial, docs)

            doc_id: Document ID

        Returns:

            True if document exists"""

        if source not in self.collections:

            return False

        try:

            collection = self.collections[source]

            result = collection.get(ids=[doc_id])

            return result and 'ids' in result and len(result['ids']) > 0

        except KeyError:

            return False

        except Exception as e:

            logger.debug(f"Document existence check failed for {doc_id}: {e}")

            return False

    def list_existing_ids(self, source: str, ids: List[str]) -> Set[str]:

        """        Return the subset of ids already present (batch lookup if backend supports).

        Args:

            source: Collection source (kb, blog, api, tutorial, docs)

            ids: List of document IDs to check

        Returns:

            Set of IDs that exist in the collection"""

        if source not in self.collections:

            return set()

        existing = set()

        collection = self.collections[source]

        try:

            # Batch check - more efficient than individual checks

            # Check in batches of 100 to avoid overwhelming ChromaDB

            batch_size = 100

            for i in range(0, len(ids), batch_size):

                batch_ids = ids[i:i+batch_size]

                result = collection.get(ids=batch_ids)

                if result and 'ids' in result:

                    existing.update(result['ids'])

        except Exception as e:

            logger.warning(f"Batch existence check failed, falling back to individual checks: {e}")

            # Fallback to individual checks

            for doc_id in ids:

                if self.has_document(source, doc_id):

                    existing.add(doc_id)

        return existing

    def get_collection_info(self) -> Dict[str, Any]:

        """Get information about collections and their paths."""

        info = {

            "family": self.config.family,

            "sections": {}

        }

        for source in ["kb", "blog", "api", "tutorial", "docs"]:

            try:

                collection = self.collections[source]

                count = collection.count()

                info["sections"][source] = {

                    "path": str(self.db_paths[source]),

                    "collection_name": collection.name,

                    "count": count,

                    "metadata": collection.metadata

                }

            except Exception as e:

                info["sections"][source] = {

                    "path": str(self.db_paths[source]),

                    "error": str(e)

                }

        return info

def _ensure_collection(self, source: str):

    """Ensure an in-memory collection container exists for the given source; idempotent and side-effect free."""

    if not hasattr(self, "_collections"):

        self._collections = set()

    self._collections.add(str(source))

    return True

    """Create collection lazily if it's a known alias and not present."""

    known = {'kb','blog'}

    if source in self.collections:

        return

    if source in known and source in self.db_paths:

        self.clients[source] = self._create_client(self.db_paths[source])

        family = getattr(self.config, 'family', 'general')

        name = f"{source}-{family}"

        self.collections[source] = self._get_or_create_collection(source, name)

class GistService:

    """Service for GitHub Gist operations."""

    def __init__(self, config: Config):

        """Initialize Gist service with token validation."""

        self.config = config

        if config.gist_upload_enabled and not config.github_gist_token:

            raise ValueError("GITHUB_GIST_TOKEN required when gist_upload_enabled=True")

        self.token = config.github_gist_token

        self.base_url = "https://api.github.com"

        self.headers = {

            "Authorization": f"token {self.token}",

            "Accept": "application/vnd.github.v3+json"

        } if self.token else {}

    def create_gist(

        self,

        files: Dict[str, str],

        description: str = "",

        public: bool = True

    ) -> Dict[str, Any]:

        """Create a GitHub Gist."""

        if not self.token:

            raise ValueError("GitHub token not configured")

        gist_files = {}

        for filename, content in files.items():

            gist_files[filename] = {"content": content}

        payload = {

            "description": description,

            "public": public,

            "files": gist_files

        }

        response = requests.post(

            f"{self.base_url}/gists",

            headers=self.headers,

            json=payload,

            timeout=30

        )

        response.raise_for_status()

        gist_data = response.json()

        urls = {

            "html_url": gist_data["html_url"],

            "raw_urls": {

                filename: file_data["raw_url"]

                for filename, file_data in gist_data["files"].items()

            }

        }

        result = {

            "gist_id": gist_data["id"],

            "urls": urls,

            "owner": gist_data.get("owner", {}).get("login", "")

        }

        logger.info(f"Created Gist: {result['gist_id']}")

        return result

    def delete_gist(self, gist_id: str):

        """Delete a Gist (for compensation)."""

        if not self.token:

            return

        try:

            response = requests.delete(

                f"{self.base_url}/gists/{gist_id}",

                headers=self.headers,

                timeout=30

            )

            response.raise_for_status()

            logger.info(f"Deleted Gist: {gist_id}")

        except Exception as e:

            logger.error(f"Failed to delete Gist {gist_id}: {e}")

    def generate_filename(self, topic_slug: str, extension: str = "cs") -> str:

        """Generate optimized filename for Gist."""

        base = topic_slug.replace("_", "-")

        filename = f"{base}.{extension}"

        min_len = self.config.gist_filename_min_length

        max_len = self.config.gist_filename_max_length

        if len(filename) < min_len:

            filename = f"{base}-demo.{extension}"

        if len(filename) > max_len:

            allowed_base_len = max_len - len(f".{extension}")

            base = base[:allowed_base_len]

            filename = f"{base}.{extension}"

        return filename

class LinkChecker:

    """Service for validating URLs."""

    def __init__(self, config: Config):

        """Initialize link checker."""

        self.config = config

        self.timeout = 10

    def validate_url(self, url: str) -> bool:

        """Validate a URL returns 200 OK."""

        try:

            response = requests.head(

                url,

                timeout=self.timeout,

                allow_redirects=True

            )

            if response.status_code == 200:

                return True

            response = requests.get(

                url,

                timeout=self.timeout,

                allow_redirects=True

            )

            return response.status_code == 200

        except Exception as e:

            logger.warning(f"URL validation failed for {url}: {e}")

            return False

    # KILO: LinkChecker.validate_urls — type-safe

    def validate_urls(self, urls: List[str]) -> Dict[str, bool]:

        """Validate multiple URLs safely."""

        results: Dict[str, bool] = {}

        for url in urls:

            if not isinstance(url, str) or not url.strip():

                logger.warning(f"Skipping non-string or empty URL entry: {repr(url)}")

                continue

            results[url] = self.validate_url(url)

        return results

class TrendsService:

    """Service for Google Trends data."""

    def __init__(self, config: Config):

        """Initialize trends service."""

        self.config = config

        try:

            self.pytrends = TrendReq(hl='en-US', tz=360)

        except ImportError:

            raise ImportError("pytrends library not installed. Run: pip install pytrends")

        self.cache: Dict[str, Tuple[Any, datetime]] = {}

        self.cache_path = config.cache_dir / "trends.jsonl"

        self._load_cache()

    def _parse_timestamp(self, timestamp_str: str) -> datetime:

        """Parse timestamp string and ensure it's timezone-aware.

        Args:

            timestamp_str: ISO format timestamp string

        Returns:

            Timezone-aware datetime object"""

        ts = datetime.fromisoformat(timestamp_str)

        # If naive (no timezone info), assume UTC

        if ts.tzinfo is None:

            ts = ts.replace(tzinfo=timezone.utc)

        return ts

    def _load_cache(self):

        """Load trends cache from disk with proper datetime handling."""

        if not self.cache_path.exists():

            logger.debug(f"Trends cache not found at {self.cache_path}, starting fresh")

            return

        try:

            loaded_count = 0

            expired_count = 0

            with open(self.cache_path, 'r', encoding='utf-8', errors='replace') as f:

                for line_num, line in enumerate(f, 1):

                    try:

                        entry = json.loads(line)

                        cache_key = entry['query_hash']

                        data = entry['data']

                        # FIXED: Use helper method to parse timestamp correctly

                        timestamp = self._parse_timestamp(entry['timestamp'])

                        # Check if entry is still valid (within 24 hours)

                        now = datetime.now(timezone.utc)

                        age = now - timestamp

                        if age < timedelta(hours=24):

                            self.cache[cache_key] = (data, timestamp)

                            loaded_count += 1

                        else:

                            expired_count += 1

                    except (json.JSONDecodeError, KeyError, ValueError) as e:

                        logger.warning(f"Skipping invalid cache entry at line {line_num}: {e}")

                        continue

            logger.info(

                f"Loaded {loaded_count} trends cache entries "

                f"({expired_count} expired entries skipped)"

            )

        except Exception as e:

            logger.error(f"Failed to load trends cache from {self.cache_path}: {e}")

            # Don't fail initialization, just start with empty cache

            self.cache = {}

    def _save_to_cache(self, query_hash: str, data: Any):

        """Save trends data to cache with timezone-aware timestamp."""

        timestamp = datetime.now(timezone.utc)

        self.cache[query_hash] = (data, timestamp)

        try:

            # Ensure cache directory exists

            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_path, 'a', encoding='utf-8') as f:

                entry = {

                    'query_hash': query_hash,

                    'data': data,

                    'timestamp': timestamp.isoformat()

                }

                f.write(json.dumps(entry) + '\n')

        except Exception as e:

            logger.error(f"Failed to save trends cache to {self.cache_path}: {e}")

    def _compute_query_hash(self, keywords: List[str], timeframe: str) -> str:

        """Compute hash of query parameters."""

        query_str = json.dumps({

            'keywords': sorted(keywords),

            'timeframe': timeframe

        }, sort_keys=True)

        return hashlib.sha256(query_str.encode()).hexdigest()

    def get_interest_over_time(

        self,

        keywords: List[str],

        timeframe: str = 'today 3-m'

    ) -> Optional[Dict[str, Any]]:

        """Get interest over time for keywords."""

        keywords = keywords[:5]

        cache_key = self._compute_query_hash(keywords, timeframe)

        if cache_key in self.cache:

            cached_data, _ = self.cache[cache_key]

            logger.debug("Cache hit for trends request")

            return cached_data

        try:

            self.pytrends.build_payload(

                keywords,

                timeframe=timeframe,

                geo='US'

            )

            interest_df = self.pytrends.interest_over_time()

            if interest_df.empty:

                return None

            data = {

                'keywords': keywords,

                'timeframe': timeframe,

                'data': interest_df.to_dict(orient='records')

            }

            self._save_to_cache(cache_key, data)

            return data

        except Exception as e:

            logger.error(f"Failed to fetch trends data: {e}")

            return None

    def get_related_queries(self, keyword: str) -> Optional[Dict[str, Any]]:

        """Get related queries for a keyword."""

        cache_key = self._compute_query_hash([keyword], 'related')

        if cache_key in self.cache:

            cached_data, _ = self.cache[cache_key]

            return cached_data

        try:

            self.pytrends.build_payload([keyword], geo='US')

            related = self.pytrends.related_queries()

            if not related or keyword not in related:

                return None

            data = {

                'keyword': keyword,

                'top': related[keyword]['top'].to_dict(orient='records') if related[keyword]['top'] is not None else [],

                'rising': related[keyword]['rising'].to_dict(orient='records') if related[keyword]['rising'] is not None else []

            }

            self._save_to_cache(cache_key, data)

            return data

        except Exception as e:

            logger.error(f"Failed to fetch related queries: {e}")

            return None

    def get_trending_searches(self, geo: str = 'united_states') -> Optional[List[str]]:

        """Get trending searches."""

        cache_key = self._compute_query_hash([geo], 'trending')

        if cache_key in self.cache:

            cached_data, _ = self.cache[cache_key]

            return cached_data

        try:

            trending_df = self.pytrends.trending_searches(pn=geo)

            if trending_df.empty:

                return None

            data = trending_df[0].head(20).tolist()

            self._save_to_cache(cache_key, data)

            return data

        except Exception as e:

            logger.error(f"Failed to fetch trending searches: {e}")

            return None

    def format_for_prompt(self, keywords: List[str]) -> str:

        """Format trends data for inclusion in LLM prompt."""

        output = ["Google Trends Data:"]

        interest_data = self.get_interest_over_time(keywords)

        if interest_data:

            output.append(f"\nInterest Over Time (last 3 months):")

            for kw in keywords:

                if kw in interest_data.get('data', [{}])[0]:

                    avg_interest = sum(

                        d.get(kw, 0) for d in interest_data['data']

                    ) / len(interest_data['data'])

                    output.append(f"  - {kw}: {avg_interest:.1f}/100 avg interest")

        if keywords:

            related = self.get_related_queries(keywords[0])

            if related and related.get('top'):

                output.append(f"\nRelated Queries for '{keywords[0]}':")

                for item in related['top'][:5]:

                    output.append(f"  - {item.get('query', 'N/A')}")

        return "\n".join(output)


# ============================================================================
# Service Fixes - NO-MOCK gate, PyTrends backoff, and error handling
# ============================================================================

# Mock/placeholder detection patterns
MOCK_PATTERNS = [
    r"Your Optimized Title Here",
    r"\{\{.*?\}\}",
    r"Compell(?:ing|)",
    r"\[PLACEHOLDER\]",
    r"Lorem ipsum",
    r"TODO:",
    r"FIXME:",
    r"Insert .* here",
    r"Add .* content",
    r"Write about",
    r"Describe .*",
    r"Example content",
    r"Sample text",
    r"Your .* here",
    r"Enter .* here",
    r"\.\.\.",  # Triple dots often indicate placeholder
    r"TBD",
    r"To be determined",
    r"Coming soon"
]

class NoMockGate:
    """Detector and rejector for mock/placeholder content."""
    
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in MOCK_PATTERNS]
        self.rejection_count = 0
    
    def contains_mock(self, text: str) -> bool:
        """Check if text contains mock/placeholder content."""
        if not text or len(text.strip()) < 10:
            return True  # Too short to be real content
        
        for pattern in self.patterns:
            if pattern.search(text):
                logger.warning(f"Mock content detected: {pattern.pattern}")
                self.rejection_count += 1
                return True
        
        return False
    
    def validate_response(self, response: Any) -> Tuple[bool, str]:
        """Validate LLM response for mock content.
        
        Returns:
            (is_valid, reason) tuple
        """
        if response is None:
            return False, "Response is None"
        
        # Check string responses
        if isinstance(response, str):
            if self.contains_mock(response):
                return False, "Contains mock/placeholder content"
            return True, ""
        
        # Check dict responses (JSON)
        if isinstance(response, dict):
            for key, value in response.items():
                if isinstance(value, str) and self.contains_mock(value):
                    return False, f"Field '{key}' contains mock content"
            return True, ""
        
        # Check list responses
        if isinstance(response, list):
            for idx, item in enumerate(response):
                if isinstance(item, str) and self.contains_mock(item):
                    return False, f"Item {idx} contains mock content"
            return True, ""
        
        return True, ""


class SEOSchemaGate:
    """Enforces and normalizes SEO schema requirements."""
    
    REQUIRED_FIELDS = ['title', 'seoTitle', 'description', 'tags', 'keywords', 'slug']
    
    @staticmethod
    def coerce_and_fill(meta: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce and fill missing SEO fields.
        
        Args:
            meta: Raw metadata dictionary
            
        Returns:
            Normalized dictionary with all required fields
        """
        from src.engine.slug_service import slugify
        
        # Handle nested structures
        if 'metadata' in meta and isinstance(meta['metadata'], dict):
            meta = meta['metadata']
        if 'data' in meta and isinstance(meta['data'], dict):
            if 'metadata' in meta['data']:
                meta = meta['data']['metadata']
        
        normalized = {}
        
        # Map synonyms to standard field names
        field_mappings = {
            'title': ['title', 'articleTitle', 'post_title', 'postTitle'],
            'seoTitle': ['seoTitle', 'seo_title', 'metaTitle', 'meta_title', 'title_tag'],
            'description': ['description', 'meta_description', 'metaDescription', 'seo_description', 'excerpt'],
            'tags': ['tags', 'tag', 'post_tags', 'categories'],
            'keywords': ['keywords', 'keyword', 'seo_keywords', 'search_keywords'],
            'slug': ['slug', 'url_slug', 'permalink', 'url'],
        }
        
        # Extract values using field mappings
        for target_field, possible_sources in field_mappings.items():
            for source in possible_sources:
                if source in meta:
                    value = meta[source]
                    
                    # Convert tags/keywords to lists if they're strings
                    if target_field in ['tags', 'keywords']:
                        if isinstance(value, str):
                            # Split by comma, semicolon, or pipe
                            value = [v.strip() for v in re.split(r'[,;|]', value) if v.strip()]
                        elif not isinstance(value, list):
                            value = []
                    
                    normalized[target_field] = value
                    break
        
        # Ensure title exists
        if 'title' not in normalized or not normalized['title']:
            if 'seoTitle' in normalized:
                normalized['title'] = normalized['seoTitle']
            else:
                normalized['title'] = 'Untitled Post'
        
        # Ensure seoTitle exists (truncate if needed)
        if 'seoTitle' not in normalized or not normalized['seoTitle']:
            title = normalized['title']
            if len(title) > 60:
                # Truncate at word boundary
                truncated = title[:60]
                last_space = truncated.rfind(' ')
                if last_space > 40:
                    title = truncated[:last_space]
                else:
                    title = truncated
            normalized['seoTitle'] = title
        
        # Ensure description exists
        if 'description' not in normalized or not normalized['description']:
            normalized['description'] = f"Learn about {normalized['title']} - comprehensive guide and tutorial."
        
        # Ensure tags and keywords are lists
        for field in ['tags', 'keywords']:
            if field not in normalized:
                normalized[field] = []
            elif not isinstance(normalized[field], list):
                normalized[field] = []
        
        # Auto-generate slug if missing
        if 'slug' not in normalized or not normalized['slug']:
            normalized['slug'] = slugify(normalized['title'])
            logger.info(f"Auto-generated slug: {normalized['slug']}")
        
        # Validate slug format (lowercase, hyphens only)
        slug = normalized['slug']
        slug = re.sub(r'[^a-z0-9-]', '-', slug.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        if not slug:
            slug = 'untitled-post'
        normalized['slug'] = slug
        
        return normalized


class PrerequisitesNormalizer:
    """Normalizes prerequisites field to always be a list."""
    
    @staticmethod
    def normalize(value: Any) -> List[str]:
        """Normalize prerequisites to a list of strings.
        
        Args:
            value: Raw prerequisites value (None, str, list, etc.)
            
        Returns:
            List of prerequisite strings (may be empty)
        """
        if value is None:
            return []
        
        if isinstance(value, str):
            # Handle comma-separated strings
            if ',' in value:
                return [v.strip() for v in value.split(',') if v.strip()]
            # Single prerequisite
            return [value.strip()] if value.strip() else []
        
        if isinstance(value, list):
            # Filter and convert to strings
            result = []
            for item in value:
                if item is not None:
                    str_item = str(item).strip()
                    if str_item:
                        result.append(str_item)
            return result
        
        # Fallback for other types
        try:
            str_value = str(value).strip()
            return [str_value] if str_value else []
        except:
            return []


class PyTrendsGuard:
    """Wrapper for PyTrends with retry logic and fallback."""
    
    def __init__(self, max_retries: int = 3, backoff: float = 2.0):
        self.max_retries = max_retries
        self.backoff = backoff
    
    def safe_fetch(self, query: str, fetch_func, fallback_value: Any = None) -> Any:
        """Safely fetch trends data with retries and fallback.
        
        Args:
            query: Search query
            fetch_func: Function to call for fetching
            fallback_value: Value to return on failure
            
        Returns:
            Fetched data or fallback value
        """
        delay = 1.0
        
        for attempt in range(self.max_retries):
            try:
                result = fetch_func(query)
                logger.info(f"PyTrends fetch successful for '{query}'")
                return result
            except Exception as e:
                logger.warning(f"PyTrends attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= self.backoff
                else:
                    # Final attempt failed, return fallback
                    logger.warning(f"PyTrends failed after {self.max_retries} attempts, using fallback")
                    if fallback_value is None:
                        fallback_value = {
                            "query": query,
                            "score": 50,  # Neutral score
                            "note": "fallback_due_to_error",
                            "trending": False
                        }
                    return fallback_value


class TopicIdentificationFallback:
    """Fallback logic for topic identification."""
    
    @staticmethod
    def ensure_topic(topic: Any) -> Dict[str, Any]:
        """Ensure topic has required fields with fallbacks.
        
        Args:
            topic: Raw topic data
            
        Returns:
            Normalized topic dictionary with title and slug
        """
        from src.engine.slug_service import slugify
        
        if not isinstance(topic, dict):
            topic = {}
        
        # Ensure title exists
        if 'title' not in topic or not topic.get('title'):
            # Try alternative fields
            title = (
                topic.get('name') or
                topic.get('topic') or
                topic.get('subject') or
                'Untitled Topic'
            )
            topic['title'] = title
            logger.warning(f"Topic missing title, using fallback: {title}")
        
        # Ensure slug exists
        if 'slug' not in topic or not topic.get('slug'):
            topic['slug'] = slugify(topic['title'])
            logger.info(f"Auto-generated topic slug: {topic['slug']}")
        
        # Ensure description exists
        if 'description' not in topic:
            topic['description'] = f"Content about {topic['title']}"
        
        return topic


class BlogSwitchPolicy:
    """Enforces blog switch output policy."""
    
    @staticmethod
    def get_output_path(config, slug: str) -> str:
        """Get the correct output path based on blog_switch policy.
        
        Args:
            config: Config object with blog_switch setting
            slug: Content slug
            
        Returns:
            Full path string for output file
        """
        from pathlib import Path
        
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if config.blog_switch:
            # Blog ON: ./output/{slug}/index.md
            slug_dir = output_dir / slug
            slug_dir.mkdir(parents=True, exist_ok=True)
            return str(slug_dir / "index.md")
        else:
            # Blog OFF: ./output/{slug}.md
            return str(output_dir / f"{slug}.md")


class RunToResultGuarantee:
    """Ensures output is always produced even on partial failures."""
    
    @staticmethod
    def create_minimal_document(topic: str = "Untitled", slug: str = "untitled") -> str:
        """Create a minimal but valid markdown document.
        
        Args:
            topic: Topic title
            slug: URL slug
            
        Returns:
            Minimal markdown document with frontmatter
        """
        frontmatter = {
            "title": topic,
            "seoTitle": topic,
            "description": f"Information about {topic}",
            "tags": [],
            "keywords": [],
            "slug": slug,
            "date": datetime.now().isoformat(),
            "author": "System",
            "prerequisites": [],
            "draft": True,
            "note": "Generated as fallback due to processing errors"
        }
        
        content = f"""---
{json.dumps(frontmatter, indent=2)}
---

# {topic}

## Introduction

This document provides information about {topic}.

## Overview

*Content is being generated. This is a placeholder document created to ensure output availability.*

## Key Points

- Topic: {topic}
- Status: Draft
- Further content to be added

## Conclusion

This document will be updated with more comprehensive content.

---
*Note: This is a minimal document generated due to processing constraints. Full content generation is pending.*
"""
        return content


def apply_llm_service_fixes(llm_service_class):
    """Apply NO-MOCK gate and other fixes to LLMService class."""
    
    # Store original generate method
    original_generate = llm_service_class.generate
    
    # Create NO-MOCK gate instance
    no_mock_gate = NoMockGate()
    
    def generate_with_validation(self, prompt: str, schema: Optional[Dict] = None, **kwargs):
        """Enhanced generate with NO-MOCK validation and retries."""
        max_attempts = kwargs.pop('max_attempts', 3)
        
        for attempt in range(max_attempts):
            try:
                # Call original generate
                response = original_generate(self, prompt, schema, **kwargs)
                
                # Validate response for mock content
                is_valid, reason = no_mock_gate.validate_response(response)
                
                if is_valid:
                    return response
                
                logger.warning(f"Attempt {attempt + 1}: Invalid response - {reason}")
                
                # Try with stricter prompt on retry
                if attempt < max_attempts - 1:
                    prompt = f"IMPORTANT: Provide real, specific content. No placeholders, examples, or generic text.\n\n{prompt}"
                    time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Generate attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    raise
        
        # All attempts failed
        raise ValueError(f"Failed to generate valid content after {max_attempts} attempts (mock content detected)")
    
    # Replace method
    llm_service_class.generate = generate_with_validation
    
    return llm_service_class
