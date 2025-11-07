"""Main Entry Point - AI Blog Generator v9.5 FIXED

Unified system with Mesh Infrastructure, Orchestration, and all hardening fixes applied.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import json
import traceback

# Add fixes to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core import Config, EventBus, load_schemas, AgentEvent
from src.core.config import load_config
from src.services.services import LLMService, DatabaseService, EmbeddingService, GistService
from src.services.services_fixes import (
    apply_llm_service_fixes, NoMockGate, SEOSchemaGate,
    PrerequisitesNormalizer, PyTrendsGuard, TopicIdentificationFallback,
    BlogSwitchPolicy, RunToResultGuarantee
)

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
    """Create and initialize services with all fixes."""
    from src.services.services import TrendsService, LinkChecker
    from src.utils.learning import PerformanceTracker
    
    # Create LLM service with NO-MOCK gate applied
    llm_service = LLMService(config)
    llm_service = apply_llm_service_fixes(llm_service)
    
    embedding_service = EmbeddingService(config)
    database_service = DatabaseService(config, embedding_service)
    gist_service = GistService(config)
    
    # Wrap TrendsService with PyTrendsGuard
    trends_service = TrendsService(config)
    trends_guard = PyTrendsGuard(
        max_retries=config.pytrends_max_retries,
        backoff=config.pytrends_backoff
    )
    # Monkey-patch the trends service to use guard
    original_fetch = trends_service.get_trends if hasattr(trends_service, 'get_trends') else lambda x: {}
    trends_service.get_trends = lambda query: trends_guard.safe_fetch(query, original_fetch)
    
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
    """Create all agents with full resilience and fixes applied."""
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
            logger.debug(traceback.format_exc())
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
        
        # Import enhanced agents with fixes
        from src.agents.publishing.frontmatter_enhanced import FrontmatterAgent as EnhancedFrontmatterAgent
    except Exception as e:
        logger.error(f"Failed to import agents: {e}")
        return agents
    
    # Create all agents with safe error handling
    
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
    
    # Research agents with topic fallback
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
    
    # SEO agents with enhanced normalization
    safe_create('SEOMetadataAgent', lambda: SEOMetadataAgent(
        config, event_bus, llm_service, trends_service
    ))
    safe_create('KeywordExtractionAgent', lambda: KeywordExtractionAgent(
        config, event_bus, llm_service, trends_service
    ))
    safe_create('KeywordInjectionAgent', lambda: KeywordInjectionAgent(
        config, event_bus, llm_service
    ))
    
    # Publishing agents with enhanced frontmatter
    safe_create('GistREADMEAgent', lambda: GistREADMEAgent(
        config, event_bus, llm_service
    ))
    safe_create('GistUploadAgent', lambda: GistUploadAgent(
        config, event_bus, gist_service
    ))
    safe_create('LinkValidationAgent', lambda: LinkValidationAgent(
        config, event_bus, link_checker
    ))
    
    # Use enhanced FrontmatterAgent with prerequisites fix
    safe_create('FrontmatterAgent', lambda: EnhancedFrontmatterAgent(
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
    """Enable mesh infrastructure (optional)."""
    try:
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
    except Exception as e:
        logger.warning(f"Could not enable mesh: {e}")


def enable_orchestration(config: Config, event_bus: EventBus, agents: Dict):
    """Enable orchestration layer (optional)."""
    try:
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
                event_bus=event_bus,
                execution_engine=execution_engine,
                host=config.orchestration.ops_console_host,
                port=config.orchestration.ops_console_port
            )
            console.start()
            logger.info(f"Ops console started at http://{config.orchestration.ops_console_host}:{config.orchestration.ops_console_port}")
        
        logger.info("Orchestration layer enabled")
        return execution_engine
    except Exception as e:
        logger.warning(f"Could not enable orchestration: {e}")
        return None


def run_default_pipeline(config: Config, event_bus: EventBus, agents: Dict, topic: str):
    """Run the default pipeline with run-to-result guarantee."""
    from src.engine.slug_service import slugify
    import uuid
    
    correlation_id = str(uuid.uuid4())
    
    # Ensure topic has proper structure
    topic_data = TopicIdentificationFallback.ensure_topic({
        'title': topic,
        'slug': slugify(topic)
    })
    
    logger.info(f"Starting pipeline for topic: {topic_data['title']}")
    
    try:
        # Execute pipeline steps
        pipeline_steps = config.orchestration.default_pipeline if hasattr(config.orchestration, 'default_pipeline') else [
            "identify_topic",
            "generate_seo", 
            "build_frontmatter",
            "assemble_content",
            "write_output"
        ]
        
        # Initial event data
        event_data = {
            'topic': topic_data,
            'correlation_id': correlation_id
        }
        
        # Execute each step
        for step in pipeline_steps:
            logger.info(f"Executing pipeline step: {step}")
            
            # Map step names to agent execution
            step_mapping = {
                'identify_topic': lambda: agents.get('TopicIdentificationAgent'),
                'generate_seo': lambda: agents.get('SEOMetadataAgent'),
                'dup_check': lambda: agents.get('DuplicationCheckAgent'),
                'build_frontmatter': lambda: agents.get('FrontmatterAgent'),
                'assemble_content': lambda: agents.get('ContentAssemblyAgent'),
                'write_output': lambda: agents.get('FileWriterAgent')
            }
            
            if step in step_mapping:
                agent = step_mapping[step]()
                if agent and hasattr(agent, 'execute'):
                    try:
                        event = AgentEvent(
                            event_type=f"execute_{step}",
                            data=event_data,
                            source_agent='pipeline',
                            correlation_id=correlation_id
                        )
                        result = agent.execute(event)
                        if result and result.data:
                            event_data.update(result.data)
                    except Exception as e:
                        logger.error(f"Step {step} failed: {e}")
                        # Continue with next step
        
        logger.info(f"Pipeline completed for topic: {topic}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        logger.info("Creating fallback document...")
        
        # Create minimal document as fallback
        fallback_doc = RunToResultGuarantee.create_minimal_document(
            topic=topic_data['title'],
            slug=topic_data['slug']
        )
        
        # Write fallback document
        output_path = config.get_output_path(topic_data['slug'])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fallback_doc)
        
        logger.info(f"Fallback document written to: {output_path}")


def main():
    """Main execution with all fixes applied."""
    parser = argparse.ArgumentParser(description='AI Blog Generator v9.5 FIXED')
    parser.add_argument('--topic', type=str, help='Topic to generate blog post about')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--blog-mode', choices=['on', 'off'], default='on',
                       help='Blog switch: on = /slug/index.md, off = /slug.md')
    parser.add_argument('--enable-mesh', action='store_true', help='Enable mesh infrastructure')
    parser.add_argument('--enable-orchestration', action='store_true', help='Enable orchestration layer')
    parser.add_argument('--test', action='store_true', help='Run tests')
    parser.add_argument('--validate-only', action='store_true', help='Validate configuration only')
    
    args = parser.parse_args()
    
    # Run tests if requested
    if args.test:
        from tests.test_fixes import run_tests
        run_tests()
        return
    
    # Load configuration
    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)
    
    # Apply command-line overrides
    if args.blog_mode:
        config.blog_switch = (args.blog_mode == 'on')
    if args.enable_mesh:
        config.mesh.enabled = True
    if args.enable_orchestration:
        config.orchestration.enabled = True
    
    # Set up logging
    setup_logging(config)
    
    logger.info("=" * 60)
    logger.info("AI Blog Generator v9.5 - FIXED VERSION")
    logger.info("=" * 60)
    logger.info(f"Configuration loaded: blog_switch={config.blog_switch}")
    logger.info(f"Provider: {config.llm_provider}")
    logger.info(f"Output directory: {config.output_dir}")
    
    # Validate configuration
    if args.validate_only:
        logger.info("Configuration validation successful")
        return
    
    # Check for topic
    if not args.topic:
        logger.error("No topic specified. Use --topic 'Your Topic'")
        sys.exit(1)
    
    # Create event bus
    event_bus = EventBus()
    
    # Create services with fixes
    logger.info("Creating services...")
    services = create_services(config)
    
    # Create agents with fixes
    logger.info("Creating agents...")
    agents = create_agents(config, event_bus, services)
    
    if len(agents) == 0:
        logger.error("No agents created. Cannot proceed.")
        sys.exit(1)
    
    # Enable optional features
    if config.mesh.enabled:
        enable_mesh(config, event_bus, agents)
    
    execution_engine = None
    if config.orchestration.enabled:
        execution_engine = enable_orchestration(config, event_bus, agents)
    
    # Run the pipeline
    logger.info(f"Generating blog post for: {args.topic}")
    
    if execution_engine:
        # Use orchestration engine
        logger.info("Running with orchestration engine...")
        # TODO: Implement orchestration execution
        run_default_pipeline(config, event_bus, agents, args.topic)
    else:
        # Use default pipeline
        logger.info("Running default pipeline...")
        run_default_pipeline(config, event_bus, agents, args.topic)
    
    logger.info("=" * 60)
    logger.info("Blog generation complete!")
    logger.info(f"Output location: {config.output_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
