#!/usr/bin/env python3
"""Quick validation that start_web.py will work correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("Validating start_web.py components...")
print("=" * 50)

try:
    # Test the exact sequence from start_web.py
    from src.engine.engine import get_engine
    from src.core import EventBus
    from src.core.template_registry import TemplateRegistry
    from src.orchestration.workflow_compiler import WorkflowCompiler
    from src.orchestration.checkpoint_manager import CheckpointManager
    from src.orchestration.job_execution_engine import JobExecutionEngine
    from src.realtime.job_control import JobController
    
    # Initialize exactly as start_web.py does
    engine = get_engine()
    event_bus = EventBus()
    template_registry = TemplateRegistry()
    workflow_compiler = WorkflowCompiler(template_registry, event_bus)
    checkpoint_manager = CheckpointManager()
    job_engine = JobExecutionEngine(workflow_compiler, checkpoint_manager)
    
    # This was the problematic line - now fixed!
    job_controller = JobController()  # No parameters!
    
    print("✅ All components initialized successfully!")
    print("✅ JobController() works without parameters")
    print("✅ start_web.py should now run without TypeError")
    
    # Try to set up web app if available
    try:
        from src.web.app import set_execution_engine
        set_execution_engine(job_engine, job_controller)
        print("✅ Web app configuration works")
    except ImportError:
        print("⚠️  FastAPI not installed - install with: pip install fastapi uvicorn")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease report this error if it persists.")
    sys.exit(1)

print("=" * 50)
print("Validation complete! You can now run:")
print("  python start_web.py")
