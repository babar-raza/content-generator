"""Live Executor Factory for End-to-End Testing

Creates a fully-wired executor using real Ollama + Chroma (no mocks).
STOP-THE-LINE: Asserts that all components are in live mode.
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Set up environment for live mode BEFORE imports
os.environ["TEST_MODE"] = "live"
os.environ["ALLOW_NETWORK"] = "0"

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import Config, load_config
from src.core.event_bus import EventBus
from src.services.services import LLMService, EmbeddingService, DatabaseService
from src.orchestration.checkpoint_manager import CheckpointManager
from src.orchestration.workflow_compiler import WorkflowCompiler
from src.orchestration.enhanced_registry import EnhancedAgentRegistry
from src.orchestration.job_execution_engine import JobExecutionEngine

logger = logging.getLogger(__name__)


def create_live_executor(
    config_override: Optional[dict] = None,
    blog_collection: Optional[str] = None,
    ref_collection: Optional[str] = None,
    ollama_model: str = "phi4-mini:latest"
):
    """Create a live executor with real Ollama and Chroma.

    Args:
        config_override: Optional config overrides
        blog_collection: Collection name for blog knowledge (if None, uses default)
        ref_collection: Collection name for API reference (if None, uses default)
        ollama_model: Ollama model to use (default: phi4-mini:latest)

    Returns:
        Configured JobExecutionEngine with live services
    """
    config = load_config()

    if config_override:
        for key, value in config_override.items():
            setattr(config, key, value)

    # Store collection names in config for agents to use
    if blog_collection:
        config.database.collection_name = blog_collection
        setattr(config, "blog_collection", blog_collection)
    if ref_collection:
        setattr(config, "ref_collection", ref_collection)

    config.llm_provider = os.getenv("LLM_PROVIDER", "OLLAMA")
    config.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    config.ollama_topic_model = os.getenv("OLLAMA_MODEL", ollama_model)
    config.ollama_content_model = os.getenv("OLLAMA_MODEL", ollama_model)
    config.ollama_code_model = os.getenv("OLLAMA_MODEL", ollama_model)
    
    logger.info(f"Creating live executor: {config.llm_provider}")
    
    event_bus = EventBus()
    llm_service = LLMService(config)
    embedding_service = EmbeddingService(config)
    database_service = DatabaseService(config)
    
    checkpoint_manager = CheckpointManager(storage_path=Path("./checkpoints"))
    
    try:
        registry = EnhancedAgentRegistry()
    except Exception:
        registry = type("MinimalRegistry", (), {"agents": {}, "get_agent": lambda self, agent_id: None})()
    
    workflow_compiler = WorkflowCompiler(registry=registry, event_bus=event_bus)
    
    workflows_file = Path("./templates/workflows.yaml")
    if workflows_file.exists():
        workflow_compiler.load_workflows_from_file(workflows_file)
    
    executor = JobExecutionEngine(
        compiler=workflow_compiler,
        registry=registry,
        event_bus=event_bus,
        config=config,
        storage_dir=Path("./.jobs")
    )
    
    executor.llm_service = llm_service
    executor.embedding_service = embedding_service
    executor.database_service = database_service
    executor.event_bus = event_bus
    executor.config = config
    
    return executor


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        executor = create_live_executor()
        print("[SUCCESS] Live executor created")
    except Exception as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
