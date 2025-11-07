"""Main Entry Point - AI Blog Generator v2.0

Unified system with Mesh Infrastructure and Orchestration.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Dict

from src.core import Config, EventBus, load_schemas, AgentEvent
from src.services.services import LLMService, DatabaseService, EmbeddingService, GistService


logger = logging.getLogger(__name__)


def setup_logging(config: Config):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('blog-generator.log')
        ]
    )


def create_services(config: Config):
    """Create and initialize services."""
    from src.services.services import TrendsService, LinkChecker
    from src.utils.learning import PerformanceTracker
    
    llm_service = LLMService(config)
    embedding_service = EmbeddingService(config)
    database_service = DatabaseService(config, embedding_service)
    gist_service = GistService(config)
    trends_service = TrendsService(config)
    link_checker = LinkChecker(config)
    performance_tracker = PerformanceTracker(window_size=20)
    
    return {
        'llm_service': llm_service,
        'database_service': database_service,
        'embedding_service': embedding_service,
        'gist_service': gist_service,
        'trends_service': trends_service,
        'link_checker': link_checker,
        'performance_tracker': performance_tracker
    }


def create_agents(config: Config, event_bus: EventBus, services):
    """Create all agents with full resilience - failures won't stop the process."""
    llm_service = services['llm_service']
    database_service = services['database_service']
    embedding_service = services['embedding_service']
    gist_service = services['gist_service']
    trends_service = services['trends_service']
    link_checker = services['link_checker']
    performance_tracker = services['performance_tracker']
    
    agents = {}
    
    def safe_create(name, creator_func):
        """Safely create agent with error handling."""
        try:
            agent = creator_func()
            agents[name] = agent
            logger.info(f"[OK] Created {name}")
            return True
        except Exception as e:
            logger.warning(f"[FAILED] Failed to create {name}: {e}")
            return False
    
    # Import agents from organized subdirectories
    try:
        from src.agents.ingestion import KBIngestionAgent, BlogIngestionAgent, APIIngestionAgent
        from src.agents.research import (
            TopicIdentificationAgent, DuplicationCheckAgent, 
            KBSearchAgent, BlogSearchAgent, APISearchAgent
        )
        from src.agents.content import (
            OutlineCreationAgent, IntroductionWriterAgent, SectionWriterAgent,
            ConclusionWriterAgent, SupplementaryContentAgent, ContentAssemblyAgent
        )
        from src.agents.code import (
            CodeGenerationAgent, CodeExtractionAgent, CodeValidationAgent,
            CodeSplittingAgent, LicenseInjectionAgent
        )
        from src.agents.seo import (
            SEOMetadataAgent, KeywordExtractionAgent, KeywordInjectionAgent
        )
        from src.agents.publishing import (
            GistREADMEAgent, GistUploadAgent, LinkValidationAgent,
            FrontmatterAgent, FileWriterAgent
        )
        from src.agents.support import ModelSelectionAgent, ErrorRecoveryAgent
    except Exception as e:
        logger.error(f"Failed to import agents: {e}")
        return agents
    
    # Ingestion agents
    safe_create('KBIngestionAgent', lambda: KBIngestionAgent(
        config, event_bus, database_service, embedding_service
    ))
    safe_create('BlogIngestionAgent', lambda: BlogIngestionAgent(
        config, event_bus, database_service
    ))
    safe_create('APIIngestionAgent', lambda: APIIngestionAgent(
        config, event_bus, database_service
    ))
    
    # Research agents
    safe_create('TopicIdentificationAgent', lambda: TopicIdentificationAgent(
        config, event_bus, llm_service
    ))
    safe_create('DuplicationCheckAgent', lambda: DuplicationCheckAgent(
        config, event_bus, database_service
    ))
    safe_create('KBSearchAgent', lambda: KBSearchAgent(
        config, event_bus, database_service
    ))
    safe_create('BlogSearchAgent', lambda: BlogSearchAgent(
        config, event_bus, database_service
    ))
    safe_create('APISearchAgent', lambda: APISearchAgent(
        config, event_bus, database_service
    ))
    
    # Content agents
    safe_create('OutlineCreationAgent', lambda: OutlineCreationAgent(
        config, event_bus, llm_service
    ))
    safe_create('IntroductionWriterAgent', lambda: IntroductionWriterAgent(
        config, event_bus, llm_service
    ))
    safe_create('SectionWriterAgent', lambda: SectionWriterAgent(
        config, event_bus, llm_service
    ))
    safe_create('ConclusionWriterAgent', lambda: ConclusionWriterAgent(
        config, event_bus, llm_service
    ))
    safe_create('SupplementaryContentAgent', lambda: SupplementaryContentAgent(
        config, event_bus, llm_service, trends_service
    ))
    safe_create('ContentAssemblyAgent', lambda: ContentAssemblyAgent(
        config, event_bus
    ))
    
    # Code agents
    safe_create('CodeGenerationAgent', lambda: CodeGenerationAgent(
        config, event_bus, llm_service
    ))
    safe_create('CodeExtractionAgent', lambda: CodeExtractionAgent(
        config, event_bus
    ))
    safe_create('CodeValidationAgent', lambda: CodeValidationAgent(
        config, event_bus, llm_service
    ))
    safe_create('CodeSplittingAgent', lambda: CodeSplittingAgent(
        config, event_bus
    ))
    safe_create('LicenseInjectionAgent', lambda: LicenseInjectionAgent(
        config, event_bus
    ))
    
    # SEO agents
    safe_create('SEOMetadataAgent', lambda: SEOMetadataAgent(
        config, event_bus, llm_service, trends_service
    ))
    safe_create('KeywordExtractionAgent', lambda: KeywordExtractionAgent(
        config, event_bus, llm_service, trends_service
    ))
    safe_create('KeywordInjectionAgent', lambda: KeywordInjectionAgent(
        config, event_bus, llm_service
    ))
    
    # Publishing agents
    safe_create('GistREADMEAgent', lambda: GistREADMEAgent(
        config, event_bus, llm_service
    ))
    safe_create('GistUploadAgent', lambda: GistUploadAgent(
        config, event_bus, gist_service
    ))
    safe_create('LinkValidationAgent', lambda: LinkValidationAgent(
        config, event_bus, link_checker
    ))
    safe_create('FrontmatterAgent', lambda: FrontmatterAgent(
        config, event_bus
    ))
    safe_create('FileWriterAgent', lambda: FileWriterAgent(
        config, event_bus
    ))
    
    # Support agents
    safe_create('ModelSelectionAgent', lambda: ModelSelectionAgent(
        config, event_bus, performance_tracker
    ))
    safe_create('ErrorRecoveryAgent', lambda: ErrorRecoveryAgent(
        config, event_bus, llm_service
    ))
    
    logger.info(f"Successfully created {len(agents)}/30 agents")
    return agents

def enable_mesh(config: Config, event_bus: EventBus, agents: Dict):
    """Enable mesh infrastructure."""
    from src.mesh import CapabilityRegistry, MeshObserver, CacheManager
    
    registry = CapabilityRegistry(
        bid_timeout=config.mesh.registry_timeout,
        selection_strategy=config.mesh.bid_strategy
    )
    observer = MeshObserver()
    
    if config.mesh.cache_enabled:
        cache = CacheManager()
    
    # Register agents with mesh
    for agent_id, agent in agents.items():
        if hasattr(agent, 'register_with_mesh'):
            agent.register_with_mesh(registry)
    
    # Connect event bus to mesh
    if hasattr(event_bus, 'set_mesh_integration'):
        event_bus.set_mesh_integration(registry, observer)
    
    logger.info(f"Mesh infrastructure enabled with {len(agents)} agents")


def enable_orchestration(config: Config, event_bus: EventBus, agents: Dict):
    """Enable orchestration layer."""
    from src.orchestration import (
        WorkflowCompiler, JobExecutionEngine, CheckpointManager, OpsConsole
    )
    
    compiler = WorkflowCompiler(agents=agents)
    checkpoint_mgr = CheckpointManager(checkpoint_dir=config.orchestration.checkpoint_dir)
    execution_engine = JobExecutionEngine(
        event_bus=event_bus,
        agents=agents,
        checkpoint_manager=checkpoint_mgr
    )
    
    # Start ops console if configured
    if config.orchestration.ops_console_port:
        console = OpsConsole(
            host=config.orchestration.ops_console_host,
            port=config.orchestration.ops_console_port,
            execution_engine=execution_engine
        )
        console.start()
        logger.info(f"Ops console started at http://{config.orchestration.ops_console_host}:{config.orchestration.ops_console_port}")
    
    logger.info("Orchestration layer enabled")
    return execution_engine, compiler


def run_basic_workflow(config: Config, event_bus: EventBus, agents: dict, topic: str, args):
    """Run basic blog generation workflow with full resilience."""
    from src.core import AgentEvent
    import uuid
    
    # Try to get monitor for tracking
    try:
        from src.utils.simple_monitor import track_event
    except ImportError:
        track_event = lambda x: None  # No-op if monitor not available
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(f"Generating blog for topic: {topic}")
    logger.info(f"Workflow started with correlation_id: {correlation_id}")
    track_event({'type': 'workflow_started', 'topic': topic, 'correlation_id': correlation_id})
    
    # Skip ingestion if no paths provided (topic-only mode)
    if args.topic and not any([args.kb_path, args.kb_dir, args.api_dir, args.blog_dir]):
        logger.info("Topic-only mode - skipping ingestion")
        track_event({'type': 'mode', 'value': 'topic-only'})
    else:
        # KB Ingestion
        if args.kb_path or args.kb_dir:
            kb_path = Path(args.kb_path if args.kb_path else args.kb_dir)
            if kb_path.exists():
                if 'KBIngestionAgent' in agents:
                    try:
                        event = AgentEvent(
                            event_type="execute_ingest_kb",
                            data={"kb_path": str(kb_path)},
                            source_agent="main",
                            correlation_id=correlation_id
                        )
                        event_bus.publish(event)
                        logger.info(f"[OK] Published KB ingestion event for {kb_path}")
                    except Exception as e:
                        logger.warning(f"[FAILED] KB ingestion failed: {e}")
                else:
                    logger.warning("KBIngestionAgent not available")
            else:
                logger.warning(f"KB path not found: {kb_path}")
        
        # Blog Ingestion
        if args.blog_dir:
            blog_path = Path(args.blog_dir)
            if blog_path.exists():
                if 'BlogIngestionAgent' in agents:
                    try:
                        event = AgentEvent(
                            event_type="execute_ingest_blog",
                            data={"blog_dir": str(blog_path)},
                            source_agent="main",
                            correlation_id=correlation_id
                        )
                        event_bus.publish(event)
                        logger.info(f"[OK] Published blog ingestion event for {blog_path}")
                    except Exception as e:
                        logger.warning(f"[FAILED] Blog ingestion failed: {e}")
                else:
                    logger.warning("BlogIngestionAgent not available")
            else:
                logger.warning(f"Blog path not found: {blog_path}")
        
        # API Ingestion
        if args.api_dir:
            api_path = Path(args.api_dir)
            if api_path.exists():
                if 'APIIngestionAgent' in agents:
                    try:
                        event = AgentEvent(
                            event_type="execute_ingest_api",
                            data={"api_dir": str(api_path)},
                            source_agent="main",
                            correlation_id=correlation_id
                        )
                        event_bus.publish(event)
                        logger.info(f"[OK] Published API ingestion event for {api_path}")
                    except Exception as e:
                        logger.warning(f"[FAILED] API ingestion failed: {e}")
                else:
                    logger.warning("APIIngestionAgent not available")
            else:
                logger.warning(f"API path not found: {api_path}")
    
    # Topic identification (always run for any mode)
    if 'TopicIdentificationAgent' in agents:
        try:
            event = AgentEvent(
                event_type="execute_topic_identification",
                data={"topic": topic},
                source_agent="main",
                correlation_id=correlation_id
            )
            event_bus.publish(event)
            logger.info(f"[OK] Published topic identification event")
            track_event({'type': 'agent_event', 'agent': 'TopicIdentificationAgent', 'status': 'published'})
        except Exception as e:
            logger.warning(f"[FAILED] Topic identification failed: {e}")
            track_event({'type': 'error', 'agent': 'TopicIdentificationAgent', 'error': str(e)})
    else:
        logger.warning("TopicIdentificationAgent not available")
    
    logger.info("Workflow events published - agents will process asynchronously")
    track_event({'type': 'workflow_events_published', 'correlation_id': correlation_id})

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='AI Blog Generator v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Core arguments
    parser.add_argument("--topic", type=str, help="Blog topic (for testing without KB)")
    parser.add_argument("--kb-path", "--kb-md", type=str, help="Path to KB article (.md file)")
    parser.add_argument("--kb-dir", type=str, help="Path to KB directory (process all .md files)")
    parser.add_argument("--api-dir", type=str, help="Path to API reference directory")
    parser.add_argument("--blog-dir", type=str, help="Path to existing blog posts directory")
    parser.add_argument("--out-dir", type=str, default="./output", help="Output directory (default: ./output)")
    
    # Feature flags
    parser.add_argument("--enable-mesh", action="store_true", help="Enable mesh infrastructure")
    parser.add_argument("--enable-orchestration", action="store_true", help="Enable orchestration")
    parser.add_argument("--ops-console", action="store_true", help="Start ops console")
    parser.add_argument("--gist-upload", action="store_true", help="Enable Gist upload")
    
    # Workflow
    parser.add_argument("--workflow", type=str, help="Workflow YAML file")
    parser.add_argument("--config", type=str, help="Config file")
    
    args = parser.parse_args()

    # Load configuration
    config = Config()
    
    # Detect family from paths
    if args.kb_path:
        config.family = Config.detect_family_from_path(Path(args.kb_path))
    elif args.kb_dir:
        config.family = Config.detect_family_from_path(Path(args.kb_dir))
    elif args.api_dir:
        config.family = Config.detect_family_from_path(Path(args.api_dir))
    else:
        # Topic-only mode uses "general" family
        config.family = "general"
    
    # Apply CLI args to config
    if args.out_dir:
        config.output_dir = Path(args.out_dir)
    if args.gist_upload:
        config.gist_upload_enabled = True
    
    # Auto-resolve api-dir from kb paths if not set
    if not args.api_dir:
        if args.kb_path:
            args.api_dir = str(Path(args.kb_path).parent.parent / "reference")
        elif args.kb_dir:
            args.api_dir = str(Path(args.kb_dir).parent / "reference")
    
    config.load_from_env()
    
    # Override with CLI args
    if args.enable_mesh:
        config.enable_mesh = True
    if args.enable_orchestration:
        config.enable_orchestration = True
    
    # Setup logging
    setup_logging(config)
    logger.info("AI Blog Generator v2.0 starting...")
    
    # Log CUDA status
    if config.device == "cuda":
        import torch
        if torch and torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA detected: {gpu_name}")
    
    # Load schemas
    load_schemas(config)
    
    # Create event bus
    event_bus = EventBus(enable_mesh=config.enable_mesh)
    
    # Create services with error handling
    try:
        services = create_services(config)
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        if not args.topic:
            logger.error("Cannot proceed without services and no topic provided")
            return 1
        logger.warning("Continuing with limited functionality...")
        services = (None, None, None, None)
    
    # Create agents with error handling
    try:
        agents = create_agents(config, event_bus, services)
        logger.info(f"Created {len(agents)} agents")
    except Exception as e:
        logger.error(f"Failed to create agents: {e}")
        if not args.topic:
            return 1
        logger.warning("Continuing with limited agents...")
        agents = {}
    
    # Start simple web monitor if requested
    if args.ops_console:
        try:
            from src.utils.simple_monitor import get_monitor, track_agent
            monitor = get_monitor(port=config.orchestration.ops_console_port or 8080)
            if monitor.start():
                logger.info(f"Web monitor started at http://localhost:{config.orchestration.ops_console_port or 8080}")
                # Track all agents
                for agent_name in agents.keys():
                    track_agent(agent_name, 'initialized')
            else:
                logger.warning("Failed to start web monitor")
        except Exception as e:
            logger.error(f"Failed to start web monitor: {e}")
            logger.warning("Continuing without web monitor")
    
    # Enable mesh if requested
    if config.enable_mesh:
        try:
            enable_mesh(config, event_bus, agents)
        except Exception as e:
            logger.error(f"Failed to enable mesh: {e}")
            logger.warning("Continuing without mesh infrastructure")
    
    # Enable orchestration if requested
    execution_engine = None
    compiler = None
    if config.enable_orchestration:
        try:
            execution_engine, compiler = enable_orchestration(config, event_bus, agents)
        except Exception as e:
            logger.error(f"Failed to enable orchestration: {e}")
            logger.warning("Continuing without orchestration")
    
    # Run workflow
    if args.topic:
        run_basic_workflow(config, event_bus, agents, args.topic, args)
    elif args.workflow:
        # Enable orchestration if workflow specified
        if not config.enable_orchestration:
            config.enable_orchestration = True
            logger.info("Auto-enabling orchestration for workflow execution")
        
        # Setup orchestration components
        from src.orchestration import (
            WorkflowCompiler, JobExecutionEngine, CheckpointManager
        )
        
        try:
            # Create orchestration components
            compiler = WorkflowCompiler(agents=agents)
            checkpoint_mgr = CheckpointManager(
                checkpoint_dir=config.orchestration.checkpoint_dir
            )
            execution_engine = JobExecutionEngine(
                workflow_compiler=compiler,
                checkpoint_manager=checkpoint_mgr
            )
            
            # Load workflow definition
            workflow_path = Path(args.workflow)
            if not workflow_path.exists():
                logger.error(f"Workflow file not found: {args.workflow}")
                return 1
            
            # Get workflow name from file
            import yaml
            with open(workflow_path) as f:
                workflow_data = yaml.safe_load(f)
                workflow_name = workflow_data.get('name', workflow_path.stem)
            
            # Prepare input parameters
            input_params = {
                'topic': args.topic if args.topic else 'General Topic',
                'kb_path': args.kb_path or args.kb_dir,
                'api_dir': args.api_dir,
                'blog_dir': args.blog_dir,
                'output_dir': str(config.output_dir),
                'family': config.family
            }
            
            logger.info(f"Executing workflow: {workflow_name}")
            logger.info(f"Input parameters: {input_params}")
            
            # Start workflow execution
            job = execution_engine.start_job(
                workflow_name=workflow_name,
                input_params=input_params
            )
            
            logger.info(f"Workflow job started: {job.job_id}")
            logger.info(f"Correlation ID: {job.correlation_id}")
            
            # Monitor execution (synchronous wait)
            import time
            while True:
                status = execution_engine.get_job_status(job.job_id)
                if not status:
                    break
                
                job_status = status.get('status')
                if job_status in ['completed', 'failed', 'cancelled']:
                    logger.info(f"Workflow {job_status}: {workflow_name}")
                    if job_status == 'failed':
                        logger.error(f"Error: {status.get('error')}")
                        return 1
                    break
                
                # Show progress
                if 'current_step' in status:
                    logger.info(f"Progress: Step {status.get('current_step')}")
                
                time.sleep(2)
            
            logger.info("Workflow execution completed successfully")
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 1
    else:
        logger.info("System initialized. Use --topic or --workflow to run.")
    
    # Keep running if ops console is active
    if args.ops_console:
        logger.info("Ops console running. Press Ctrl+C to exit.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
