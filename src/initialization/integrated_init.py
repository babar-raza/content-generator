"""Integrated System Initialization with Comprehensive Checks."""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from src.core import Config, EventBus

logger = logging.getLogger(__name__)


class SystemInitializer:
    """Handles comprehensive system initialization with checks."""
    
    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.initialization_results = {}
    
    def initialize_all(self) -> Tuple[Optional[Any], Optional[Any], Dict[str, Any]]:
        """Initialize all system components with comprehensive checks.
        
        Returns:
            Tuple of (execution_engine, job_controller, initialization_status)
        """
        print("=" * 70)
        print("SYSTEM INITIALIZATION")
        print("=" * 70)
        print()
        
        # Step 1: GPU/Device Detection
        print("🔍 Checking compute devices...")
        device_status = self._check_device()
        self.initialization_results['device'] = device_status
        
        # Step 2: Cache Validation
        print("\n🗂️  Validating cache directories...")
        cache_status = self._check_cache()
        self.initialization_results['cache'] = cache_status
        
        # Step 3: Ollama Detection
        print("\n🤖 Checking Ollama setup...")
        ollama_status = self._check_ollama()
        self.initialization_results['ollama'] = ollama_status
        
        # Step 4: LLM Provider Configuration
        print("\n🔌 Validating LLM configuration...")
        llm_status = self._check_llm_provider()
        self.initialization_results['llm'] = llm_status
        
        # Step 5: Initialize Execution Engine
        print("\n⚙️  Initializing execution engine...")
        execution_engine, job_controller = self._initialize_execution_engine()
        self.initialization_results['execution_engine'] = {
            'initialized': execution_engine is not None,
            'job_controller': job_controller is not None
        }
        
        # Step 6: Initialize Visual Orchestration
        print("\n📊 Initializing visual orchestration...")
        visual_status = self._initialize_visual_orchestration()
        self.initialization_results['visual'] = visual_status
        
        print("\n" + "=" * 70)
        print("INITIALIZATION COMPLETE")
        print("=" * 70)
        print()
        
        self._print_summary()
        
        return execution_engine, job_controller, self.initialization_results
    
    def _check_device(self) -> Dict[str, Any]:
        """Check and initialize GPU/device."""
        try:
            from src.engine.device import get_gpu_manager
            gpu_manager = get_gpu_manager()
            device = gpu_manager.choose_device("auto")
            
            logger.info(f"✓ Device selected: {device} ({gpu_manager.detection_reason})")
            print(f"  ✓ Device: {device}")
            print(f"    Reason: {gpu_manager.detection_reason}")
            
            return {
                'available': True,
                'device': device,
                'reason': gpu_manager.detection_reason,
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"✗ Device detection failed: {e}")
            print(f"  ✗ Device detection failed: {e}")
            return {
                'available': False,
                'device': 'cpu',
                'error': str(e),
                'status': 'error'
            }
    
    def _check_cache(self) -> Dict[str, Any]:
        """Validate cache directories."""
        cache_dirs = [
            Path("./cache"),
            Path("./checkpoints"),
            Path("./output")
        ]
        
        status = {'directories': {}, 'status': 'success'}
        
        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                cache_dir.mkdir(parents=True, exist_ok=True)
                print(f"  ✓ Created: {cache_dir}")
                status['directories'][str(cache_dir)] = 'created'
            else:
                print(f"  ✓ Exists: {cache_dir}")
                status['directories'][str(cache_dir)] = 'exists'
        
        return status
    
    def _check_ollama(self) -> Dict[str, Any]:
        """Check Ollama availability and models."""
        try:
            from src.utils.ollama_detector import check_ollama_setup
            
            ollama_url = getattr(self.config, 'ollama_base_url', 'http://localhost:11434')
            ollama_info = check_ollama_setup(ollama_url)
            
            if ollama_info['available']:
                print(f"  ✓ Ollama Status: {ollama_info['status']}")
                print(f"    URL: {ollama_info['base_url']}")
                print(f"    Models: {ollama_info['models_count']} installed")
                
                # Show top 3 models
                if ollama_info['models']:
                    print("    Top models:")
                    for model in ollama_info['models'][:3]:
                        caps = ', '.join(model['capabilities'])
                        print(f"      • {model['name']} [{caps}]")
                
                # Show recommendations
                if ollama_info['recommendations']:
                    print("    Recommended for:")
                    for cap, models in ollama_info['recommendations'].items():
                        if models:
                            print(f"      • {cap}: {models[0]}")
            else:
                print(f"  ⚠ Ollama Status: {ollama_info['status']}")
                print("    Note: Ollama models won't be available")
            
            ollama_info['status_level'] = 'success' if ollama_info['available'] else 'warning'
            return ollama_info
            
        except Exception as e:
            logger.warning(f"Ollama check failed: {e}")
            print(f"  ⚠ Ollama check failed: {e}")
            return {
                'available': False,
                'status': f'Error: {str(e)}',
                'status_level': 'error'
            }
    
    def _check_llm_provider(self) -> Dict[str, Any]:
        """Validate LLM provider configuration."""
        llm_provider = getattr(self.config, 'llm_provider', None)
        
        if not llm_provider:
            print("  ⚠ No LLM provider configured!")
            print("    Set environment variable: LLM_PROVIDER=ollama|gemini|openai")
            print("    Jobs will fail without LLM configuration")
            return {
                'configured': False,
                'provider': None,
                'status': 'warning'
            }
        
        print(f"  ✓ Provider: {llm_provider}")
        
        status = {
            'configured': True,
            'provider': llm_provider,
            'status': 'success'
        }
        
        # Check provider-specific configuration
        if llm_provider == 'gemini':
            if not getattr(self.config, 'gemini_api_key', None):
                print("    ✗ GEMINI_API_KEY not set!")
                status['status'] = 'error'
                status['error'] = 'API key missing'
            else:
                print("    ✓ API key configured")
        
        elif llm_provider == 'openai':
            if not getattr(self.config, 'openai_api_key', None):
                print("    ✗ OPENAI_API_KEY not set!")
                status['status'] = 'error'
                status['error'] = 'API key missing'
            else:
                print("    ✓ API key configured")
        
        elif llm_provider == 'ollama':
            ollama_url = getattr(self.config, 'ollama_base_url', 'http://localhost:11434')
            print(f"    Ollama URL: {ollama_url}")
            
            # Check if we have model configurations
            topic_model = getattr(self.config, 'ollama_topic_model', None)
            content_model = getattr(self.config, 'ollama_content_model', None)
            code_model = getattr(self.config, 'ollama_code_model', None)
            
            if topic_model:
                print(f"    Topic model: {topic_model}")
            if content_model:
                print(f"    Content model: {content_model}")
            if code_model:
                print(f"    Code model: {code_model}")
        
        return status
    
    def _initialize_execution_engine(self) -> Tuple[Optional[Any], Optional[Any]]:
        """Initialize job execution engine."""
        try:
            from src.orchestration.checkpoint_manager import CheckpointManager
            from src.orchestration.workflow_compiler import WorkflowCompiler
            from src.orchestration.job_execution_engine import JobExecutionEngine
            
            # Create checkpoint manager
            checkpoint_manager = CheckpointManager(
                storage_dir=Path("./checkpoints")
            )
            print("  ✓ Checkpoint manager initialized")
            
            # Create agent registry
            from src.orchestration.enhanced_registry import EnhancedAgentRegistry
            try:
                registry = EnhancedAgentRegistry()
                print("  ✓ Agent registry initialized")
            except Exception as e:
                logger.warning(f"Could not create full agent registry: {e}")
                # Create minimal registry
                registry = type('SimpleRegistry', (), {
                    'agents': {},
                    'get_agent': lambda self, agent_id: None
                })()
                print("  ⚠ Using minimal agent registry")
            
            # Create workflow compiler
            workflow_compiler = WorkflowCompiler(
                registry=registry,
                event_bus=self.event_bus
            )
            print("  ✓ Workflow compiler initialized")
            
            # Load workflow definitions
            workflows_dir = Path("./templates")
            if workflows_dir.exists():
                workflow_files = list(workflows_dir.glob("workflows.yaml"))
                if workflow_files:
                    try:
                        workflow_compiler.load_workflows_from_file(workflow_files[0])
                        print("  ✓ Loaded workflow definitions")
                    except Exception as e:
                        logger.warning(f"Could not load workflows: {e}")
                        print(f"  ⚠ Could not load workflows: {e}")
            
            # Create execution engine
            execution_engine = JobExecutionEngine(
                workflow_compiler=workflow_compiler,
                checkpoint_manager=checkpoint_manager
            )
            print("  ✓ Job execution engine initialized")
            
            # Get job controller
            from src.realtime.job_control import get_controller
            job_controller = get_controller()
            print("  ✓ Job controller initialized")
            
            return execution_engine, job_controller
            
        except ImportError as e:
            logger.error(f"Import error: {e}")
            print(f"  ✗ Import error: {e}")
            print("    Make sure dependencies are installed:")
            print("    pip install -r requirements.txt")
            return None, None
        except Exception as e:
            logger.error(f"Failed to initialize: {e}", exc_info=True)
            print(f"  ✗ Initialization failed: {e}")
            return None, None
    
    def _initialize_visual_orchestration(self) -> Dict[str, Any]:
        """Initialize visual orchestration components."""
        status = {'components': {}, 'status': 'success'}
        
        try:
            # Check workflow visualizer
            try:
                from src.visualization.workflow_visualizer import WorkflowVisualizer
                visualizer = WorkflowVisualizer(workflow_dir='./templates')
                status['components']['visualizer'] = True
                print("  ✓ Workflow visualizer")
            except Exception as e:
                status['components']['visualizer'] = False
                print(f"  ⚠ Workflow visualizer: {e}")
            
            # Check flow monitor
            try:
                from src.visualization.monitor import get_monitor
                monitor = get_monitor()
                status['components']['monitor'] = True
                print("  ✓ Flow monitor")
            except Exception as e:
                status['components']['monitor'] = False
                print(f"  ⚠ Flow monitor: {e}")
            
            # Check agent flow monitor
            try:
                from src.visualization.agent_flow_monitor import get_flow_monitor
                flow_monitor = get_flow_monitor()
                status['components']['agent_flow_monitor'] = True
                print("  ✓ Agent flow monitor")
            except Exception as e:
                status['components']['agent_flow_monitor'] = False
                print(f"  ⚠ Agent flow monitor: {e}")
            
            # Check workflow debugger
            try:
                from src.visualization.workflow_debugger import get_workflow_debugger
                debugger = get_workflow_debugger()
                status['components']['debugger'] = True
                print("  ✓ Workflow debugger")
            except Exception as e:
                status['components']['debugger'] = False
                print(f"  ⚠ Workflow debugger: {e}")
            
        except Exception as e:
            logger.error(f"Visual orchestration init error: {e}")
            print(f"  ✗ Visual orchestration failed: {e}")
            status['status'] = 'error'
        
        return status
    
    def _print_summary(self):
        """Print initialization summary."""
        print("Summary:")
        
        # Device
        device_info = self.initialization_results.get('device', {})
        if device_info.get('available'):
            print(f"  ✓ Device: {device_info.get('device', 'unknown')}")
        else:
            print("  ✗ Device: Failed")
        
        # Cache
        cache_info = self.initialization_results.get('cache', {})
        if cache_info.get('status') == 'success':
            print("  ✓ Cache: Ready")
        
        # Ollama
        ollama_info = self.initialization_results.get('ollama', {})
        if ollama_info.get('available'):
            print(f"  ✓ Ollama: {ollama_info.get('models_count', 0)} models")
        else:
            print("  ⚠ Ollama: Not available")
        
        # LLM
        llm_info = self.initialization_results.get('llm', {})
        if llm_info.get('configured'):
            print(f"  ✓ LLM: {llm_info.get('provider', 'unknown')}")
        else:
            print("  ⚠ LLM: Not configured")
        
        # Execution engine
        engine_info = self.initialization_results.get('execution_engine', {})
        if engine_info.get('initialized'):
            print("  ✓ Execution Engine: Ready")
        else:
            print("  ⚠ Execution Engine: Limited mode")
        
        # Visual orchestration
        visual_info = self.initialization_results.get('visual', {})
        components = visual_info.get('components', {})
        active_count = sum(1 for v in components.values() if v)
        total_count = len(components)
        print(f"  {'✓' if active_count == total_count else '⚠'} Visual Orchestration: {active_count}/{total_count} components")


def initialize_integrated_system(config: Config, event_bus: EventBus):
    """Initialize integrated system with all checks.
    
    Returns:
        Tuple of (execution_engine, job_controller, initialization_status)
    """
    initializer = SystemInitializer(config, event_bus)
    return initializer.initialize_all()
