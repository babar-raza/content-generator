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

# Early import attempts before logger is configured
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False
    # Will log warning after logger is configured

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    chromadb = None
    Settings = None
    HAS_CHROMADB = False

try:
    from pytrends.request import TrendReq
    HAS_PYTRENDS = True
except ImportError:
    TrendReq = None
    HAS_PYTRENDS = False
    
from src.core.config import Config
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

# Log warnings about missing dependencies
if not HAS_SENTENCE_TRANSFORMERS:
    logger.warning("sentence_transformers not available - using fallback embeddings")
if not HAS_CHROMADB:
    logger.warning("chromadb not available - database features disabled")
if not HAS_PYTRENDS:
    logger.warning("pytrends not available - trends features disabled")

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

        logger.info(f"✓ Saved LLM response to cache (output_len: {len(output)})")

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

            logger.info(f"✓ LLM Cache HIT (age: {age:.0f}s, provider: {provider or 'default'}, prompt_len: {len(prompt)})")

            return cached_output

        logger.info(f"✗ LLM Cache MISS (provider: {provider or 'default'}, prompt_len: {len(prompt)}), generating...")

        # Determine providers to try

        if provider:

            providers_to_try = [provider]

        else:

            providers_to_try = self.provider_priority

        # Try providers in order

        last_error = None

        for idx, prov in enumerate(providers_to_try):

            if idx > 0:
                logger.info(f"Attempting fallback provider #{idx + 1}: {prov}")

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

                        import google.generativeai as genai

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

                            # Only add schema if it has properties (Gemini requirement)
                            if json_schema and isinstance(json_schema, dict):
                                # Check if schema has properties or is just {"type": "object"}
                                if json_schema.get("properties") or json_schema.get("type") != "object":
                                    generation_config["response_schema"] = json_schema

                        # Build full prompt

                        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

                        # Log prompt length for debugging

                        logger.info(f"Gemini prompt length: {len(full_prompt)} chars")

                        # Try generation with retry only for non-rate-limit errors

                        max_attempts = 3

                        for attempt in range(max_attempts):

                            try:

                                gemini_model = genai.GenerativeModel(model_name=mapped_model,

                                    generation_config=generation_config

                                )

                                response = gemini_model.generate_content(full_prompt)

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

                                output = text
                                break

                            except Exception as e:

                                error_str = str(e)

                                # Check for rate limiting - immediately fail to trigger fallback

                                if "429" in error_str or "quota" in error_str.lower() or "Resource exhausted" in error_str:

                                    logger.warning(f"Gemini rate limit detected (attempt {attempt + 1}): {e}")

                                    logger.info("Falling back to next provider (Ollama) due to rate limit")

                                    # Don't retry, raise immediately to trigger fallback

                                    raise RuntimeError(f"Gemini rate limit exceeded: {e}")

                                logger.warning(f"Gemini generation error (attempt {attempt + 1}/{max_attempts}): {e}")

                                # Check for content filtering

                                if "safety" in error_str.lower() or "blocked" in error_str.lower():

                                    logger.error("Gemini content safety filter triggered")

                                    raise ValueError(f"Content blocked by Gemini safety filter: {e}")

                                if attempt == max_attempts - 1:

                                    raise

                                import time

                                time.sleep(2 ** attempt)

                        if 'output' not in locals():
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

                # Apply NO-MOCK validation before caching
                from src.services.services_fixes import NoMockGate
                no_mock_gate = NoMockGate()
                is_valid, reason = no_mock_gate.validate_response(output)
                
                if not is_valid:
                    logger.warning(f"Provider {prov} returned mock content: {reason}")
                    # Try next provider
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

        """Generate using Ollama with fallback to generate endpoint."""

        if not model:

            model = self.config.ollama_topic_model

        temp = self._effective_sampling(temperature)

        # Try chat endpoint first (preferred for newer Ollama)
        try:
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
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Fallback to generate endpoint for older Ollama versions
                logger.info("Chat endpoint not available, falling back to generate endpoint")
                
                # Build full prompt with system message
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                
                payload = {
                    "model": model,
                    "prompt": full_prompt,
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
                    "http://localhost:11434/api/generate",
                    json=payload,
                    timeout=timeout
                )
                
                response.raise_for_status()
                result = response.json()
                return result["response"]
            else:
                raise

    def _generate_gemini(

        self,

        prompt: str,

        system_prompt: Optional[str],

        json_mode: bool,

        temperature: Optional[float],

        model: Optional[str]

    ) -> str:

        """Generate using Gemini with rate limiting."""

        import google.generativeai as genai

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

        # OpenAI requires the word "json" in messages when using json_object format
        user_content = prompt
        if json_mode and "json" not in prompt.lower():
            user_content = f"{prompt}\n\nPlease respond in JSON format."
            
        messages.append({"role": "user", "content": user_content})

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
        if HAS_SENTENCE_TRANSFORMERS:
            self.model = SentenceTransformer(

                'sentence-transformers/all-MiniLM-L6-v2',

                device=config.device

            )

            self.cache: Dict[str, List[float]] = {}

            logger.info(f"Embedding model loaded on {config.device}")

            if config.device == "cuda":

                logger.info(f"Batch size for GPU: {config.embedding_batch_size}")
        else:
            self.model = None
            self.cache: Dict[str, List[float]] = {}
            logger.warning("EmbeddingService initialized without sentence_transformers - using dummy embeddings")

    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:

        # FIXED: Ensure return value is always a list of lists, never None

        if not texts:

            return []

        """Encode texts to embeddings with GPU acceleration."""
        
        import hashlib

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
            if self.model is None:
                # Fallback: generate dummy embeddings (random but consistent per text)
                import hashlib
                embeddings = []
                for text in uncached_texts:
                    # Create a deterministic embedding based on text hash
                    text_hash = hashlib.sha256(text.encode()).hexdigest()
                    # Convert hash to 384-dim vector (same as all-MiniLM-L6-v2)
                    embedding = [int(text_hash[i:i+2], 16) / 255.0 for i in range(0, min(len(text_hash), 192*2), 2)]
                    # Pad to 384 dimensions
                    embedding.extend([0.0] * (384 - len(embedding)))
                    embeddings.append(embedding)
            else:
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

                # Handle both numpy arrays and lists
                if hasattr(embedding, 'tolist'):
                    emb_list = embedding.tolist()
                else:
                    emb_list = embedding  # Already a list

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
        self.enabled = HAS_CHROMADB
        
        if not HAS_CHROMADB:
            logger.warning("DatabaseService initialized without chromadb - features disabled")
            self.clients = {}
            self.collections = {}
            self.db_paths = {}
            return
        
        # Get default family (defaults to 'general' if not set)
        self.default_family = getattr(config, 'family', 'general')
        
        db_base_path = Path(config.chroma_db_path)
        
        # Add batch method wrapper
        self.embedding_service.batch = lambda texts: self.embedding_service.encode(texts)
        
        # Store base path for dynamic collection creation
        self.db_base_path = db_base_path
        
        # Track created database paths and clients
        self.db_paths = {}
        self.clients = {}
        self.collections = {}
        
        # Don't initialize default family collections at startup - make it lazy
        # Collections will be created on-demand when actually needed
        # self._ensure_family_collections(self.default_family)
        
        logger.info(f"ChromaDB initialized (lazy mode) - collections will be created on demand")
    
    def _ensure_family_collections(self, family: str):
        """Ensure collections exist for a given family.
        
        Args:
            family: Family identifier (e.g., 'words', 'pdf', 'general')
        """
        sources = ["kb", "blog", "api"]
        
        for source in sources:
            collection_key = f"{source}-{family}"
            
            if collection_key not in self.collections:
                # Create database directory path
                db_path = self.db_base_path / collection_key
                db_path.mkdir(parents=True, exist_ok=True)
                
                # Create client if needed
                if collection_key not in self.clients:
                    self.clients[collection_key] = self._create_client(db_path)
                
                # Store path
                self.db_paths[collection_key] = db_path
                
                # Create/get collection
                self.collections[collection_key] = self._get_or_create_collection(
                    collection_key, collection_key, self.clients[collection_key]
                )
                
                logger.info(f"  Initialized collection: {collection_key} at {db_path}")
            
    def _create_client(self, path: Path):

        """Create a ChromaDB client."""
        
        if not HAS_CHROMADB:
            return None
        
        # Only use Settings if chromadb is available
        if Settings is not None:
            return chromadb.PersistentClient(
                path=str(path),
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            return chromadb.PersistentClient(path=str(path))

    def _get_or_create_collection(self, section: str, name: str, client=None):

        """Get or create a collection with semantic naming."""

        if client is None:
            client = self.clients.get(section)
            
        if client is None:
            raise ValueError(f"No client available for section: {section}")

        try:

            collection = client.get_collection(name=name)

            logger.debug(f"Loaded existing collection: {name}")

            return collection

        except KeyError as e:

            # Chroma 0.6.x reading an older sysdb emits KeyError: '_type'

            if "_type" in str(e):

                db_path = self.db_paths.get(section, self.db_base_path / name)

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

        ids: Optional[List[str]] = None,
        
        family: Optional[str] = None

    ):

        """Add documents to a collection.
        
        Args:
            source: Source type ('kb', 'blog', 'api')
            documents: List of document texts
            metadatas: Optional metadata for each document
            ids: Optional IDs for documents
            family: Family identifier (e.g., 'words', 'pdf'). If None, uses default.
        """
        
        # Use provided family or default
        if family is None:
            family = self.default_family
        
        # Ensure collections exist for this family
        self._ensure_family_collections(family)
        
        # Get collection key
        collection_key = f"{source}-{family}"

        if collection_key not in self.collections:

            raise ValueError(f"Collection not found: {collection_key}")

        collection = self.collections[collection_key]

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

                logger.info(f"All {len(documents)} documents already exist in {collection_key} (skipped)")

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

            logger.info(f"Added {total_added} documents to {collection_key} at {self.db_paths[collection_key]} ({skipped} duplicates skipped)")

        except Exception as e:

            logger.error(f"Error adding documents to {collection_key}: {e}")

            raise

    def query(

        self,

        source: str,

        query_text: str,

        top_k: int = 8,

        where: Optional[Dict] = None,
        
        family: Optional[str] = None

    ) -> Dict[str, Any]:

        """Query a collection.
        
        Args:
            source: Source type ('kb', 'blog', 'api')
            query_text: Text to query
            top_k: Number of results to return
            where: Optional filter conditions
            family: Family identifier. If None, uses default.
            
        Returns:
            Query results
        """
        
        # Use provided family or default
        if family is None:
            family = self.default_family
        
        # Ensure collections exist for this family
        self._ensure_family_collections(family)
        
        # Get collection key
        collection_key = f"{source}-{family}"

        if collection_key not in self.collections:

            raise ValueError(f"Collection not found: {collection_key}")

        collection = self.collections[collection_key]

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

        threshold: float = 0.25,
        
        family: Optional[str] = None

    ) -> Tuple[bool, float]:

        """Check if query is duplicate of existing document.
        
        Args:
            source: Source type
            query_text: Text to check
            threshold: Similarity threshold for duplicates
            family: Family identifier. If None, uses default.
            
        Returns:
            Tuple of (is_duplicate, similarity_score)
        """

        results = self.query(source, query_text, top_k=1, family=family)

        if not results['distances'] or not results['distances'][0]:

            return False, 0.0

        distance = results['distances'][0][0]

        similarity = 1.0 - distance

        is_duplicate = distance < threshold

        return is_duplicate, similarity

    def has_document(self, source: str, doc_id: str) -> bool:

        """Check if a document exists in collection.

        Args:

            source: Collection source (kb, blog, api)

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

            source: Collection source (kb, blog, api)

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

        for source in ["kb", "blog", "api"]:

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
            # TrendReq internally creates Retry objects, so pass integers
            # This avoids compatibility issues with different urllib3 versions
            self.pytrends = TrendReq(
                hl='en-US',
                tz=360,
                retries=2,
                backoff_factor=0.4,
                timeout=(10, 30),
                requests_args={'verify': True}  # Explicit requests args
            )

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

        logger.info(f"✓ Saved trends data to cache")

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

        # Guard: filter empty/blank keywords
        keywords = [k.strip() for k in keywords if k and k.strip()]
        if not keywords:
            logger.warning("No valid keywords provided for trends query, skipping")
            return None
        
        keywords = keywords[:5]

        cache_key = self._compute_query_hash(keywords, timeframe)

        if cache_key in self.cache:

            cached_data, cached_time = self.cache[cache_key]

            age = (datetime.now(timezone.utc) - cached_time).total_seconds()

            logger.info(f"✓ Trends Cache HIT (age: {age:.0f}s, keywords: {keywords})")

            return cached_data

        logger.info(f"✗ Trends Cache MISS (keywords: {keywords}), fetching from API...")

        # Get geo from config if available, default to US
        geo = getattr(self.config, 'trends_geo', 'US')

        try:

            self.pytrends.build_payload(

                keywords,

                timeframe=timeframe,

                geo=geo

            )

            interest_df = self.pytrends.interest_over_time()

            if interest_df.empty:
                # Retry with fallback timeframe
                if timeframe != 'now 7-d':
                    logger.info(f"Empty results for '{timeframe}', retrying with 'now 7-d'")
                    try:
                        self.pytrends.build_payload(keywords, timeframe='now 7-d', geo=geo)
                        interest_df = self.pytrends.interest_over_time()
                        if not interest_df.empty:
                            timeframe = 'now 7-d'  # Update for cache key
                    except Exception as retry_error:
                        logger.warning(f"Fallback timeframe also failed: {retry_error}")
                
                if interest_df.empty:
                    logger.warning(f"No trends data available for keywords: {keywords}")
                    return None

            data = {

                'keywords': keywords,

                'timeframe': timeframe,

                'data': interest_df.to_dict(orient='records')

            }

            self._save_to_cache(cache_key, data)

            return data

        except Exception as e:

            logger.warning(f"Trends API error: {e}")

            return None

    def get_related_queries(self, keyword: str) -> Optional[Dict[str, Any]]:

        """Get related queries for a keyword."""

        cache_key = self._compute_query_hash([keyword], 'related')

        if cache_key in self.cache:

            cached_data, cached_time = self.cache[cache_key]

            age = (datetime.now(timezone.utc) - cached_time).total_seconds()

            logger.info(f"✓ Trends Related Queries Cache HIT (age: {age:.0f}s, keyword: {keyword})")

            return cached_data

        logger.info(f"✗ Trends Related Queries Cache MISS (keyword: {keyword}), fetching from API...")

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
