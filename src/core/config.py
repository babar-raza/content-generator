"""Unified Configuration System

Combines configuration from v5_1, v5_2, and v-ucop.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# CUDA detection
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

# Optional YAML import (lazy-fallback to avoid hard dependency at import time)
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass
class LLMConfig:
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "llama2"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class DatabaseConfig:
    chroma_db_path: str = "./chroma_db"
    embedding_model: str = "all-MiniLM-L6-v2"
    collection_name: str = "blog_knowledge"


@dataclass
class MeshConfig:
    enabled: bool = False
    registry_timeout: float = 2.0
    bid_strategy: str = "highest_score"
    cache_enabled: bool = True
    async_enabled: bool = True
    max_workers: int = 4
    batch_size: int = 5


@dataclass
class OrchestrationConfig:
    enabled: bool = False
    ops_console_host: str = "0.0.0.0"
    ops_console_port: int = 8080
    checkpoint_dir: str = "./checkpoints"
    workflow_dir: str = "./templates"
    hot_reload: bool = True


@dataclass
class Config:
    """Main configuration class."""
    
    # Paths
    config_dir: Path = field(default_factory=lambda: Path("./config"))
    templates_dir: Path = field(default_factory=lambda: Path("./templates"))
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    cache_dir: Path = field(default_factory=lambda: Path("./cache"))
    chroma_db_path: Path = field(default_factory=lambda: Path("./chroma_db"))
    ingestion_state_file: Path = field(default_factory=lambda: Path("./ingestion_state.json"))
    
    # Family detection (auto-detected from paths or set manually)
    family: str = "general"
    
    # Family name mapping (for API products)
    FAMILY_NAME_MAP = {
        'words': 'Aspose.Words',
        'pdf': 'Aspose.PDF',
        'cells': 'Aspose.Cells',
        'slides': 'Aspose.Slides',
        'email': 'Aspose.Email',
        'barcode': 'Aspose.BarCode',
        'diagram': 'Aspose.Diagram',
        'tasks': 'Aspose.Tasks',
        'ocr': 'Aspose.OCR',
        'note': 'Aspose.Note',
        'imaging': 'Aspose.Imaging',
        'zip': 'Aspose.ZIP',
    }
    
    # Device settings - CUDA auto-detection (overrideable by RUNTIME_DEVICE env var)
    device: str = field(default="auto")  # Will be resolved in post_init
    embedding_batch_size: int = 32

    # Sub-configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    mesh: MeshConfig = field(default_factory=MeshConfig)
    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)

    # LLM Provider Settings
    llm_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_rpm_limit: int = 15
    
    # Model Configuration
    gemini_model: str = "models/gemini-2.0-flash"
    openai_model: str = "gpt-4o-mini"
    
    # Ollama-specific settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_topic_model: str = "llama2"
    ollama_content_model: str = "qwen2.5"
    ollama_code_model: str = "qwen2.5-coder"
    
    llm_temperature: float = 0.7
    deterministic: bool = False
    cache_ttl: int = 86400  # 24 hours
    
    # Ollama Model Router settings
    enable_smart_routing: bool = True  # Enable intelligent model selection
    
    # GitHub settings
    gist_upload_enabled: bool = False
    github_gist_token: Optional[str] = None

    # Feature flags
    enable_mesh: bool = False
    enable_orchestration: bool = False
    enable_caching: bool = True
    enable_learning: bool = True

    # Performance
    request_timeout: int = 300
    max_retries: int = 3
    backoff_factor: float = 2.0

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Loaded data (lazy)
    _tone_config: Optional[Dict[str, Any]] = None
    _templates: Optional[Dict[str, Any]] = None
    _schemas: Optional[Dict[str, Any]] = None

    @staticmethod
    def detect_family_from_path(path: Path) -> str:
        """Detect API family from file path."""
        path_parts = [part.lower() for part in path.parts]
        
        for family_key in Config.FAMILY_NAME_MAP.keys():
            if family_key in path_parts:
                return family_key
        
        return "general"
    
    def __post_init__(self):
        """Resolve auto-detection fields after initialization."""
        # Auto-detect device if set to 'auto'
        if self.device == "auto":
            env_device = os.getenv("RUNTIME_DEVICE", "").lower()
            if env_device in ["cuda", "cpu"]:
                self.device = env_device
            else:
                # Auto-detect CUDA
                self.device = "cuda" if (TORCH_AVAILABLE and torch.cuda.is_available()) else "cpu"

    def load_from_env(self):
        """Load configuration from environment variables with smart defaults."""
        
        # LLM Provider - with auto-detection fallback
        env_provider = os.getenv("LLM_PROVIDER", "").upper()
        if env_provider in ["OLLAMA", "GEMINI", "OPENAI"]:
            self.llm_provider = env_provider
        else:
            # Auto-detect: Ollama (free) → Gemini (free tier) → OpenAI (paid)
            self.llm_provider = self._auto_detect_provider()
        
        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Store in llm sub-config for backwards compatibility
        self.llm.gemini_api_key = self.gemini_api_key
        self.llm.openai_api_key = self.openai_api_key
        self.llm.ollama_base_url = os.getenv("OLLAMA_BASE_URL", self.ollama_base_url)
        
        # Model Configuration
        self.gemini_model = os.getenv("GEMINI_MODEL", self.gemini_model)
        self.openai_model = os.getenv("OPENAI_MODEL", self.openai_model)
        self.gemini_rpm_limit = int(os.getenv("GEMINI_RPM_LIMIT", str(self.gemini_rpm_limit)))
        
        # Ollama Models
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", self.ollama_base_url)
        self.ollama_topic_model = os.getenv("OLLAMA_TOPIC_MODEL", self.ollama_topic_model)
        self.ollama_content_model = os.getenv("OLLAMA_CONTENT_MODEL", self.ollama_content_model)
        self.ollama_code_model = os.getenv("OLLAMA_CODE_MODEL", self.ollama_code_model)
        
        # Performance Settings
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", str(self.llm_temperature)))
        self.cache_ttl = int(os.getenv("CACHE_TTL", str(self.cache_ttl)))
        self.enable_smart_routing = os.getenv("ENABLE_SMART_ROUTING", "true").lower() == "true"
        
        # Database
        self.database.chroma_db_path = os.getenv("CHROMA_DB_PATH", self.database.chroma_db_path)

        # Feature Flags
        self.mesh.enabled = os.getenv("MESH_ENABLED", "false").lower() == "true"
        self.enable_mesh = self.mesh.enabled

        self.orchestration.enabled = os.getenv("ORCHESTRATION_ENABLED", "false").lower() == "true"
        self.enable_orchestration = self.orchestration.enabled
        
        self.enable_caching = os.getenv("ENABLE_CACHING", "true").lower() == "true"

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        
        # GitHub Gist
        self.gist_upload_enabled = os.getenv("GIST_UPLOAD_ENABLED", "false").lower() == "true"
        self.github_gist_token = os.getenv("GITHUB_GIST_TOKEN")
    
    def _auto_detect_provider(self) -> str:
        """Auto-detect available LLM provider.
        
        Priority: Ollama (free) → Gemini (free tier) → OpenAI (paid)
        
        Returns:
            Best available provider name
        """
        # 1. Try Ollama (free, local)
        try:
            import requests
            response = requests.get(
                f"{self.ollama_base_url}/api/tags",
                timeout=2
            )
            if response.status_code == 200:
                logger.info("✓ Auto-detected Ollama as LLM provider")
                return "OLLAMA"
        except Exception:
            pass
        
        # 2. Try Gemini (free tier, requires API key)
        if os.getenv("GEMINI_API_KEY"):
            logger.info("✓ Auto-detected Gemini as LLM provider (API key found)")
            return "GEMINI"
        
        # 3. Try OpenAI (paid, requires API key)
        if os.getenv("OPENAI_API_KEY"):
            logger.info("✓ Auto-detected OpenAI as LLM provider (API key found)")
            return "OPENAI"
        
        # 4. Default to Ollama (will need manual setup)
        logger.warning("⚠ No LLM provider detected, defaulting to Ollama")
        logger.warning("  Make sure Ollama is running or set GEMINI_API_KEY/OPENAI_API_KEY")
        return "OLLAMA"

    def load_tone_config(self) -> Dict[str, Any]:
        if self._tone_config is None:
            tone_file = self.config_dir / "tone.json"
            if tone_file.exists():
                try:
                    self._tone_config = json.loads(tone_file.read_text(encoding="utf-8"))
                except Exception as e:  # pragma: no cover
                    logger.warning("Failed to load tone.json: %s", e)
                    self._tone_config = {}
            else:
                self._tone_config = {}
        return self._tone_config

    def load_templates(self) -> Dict[str, Any]:
        if self._templates is not None:
            return self._templates

        templates: Dict[str, Any] = {}
        if yaml is None:
            logger.info("PyYAML not available at import time; skipping templates load until runtime.")
            self._templates = templates
            return templates

        try:
            for template_file in self.templates_dir.glob("*.yaml"):
                with open(template_file, "r", encoding="utf-8") as f:
                    templates[template_file.stem] = yaml.safe_load(f) or {}
        except Exception as e:  # pragma: no cover
            logger.warning("Failed to load templates: %s", e)
        self._templates = templates
        return templates

    def get_template(self, template_type: str) -> Dict[str, Any]:
        templates = self.load_templates()
        # naming convention: blog_templates, code_templates, frontmatter_templates, workflows
        return templates.get(f"{template_type}_templates", templates.get(template_type, {}))


# Schemas registry (loaded from config/agents.yaml when available)
SCHEMAS: Dict[str, Dict[str, Any]] = {}


def load_schemas(config: Config):
    """Load schemas from agents.yaml if available."""
    global SCHEMAS
    agents_file = config.config_dir / "agents.yaml"
    if not agents_file.exists():
        SCHEMAS = {}
        return
    try:
        if yaml is None:
            logger.info("PyYAML not available; cannot parse agents.yaml at this time.")
            SCHEMAS = {}
            return
        with open(agents_file, "r", encoding="utf-8") as f:
            agents_data = yaml.safe_load(f) or {}
            SCHEMAS = agents_data.get("schemas", {})
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to load schemas from agents.yaml: %s", e)
        SCHEMAS = {}


def load_config(config_file: Optional[str] = None) -> Config:
    """Load configuration from environment and optional config file.

    Args:
        config_file: Optional path to config file (e.g., 'config/main.yaml').

    Returns:
        Config instance with loaded settings.

    Raises:
        None.

    Preconditions:
        None.

    Postconditions:
        Config instance initialized and loaded from environment.

    Side Effects:
        SCHEMAS may be loaded if agents.yaml exists.

    I/O schema:
        - Input shape: config_file (str, optional).
        - Output shape: Config.

    Concurrency & performance:
        - Thread-safe: No shared state.
        - Performance: Environment variable access and optional file reads.

    Configuration:
        - Environment variables for config.
        - config_file for config directory override.

    External interactions:
        - File system reads for schemas.
    """
    config = Config()
    if config_file:
        config.config_dir = Path(config_file).parent
    config.load_from_env()
    load_schemas(config)
    return config


# ============================================================================
# CONSTANTS (from v5_1)
# ============================================================================

CSHARP_LICENSE_HEADER = """// Create an instance of the Metered class
Metered metered = new Metered();
// Set the metered key
string publicKey = "YourPublicKey";
string privateKey = "YourPrivateKey";
metered.SetMeteredKey(publicKey, privateKey);"""

# PROMPTS dictionary - loaded from templates
PROMPTS = {}

# FAILURE_STRATEGIES - error handling strategies
FAILURE_STRATEGIES = {
    "TimeoutError": [
        {"action": "increase_timeout", "params": {"multiplier": 2, "max": 30}},
        {"action": "switch_provider", "params": {"priority": ["OPENAI", "GEMINI", "OLLAMA"]}},
    ],
    "JSONParseError": [
        {"action": "enforce_json_mode", "params": {"strict": True}},
    ],
    "RateLimit": [
        {"action": "exponential_backoff", "params": {"max_attempts": 5}},
    ],
}


__all__ = [
    'Config', 'LLMConfig', 'DatabaseConfig', 'MeshConfig', 'OrchestrationConfig',
    'SCHEMAS', 'load_schemas', 'load_config', 'PROMPTS', 'CSHARP_LICENSE_HEADER', 'FAILURE_STRATEGIES'
]
# DOCGEN:LLM-FIRST@v4