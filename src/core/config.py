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
    default_pipeline: list = field(default_factory=lambda: [
        "identify_topic", 
        "generate_seo",
        "dup_check",
        "build_frontmatter",
        "assemble_content",
        "write_output"
    ])


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
    api_dir: Path = field(default_factory=lambda: Path("./data/docs"))
    blog_dir: Path = field(default_factory=lambda: Path("./data/blog"))
    
    # NEW: Blog Switch Policy
    blog_switch: bool = field(default=True)  # ON = ./output/{slug}/index.md, OFF = ./output/{slug}.md
    
    # Family detection (auto-detected from paths or set manually)
    family: str = "general"
    company_name: str = "Company"
    
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
    
    # Content path patterns for family detection
    # These patterns help detect family from various content source paths
    CONTENT_PATH_PATTERNS = {
        'docs': r'(?:content/)?docs\.aspose\.net/([^/]+)/(?:en/)?',
        'kb': r'(?:content/)?kb\.aspose\.net/([^/]+)/(?:en/)?',
        'tutorial': r'(?:content/)?tutorial\.aspose\.net/([^/]+)/(?:en/)?',
        'reference': r'(?:content/)?reference\.aspose\.net/([^/]+)/(?:en/)?',
        'blog': r'(?:content/)?blog\.aspose\.net/([^/]+)/?',
    }
    
    # Fallback pattern: look for family names anywhere in path
    FAMILY_IN_PATH_PATTERN = r'/({})(?:/|$)'.format('|'.join(FAMILY_NAME_MAP.keys()))
    
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
    gemini_model: str = "models/gemini-2.5-flash"
    openai_model: str = "gpt-4o-mini"
    
    # Ollama-specific settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_topic_model: str = "llama2"
    ollama_content_model: str = "qwen2.5"
    ollama_code_model: str = "qwen2.5-coder"
    
    llm_temperature: float = 0.7
    llm_top_p: float = 0.95
    deterministic: bool = False
    global_seed: Optional[int] = None
    cache_ttl: int = 86400  # 24 hours
    
    # Text chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Duplication detection settings
    chroma_distance_threshold: float = 0.5
    
    # RAG settings
    rag_top_k: int = 5
    
    # Template settings
    active_blog_template: str = "blog"
    PREREQUISITES_TEMPLATE = """## Prerequisites

* Visual Studio 2019 or later
* .NET 6.0+ or .NET Framework 4.6.2+
* {family_name} for .NET installed (NuGet)

```shell
PM> Install-Package Aspose.{package_name}
```"""
    
    # Workflow settings
    warnings_as_errors: bool = False
    
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
    
    # Dynamic attributes (set at runtime)
    resilience_manager: Optional[Any] = None
    
    @property
    def tone_config(self) -> Dict[str, Any]:
        """Lazy load tone config."""
        if self._tone_config is None:
            tone_file = self.config_dir / "tone.json"
            if tone_file.exists():
                import json
                with open(tone_file, 'r') as f:
                    self._tone_config = json.load(f)
            else:
                self._tone_config = {}
        return self._tone_config
    
    @property
    def templates(self) -> Dict[str, Any]:
        """Lazy load templates."""
        if self._templates is None:
            self._templates = {}
        return self._templates
    
    def get_output_path(self, slug: str) -> Path:
        """Get the correct output path based on blog_switch policy."""
        if self.blog_switch:
            # Blog ON: ./output/{slug}/index.md
            dir_path = Path(self.output_dir) / slug
            dir_path.mkdir(parents=True, exist_ok=True)
            return dir_path / "index.md"
        else:
            # Blog OFF: ./output/{slug}.md
            return Path(self.output_dir) / f"{slug}.md"

    @staticmethod
    def detect_family_from_path(path: Path) -> str:
        """Detect API family from file path using configured patterns.
        
        Tries multiple detection strategies:
        1. Aspose.net path patterns (docs, kb, tutorial, reference, blog)
        2. Direct family name in path parts
        3. Pattern matching with regex
        
        Args:
            path: Path to analyze for family detection
            
        Returns:
            Family key (e.g., 'words', 'pdf') or 'general' if not detected
        """
        import re
        
        path_str = str(path).replace('\\', '/')
        
        # Strategy 1: Try content path patterns
        for source_type, pattern in Config.CONTENT_PATH_PATTERNS.items():
            match = re.search(pattern, path_str, re.IGNORECASE)
            if match:
                family = match.group(1).lower()
                if family in Config.FAMILY_NAME_MAP:
                    return family
        
        # Strategy 2: Check path parts directly
        path_parts = [part.lower() for part in path.parts]
        for family_key in Config.FAMILY_NAME_MAP.keys():
            if family_key in path_parts:
                return family_key
        
        # Strategy 3: Regex pattern match in full path
        pattern = Config.FAMILY_IN_PATH_PATTERN
        match = re.search(pattern, path_str, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        
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
    
    def get_frontmatter_template(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Load frontmatter template with placeholder replacement.
        
        Args:
            name: Optional template name ('default', 'tutorial', 'api_reference').
                  If None, uses 'default'.
        
        Returns:
            Template dictionary with {family} and {company} placeholders replaced.
        """
        templates = self.load_templates()
        frontmatter_templates = templates.get("frontmatter_templates", {})
        
        if not frontmatter_templates:
            # Fallback if template file is missing
            return {
                'author': 'Babar Raza',
                'draft': True,
                'categories': [f'Aspose.{self.family} Plugin Family'],
            }
        
        # Get the specified template or fall back to default
        if name and name in frontmatter_templates:
            template = frontmatter_templates[name]
        elif 'default' in frontmatter_templates:
            template = frontmatter_templates['default']
        else:
            # Use first available template
            template = next(iter(frontmatter_templates.values()), {})
        
        # Replace placeholders
        def replace_placeholders(value):
            if isinstance(value, str):
                return value.replace('{family}', self.family).replace('{company}', self.company_name)
            elif isinstance(value, list):
                return [replace_placeholders(item) for item in value]
            elif isinstance(value, dict):
                return {k: replace_placeholders(v) for k, v in value.items()}
            return value
        
        return replace_placeholders(template)


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

def load_prompts():
    """Load prompts from templates/prompts.yaml"""
    import yaml
    from pathlib import Path
    
    prompts_file = Path(__file__).parent.parent.parent / "templates" / "prompts.yaml"
    if prompts_file.exists():
        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                loaded_prompts = yaml.safe_load(f)
                if loaded_prompts:
                    PROMPTS.update(loaded_prompts)
                    import logging
                    logging.getLogger(__name__).info(f"✓ Loaded {len(loaded_prompts)} prompt templates")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not load prompts: {e}")
    else:
        import logging
        logging.getLogger(__name__).warning(f"Prompts file not found: {prompts_file}")

# Load prompts on module import
load_prompts()

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


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or environment.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Configured Config instance
    """
    config = Config()
    
    # Load from environment variables
    if os.getenv('GEMINI_API_KEY'):
        config.gemini_api_key = os.getenv('GEMINI_API_KEY')
    if os.getenv('OPENAI_API_KEY'):
        config.openai_api_key = os.getenv('OPENAI_API_KEY')
    if os.getenv('OLLAMA_BASE_URL'):
        config.ollama_base_url = os.getenv('OLLAMA_BASE_URL')
    if os.getenv('OLLAMA_MODEL'):
        config.ollama_topic_model = os.getenv('OLLAMA_MODEL')
    
    # Set provider based on available keys
    if config.ollama_base_url:
        config.llm_provider = "OLLAMA"
    elif config.gemini_api_key:
        config.llm_provider = "GEMINI"
    elif config.openai_api_key:
        config.llm_provider = "OPENAI"
    
    return config


__all__ = [
    'Config', 'LLMConfig', 'DatabaseConfig', 'MeshConfig', 'OrchestrationConfig',
    'SCHEMAS', 'load_schemas', 'PROMPTS', 'CSHARP_LICENSE_HEADER', 'FAILURE_STRATEGIES',
    'load_config'
]
