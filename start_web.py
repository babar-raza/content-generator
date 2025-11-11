#!/usr/bin/env python3
"""
UCOP Unified Web Interface
Single entry point for all UCOP features with modular activation.
"""

import sys
import os
import logging
import argparse
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import configuration
from src.core import Config, EventBus
try:
    from src.core.config_validator import ConfigValidator
except ImportError:
    ConfigValidator = None

# Setup logging
def setup_logging(log_level: str = "INFO"):
    """Configure logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ucop_unified.log')
        ]
    )
    return logging.getLogger(__name__)


class OperatingMode(Enum):
    """Operating modes for the unified interface."""
    FULL = "full"           # All features enabled
    JOB = "job"            # Job management only
    VISUAL = "visual"      # Visual orchestration only
    MESH = "mesh"          # Agent mesh monitoring only
    DEBUG = "debug"        # Debugging tools only
    MONITOR = "monitor"    # System monitoring only
    API = "api"           # API-only mode (no UI)
    CUSTOM = "custom"      # Custom feature selection


class UnifiedWebServer:
    """Unified web server with modular feature management."""
    
    def __init__(self, config: Config, args: argparse.Namespace):
        self.config = config
        self.args = args
        self.logger = setup_logging(args.log_level)
        self.event_bus = EventBus()
        
        # Feature states
        self.features = {
            'jobs': False,
            'visual': False,
            'mesh': False,
            'debug': False,
            'monitor': False,
            'api_docs': False
        }
        
        # Component references
        self.execution_engine = None
        self.job_controller = None
        self.workflow_visualizer = None
        self.mesh_monitor = None
        self.debugger = None
        self.system_monitor = None
        
        # Set features based on mode
        self._configure_features()
    
    def _configure_features(self):
        """Configure features based on operating mode and flags."""
        mode = self.args.mode
        
        if mode == OperatingMode.FULL.value:
            # Enable all features
            self.features = {k: True for k in self.features}
        elif mode == OperatingMode.JOB.value:
            self.features['jobs'] = True
            self.features['monitor'] = True
        elif mode == OperatingMode.VISUAL.value:
            self.features['visual'] = True
            self.features['jobs'] = True  # Visual needs jobs
        elif mode == OperatingMode.MESH.value:
            self.features['mesh'] = True
            self.features['monitor'] = True
        elif mode == OperatingMode.DEBUG.value:
            self.features['debug'] = True
            self.features['visual'] = True  # Debug needs visual
            self.features['jobs'] = True    # Debug needs jobs
        elif mode == OperatingMode.MONITOR.value:
            self.features['monitor'] = True
        elif mode == OperatingMode.API.value:
            self.features['jobs'] = True
            self.features['api_docs'] = True
        elif mode == OperatingMode.CUSTOM.value:
            # Use individual feature flags
            if self.args.with_jobs:
                self.features['jobs'] = True
            if self.args.with_visual:
                self.features['visual'] = True
                self.features['jobs'] = True  # Visual requires jobs
            if self.args.with_mesh:
                self.features['mesh'] = True
            if self.args.with_debug:
                self.features['debug'] = True
                self.features['visual'] = True  # Debug requires visual
                self.features['jobs'] = True    # Debug requires jobs
            if self.args.with_monitor:
                self.features['monitor'] = True
            if self.args.with_api_docs:
                self.features['api_docs'] = True
    
    def print_header(self):
        """Print application header with enabled features."""
        print("=" * 70)
        print("UCOP Unified Web Interface")
        print("=" * 70)
        print()
        print(f"Operating Mode: {self.args.mode}")
        print()
        print("Enabled Features:")
        for feature, enabled in self.features.items():
            status = "[ON]" if enabled else "[OFF]"
            feature_name = feature.replace('_', ' ').title()
            print(f"  {status} {feature_name}")
        print()
    
    def validate_environment(self) -> bool:
        """Validate environment and dependencies."""
        print("Validating Environment...")
        print("-" * 50)
        
        validation_passed = True
        
        # Check core dependencies
        required_modules = [
            ('uvicorn', 'pip install uvicorn'),
            ('fastapi', 'pip install fastapi'),
            ('jinja2', 'pip install jinja2'),
            ('pydantic', 'pip install pydantic'),
            ('websockets', 'pip install websockets'),
            ('aiofiles', 'pip install aiofiles'),
        ]
        
        for module_name, install_cmd in required_modules:
            try:
                __import__(module_name)
                print(f"  [OK] {module_name} installed")
            except ImportError:
                print(f"  [FAIL] {module_name} not installed - run: {install_cmd}")
                validation_passed = False
        
        # Check feature-specific dependencies
        if self.features['visual']:
            try:
                import graphviz
                print("  [OK] graphviz installed (visual)")
            except ImportError:
                print("  [WARN] graphviz not installed - visual features limited")
        
        # Validate configuration
        try:
            # Check basic configuration
            if hasattr(self.config, 'llm_provider'):
                print(f"  [OK] LLM Provider configured: {self.config.llm_provider}")
            else:
                print("  [WARN] No LLM provider configured - some features may be limited")
            
            # Try to validate config files if they exist
            if ConfigValidator:
                validator = ConfigValidator()
                config_dir = Path("./config")
                
                if config_dir.exists():
                    try:
                        configs = validator.load_and_validate_all()
                        print("  [OK] Configuration files validated")
                    except FileNotFoundError as e:
                        print(f"  [WARN] Configuration files missing - using defaults")
                    except Exception as e:
                        print(f"  [WARN] Configuration validation warning: {e}")
                else:
                    print("  [WARN] Config directory not found - using defaults")
            else:
                print("  [WARN] ConfigValidator not available - using defaults")
                
        except Exception as e:
            print(f"  [WARN] Configuration check skipped: {e}")
        
        print()
        return validation_passed
    
    def initialize_device(self):
        """Initialize compute device (CPU/GPU)."""
        print("Initializing Compute Device...")
        print("-" * 50)
        
        try:
            from src.engine.device import DeviceManager
            device_manager = DeviceManager()
            device_info = device_manager.get_device_info()
            
            print(f"  [OK] Device: {device_info['device']}")
            print(f"  [OK] Compute: {device_info['compute_capability']}")
            if device_info.get('gpu_name'):
                print(f"  [OK] GPU: {device_info['gpu_name']}")
            print()
            return device_manager
        except Exception as e:
            self.logger.warning(f"Device initialization failed: {e}")
            print("  [WARN] Using CPU (GPU not available)")
            print()
            return None
    
    def initialize_directories(self):
        """Create necessary directories."""
        print("Initializing Directory Structure...")
        print("-" * 50)
        
        directories = [
            "./data/jobs",
            "./data/outputs",
            "./data/checkpoints",
            "./data/cache",
            "./data/logs",
            "./templates",
            "./config",
            "./uploads",
            "./checkpoints"
        ]
        
        for directory in directories:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            print(f"  [OK] {directory}")
        
        print()
    
    def initialize_job_system(self):
        """Initialize job execution system."""
        if not self.features['jobs']:
            return
        
        print("Initializing Job System...")
        print("-" * 50)
        
        try:
            # Initialize checkpoint manager
            from src.orchestration.checkpoint_manager import CheckpointManager
            checkpoint_manager = CheckpointManager(storage_dir=Path("./checkpoints"))
            print("  [OK] Checkpoint manager initialized")
            
            # Initialize agent registry
            try:
                from src.orchestration.enhanced_registry import EnhancedAgentRegistry
                registry = EnhancedAgentRegistry()
                registry.auto_discover()
                print(f"  [OK] Agent registry initialized ({len(registry.agents)} agents)")
            except:
                # Fallback to minimal registry
                registry = None
                print("  [WARN] Using minimal agent registry")
            
            # Initialize workflow compiler
            from src.orchestration.workflow_compiler import WorkflowCompiler
            workflow_compiler = WorkflowCompiler(
                registry=registry,
                event_bus=self.event_bus
            )
            print("  [OK] Workflow compiler initialized")
            
            # Load workflow definitions
            workflows_dir = Path("./templates")
            if workflows_dir.exists():
                workflow_files = list(workflows_dir.glob("workflows*.yaml"))
                for workflow_file in workflow_files:
                    try:
                        workflow_compiler.load_workflows_from_file(workflow_file)
                        print(f"  [OK] Loaded workflows from {workflow_file.name}")
                    except Exception as e:
                        self.logger.warning(f"Could not load {workflow_file}: {e}")
            
            # Use enhanced execution engine if available, otherwise fallback
            try:
                from src.orchestration.job_execution_engine_enhanced import JobExecutionEngineEnhanced
                
                # Determine verbosity based on log level
                verbose = self.args.log_level in ['debug', 'info']
                debug = self.args.log_level == 'debug'
                
                self.execution_engine = JobExecutionEngineEnhanced(
                    workflow_compiler=workflow_compiler,
                    checkpoint_manager=checkpoint_manager,
                    verbose=verbose,
                    debug=debug
                )
                print("  [OK] Enhanced job execution engine initialized (verbose logging enabled)")
                
            except ImportError:
                # Fallback to standard engine
                from src.orchestration.job_execution_engine import JobExecutionEngine
                self.execution_engine = JobExecutionEngine(
                    workflow_compiler=workflow_compiler,
                    checkpoint_manager=checkpoint_manager
                )
                print("  [OK] Standard job execution engine initialized")
            
            # Initialize job controller
            from src.realtime.job_control import JobController, get_controller
            try:
                self.job_controller = get_controller()
                print("  [OK] Job controller (singleton) initialized")
            except:
                self.job_controller = JobController()
                print("  [OK] Job controller (new) initialized")
            
            print()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize job system: {e}", exc_info=True)
            print(f"  [FAIL] Job system initialization failed: {e}")
            print()
            return False
    
    def initialize_visual_system(self):
        """Initialize visual orchestration components."""
        if not self.features['visual']:
            return
        
        print("Initializing Visual Orchestration...")
        print("-" * 50)
        
        try:
            from src.visualization.workflow_visualizer import WorkflowVisualizer
            self.workflow_visualizer = WorkflowVisualizer()
            print("  [OK] Workflow visualizer initialized")
            
            if self.features['mesh']:
                from src.visualization.agent_flow_monitor import get_flow_monitor
                self.mesh_monitor = get_flow_monitor()
                print("  [OK] Agent flow monitor initialized")
            
            if self.features['debug']:
                from src.visualization.workflow_debugger import get_workflow_debugger
                self.debugger = get_workflow_debugger()
                print("  [OK] Workflow debugger initialized")
            
            print()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize visual system: {e}", exc_info=True)
            print(f"  [FAIL] Visual system initialization failed: {e}")
            print()
            return False
    
    def initialize_monitoring_system(self):
        """Initialize system monitoring components."""
        if not self.features['monitor']:
            return
        
        print("Initializing Monitoring System...")
        print("-" * 50)
        
        try:
            from src.visualization.monitor import get_monitor
            self.system_monitor = get_monitor()
            print("  [OK] System monitor initialized")
            
            # Start background monitoring if available
            if hasattr(self.system_monitor, 'start_monitoring'):
                self.system_monitor.start_monitoring()
                print("  [OK] Background monitoring started")
            else:
                print("  [OK] System monitor ready")
            
            print()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring: {e}", exc_info=True)
            print(f"  [FAIL] Monitoring initialization failed: {e}")
            print()
            return False
    
    def create_app(self):
        """Create the FastAPI application with selected modules."""
        print("Creating Web Application...")
        print("-" * 50)
        
        try:
            # Import the appropriate app based on features
            if self.features['visual'] or self.features['mesh'] or self.features['debug']:
                # Use integrated app with visual features
                from src.web.app_integrated import app, set_execution_engine
                print("  [OK] Using integrated web app (with visual features)")
            else:
                # Use basic app
                from src.web.app import app, set_execution_engine
                print("  [OK] Using basic web app")
            
            # Connect execution engine if available
            if self.execution_engine and self.job_controller:
                set_execution_engine(self.execution_engine, self.job_controller)
                print("  [OK] Job execution engine connected")
            
            # Add API documentation if enabled
            if self.features['api_docs']:
                from fastapi.openapi.docs import get_swagger_ui_html
                print("  [OK] API documentation enabled")
            
            # Configure CORS if enabled
            if self.args.enable_cors:
                from fastapi.middleware.cors import CORSMiddleware
                app.add_middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
                print("  [OK] CORS enabled")
            
            print()
            return app
            
        except Exception as e:
            self.logger.error(f"Failed to create web app: {e}", exc_info=True)
            print(f"  [FAIL] Web app creation failed: {e}")
            print()
            return None
    
    def print_server_info(self):
        """Print server information and available endpoints."""
        print()
        print("=" * 70)
        print("Server Information")
        print("=" * 70)
        print()
        print(f"Dashboard:    http://localhost:{self.args.port}")
        print(f"              http://127.0.0.1:{self.args.port}")
        
        if self.args.api_only:
            print()
            print("Running in API-only mode (no UI)")
        
        if self.features['api_docs']:
            print(f"API Docs:     http://localhost:{self.args.port}/docs")
            print(f"OpenAPI:      http://localhost:{self.args.port}/openapi.json")
        
        print(f"Health Check: http://localhost:{self.args.port}/health")
        
        print()
        print(f"Server:       {self.args.host}:{self.args.port}")
        
        if self.args.host == "0.0.0.0":
            print("              (listening on all interfaces)")
        
        print()
        print("Available Features:")
        
        if self.features['jobs']:
            print("  Job Management")
            print("    - /jobs          - Job dashboard")
            print("    - /api/jobs      - Job API")
            print("    - /ws/jobs       - Job WebSocket")
        
        if self.features['visual']:
            print("  Visual Orchestration")
            print("    - /visual        - Workflow visualization")
            print("    - /api/visual    - Visual API")
            print("    - /ws/visual     - Visual WebSocket")
        
        if self.features['mesh']:
            print("  Agent Mesh Monitoring")
            print("    - /mesh          - Agent flow monitor")
            print("    - /api/mesh      - Mesh API")
        
        if self.features['debug']:
            print("  Debugging Tools")
            print("    - /debug         - Workflow debugger")
            print("    - /api/debug     - Debug API")
        
        if self.features['monitor']:
            print("  System Monitoring")
            print("    - /monitor       - System metrics")
            print("    - /api/metrics   - Metrics API")
        
        print()
        print("Press Ctrl+C to stop")
        print("=" * 70)
        print()
    
    def run(self):
        """Run the unified web server."""
        # Print header
        self.print_header()
        
        # Validate environment
        if not self.validate_environment():
            print("[ERROR] Environment validation failed. Please fix the issues above.")
            return 1
        
        # Initialize systems
        self.initialize_device()
        self.initialize_directories()
        
        # Initialize components based on features
        if self.features['jobs']:
            if not self.initialize_job_system():
                self.logger.warning("Job system initialization failed - continuing with limited functionality")
        
        if self.features['visual'] or self.features['mesh'] or self.features['debug']:
            if not self.initialize_visual_system():
                self.logger.warning("Visual system initialization failed - continuing with limited functionality")
        
        if self.features['monitor']:
            if not self.initialize_monitoring_system():
                self.logger.warning("Monitoring initialization failed - continuing with limited functionality")
        
        # Create web application
        app = self.create_app()
        if not app:
            print("[ERROR] Failed to create web application")
            return 1
        
        # Print server information
        self.print_server_info()
        
        # Start server
        try:
            import uvicorn
            
            # Configure uvicorn
            uvicorn_config = {
                "app": app,
                "host": self.args.host,
                "port": self.args.port,
                "log_level": self.args.log_level.lower(),
                "reload": self.args.reload,
                "workers": self.args.workers if not self.args.reload else 1,
            }
            
            # Run server
            uvicorn.run(**uvicorn_config)
            
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down gracefully...")
            return 0
        except Exception as e:
            self.logger.error(f"Server error: {e}", exc_info=True)
            print(f"[ERROR] Server error: {e}")
            return 1


def create_parser():
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='UCOP Unified Web Interface - All features in one place',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with all features
  python start_web.py --mode full
  
  # Job management only
  python start_web.py --mode job
  
  # Visual orchestration with debugging
  python start_web.py --mode debug
  
  # Custom feature selection
  python start_web.py --mode custom --with-jobs --with-visual --with-monitor
  
  # API-only mode with documentation
  python start_web.py --mode api --port 8081
  
  # Development mode with auto-reload
  python start_web.py --mode full --reload --log-level debug
"""
    )
    
    # Server configuration
    parser.add_argument('--host', default='0.0.0.0',
                      help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080,
                      help='Port to bind to (default: 8080)')
    
    # Operating mode
    parser.add_argument('--mode', 
                      choices=['full', 'job', 'visual', 'mesh', 'debug', 'monitor', 'api', 'custom'],
                      default='full',
                      help='Operating mode (default: full)')
    
    # Feature flags (for custom mode)
    parser.add_argument('--with-jobs', action='store_true',
                      help='Enable job management')
    parser.add_argument('--with-visual', action='store_true',
                      help='Enable visual orchestration')
    parser.add_argument('--with-mesh', action='store_true',
                      help='Enable agent mesh monitoring')
    parser.add_argument('--with-debug', action='store_true',
                      help='Enable debugging tools')
    parser.add_argument('--with-monitor', action='store_true',
                      help='Enable system monitoring')
    parser.add_argument('--with-api-docs', action='store_true',
                      help='Enable API documentation')
    
    # Server options
    parser.add_argument('--config', type=str,
                      help='Configuration file path')
    parser.add_argument('--no-browser', action='store_true',
                      help="Don't auto-open browser")
    parser.add_argument('--log-level',
                      choices=['debug', 'info', 'warning', 'error'],
                      default='info',
                      help='Logging level (default: info)')
    parser.add_argument('--enable-cors', action='store_true',
                      help='Enable CORS')
    parser.add_argument('--api-only', action='store_true',
                      help='API-only mode (no UI)')
    parser.add_argument('--reload', action='store_true',
                      help='Enable auto-reload (development)')
    parser.add_argument('--workers', type=int, default=1,
                      help='Number of worker processes (default: 1)')
    parser.add_argument('--theme',
                      choices=['light', 'dark', 'auto'],
                      default='auto',
                      help='UI theme (default: auto)')
    
    return parser


def main():
    """Main entry point."""
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Load configuration
    config = Config()
    
    # Load from file if specified
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            config.load_from_file(config_path)
        else:
            print(f"[ERROR] Configuration file not found: {args.config}")
            return 1
    else:
        # Load from environment
        try:
            config.load_from_env()
        except Exception as e:
            print(f"[WARN] Could not load .env file: {e}")
    
    # Create and run server
    server = UnifiedWebServer(config, args)
    return server.run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[INFO] Shutdown complete")
        sys.exit(0)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"[ERROR] Fatal error: {e}")
        sys.exit(1)
