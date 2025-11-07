"""Launch UCOP Web UI with integrated job execution engine."""

import sys
import asyncio
import uvicorn
import logging
import threading
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core import Config, EventBus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_execution_engine(config: Config, event_bus: EventBus):
    """Initialize the job execution engine."""
    try:
        # Initialize GPU manager first
        from src.engine.device import get_gpu_manager
        gpu_manager = get_gpu_manager()
        device = gpu_manager.choose_device("auto")
        logger.info(f"✓ Device selected: {device} ({gpu_manager.detection_reason})")
        
        # Validate LLM configuration
        llm_provider = getattr(config, 'llm_provider', None)
        if not llm_provider:
            logger.warning("⚠ No LLM provider configured!")
            logger.warning("  Set environment variable: LLM_PROVIDER=ollama|gemini|openai")
            logger.warning("  Jobs will fail without LLM configuration")
        else:
            logger.info(f"✓ LLM Provider: {llm_provider}")
            # Check for API keys if needed
            if llm_provider == 'gemini':
                if not getattr(config, 'gemini_api_key', None):
                    logger.error("✗ GEMINI_API_KEY not set!")
            elif llm_provider == 'openai':
                if not getattr(config, 'openai_api_key', None):
                    logger.error("✗ OPENAI_API_KEY not set!")
            elif llm_provider == 'ollama':
                ollama_url = getattr(config, 'ollama_base_url', 'http://localhost:11434')
                logger.info(f"  Ollama URL: {ollama_url}")
                # Check if Ollama is actually running
                try:
                    import requests
                    response = requests.get(f"{ollama_url}/api/tags", timeout=2)
                    if response.status_code == 200:
                        logger.info("✓ Ollama service is running")
                    else:
                        logger.warning(f"⚠ Ollama returned status {response.status_code}")
                except Exception as e:
                    logger.error(f"✗ Ollama service not accessible at {ollama_url}")
                    logger.error(f"  Error: {e}")
                    logger.error("  Please start Ollama with: ollama serve")
                    logger.error("  Jobs will fall back to Gemini/OpenAI if configured")
        
        from src.orchestration.checkpoint_manager import CheckpointManager
        from src.orchestration.workflow_compiler import WorkflowCompiler
        from src.orchestration.job_execution_engine import JobExecutionEngine
        
        # Create checkpoint manager
        checkpoint_manager = CheckpointManager(
            storage_dir=Path("./checkpoints")
        )
        logger.info("✓ Checkpoint manager initialized")
        
        # Create a simple registry for workflow compiler
        # The registry would normally be the full agent registry, but we'll create a minimal one
        from src.orchestration.enhanced_registry import EnhancedAgentRegistry
        
        # Create necessary services for agents
        try:
            from src.services.services import DatabaseService, EmbeddingService, LLMService
            
            llm_service = LLMService(config)
            embedding_service = EmbeddingService(config)
            database_service = DatabaseService(config, embedding_service)
            logger.info("✓ Created agent services")
        except Exception as e:
            logger.error(f"Could not create all services: {e}", exc_info=True)
            logger.error("This will prevent agents from being instantiated")
            database_service = None
            embedding_service = None
            llm_service = None
        
        try:
            registry = EnhancedAgentRegistry(
                config=config,
                event_bus=event_bus,
                database_service=database_service,
                embedding_service=embedding_service,
                llm_service=llm_service
            )
            logger.info("✓ Agent registry initialized")
        except Exception as e:
            logger.warning(f"Could not create full agent registry: {e}")
            # Create minimal registry
            registry = type('SimpleRegistry', (), {
                'agents': {},
                'get_agent': lambda self, agent_id: None
            })()
        
        # Create workflow compiler
        # Import websocket manager for real-time updates
        from src.realtime.websocket import get_ws_manager
        ws_manager = get_ws_manager()
        
        workflow_compiler = WorkflowCompiler(
            registry=registry,
            event_bus=event_bus,
            checkpoint_dir=Path("./data/checkpoints"),
            websocket_manager=ws_manager
        )
        logger.info("✓ Workflow compiler initialized")
        
        # Try to load workflow definitions if they exist
        workflows_dir = Path("./templates")
        if workflows_dir.exists():
            workflow_files = list(workflows_dir.glob("workflows.yaml"))
            if workflow_files:
                try:
                    workflow_compiler.load_workflows_from_file(workflow_files[0])
                    logger.info("✓ Loaded workflow definitions")
                except Exception as e:
                    logger.warning(f"Could not load workflows: {e}")
        
        # Create execution engine
        execution_engine = JobExecutionEngine(
            workflow_compiler=workflow_compiler,
            checkpoint_manager=checkpoint_manager
        )
        logger.info("✓ Job execution engine initialized")
        
        # Get global job controller
        from src.realtime.job_control import get_controller
        job_controller = get_controller()
        logger.info("✓ Job controller initialized")
        
        return execution_engine, job_controller
        
    except ImportError as e:
        logger.error(f"Import error while initializing execution engine: {e}")
        logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
        return None, None
    except Exception as e:
        logger.error(f"Failed to initialize execution engine: {e}", exc_info=True)
        logger.warning("Web UI will have limited functionality")
        return None, None


def main():
    """Main entry point."""
    print("=" * 60)
    print("UCOP Web UI with Integrated Job Engine")
    print("=" * 60)
    print()
    
    # Load configuration
    config = Config()
    config.load_from_env()
    
    # Create event bus
    event_bus = EventBus()
    
    # Initialize execution engine
    print("Initializing job execution engine...")
    execution_engine, job_controller = initialize_execution_engine(config, event_bus)
    
    # Import web app
    try:
        from src.web.app import app, set_execution_engine
    except ImportError as e:
        logger.error(f"Failed to import web app: {e}")
        logger.error("Make sure FastAPI and dependencies are installed")
        sys.exit(1)
    
    if execution_engine and job_controller:
        # Connect web UI to execution engine
        set_execution_engine(execution_engine, job_controller)
        print("✓ Job execution engine connected to web UI")
    else:
        print("⚠ Web UI running in limited mode (no job execution)")
        print("  Jobs from CLI will not be visible")
        print("  Job creation from web UI will not work")
    
    print()
    print("Starting web server...")
    print("Dashboard: http://localhost:8080  (or http://127.0.0.1:8080)")
    print("API Docs: http://localhost:8080/docs")
    print("Health Check: http://localhost:8080/health")
    print("Status Check: http://localhost:8080/api/status")
    print()
    print("Note: Server runs on 0.0.0.0:8080 (listens on all interfaces)")
    print("      You can access it via localhost:8080 from this machine")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Start uvicorn server
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UCOP Web UI with Job Engine")
    parser.add_argument('--test', action='store_true', help='Run comprehensive tests')
    args = parser.parse_args()
    
    if args.test:
        print("Running comprehensive test suite...")
        import subprocess
        import os
        os.chdir(Path(__file__).parent)
        # Run all tests
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"])
        sys.exit(0)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
