#!/usr/bin/env python3
"""Test the complete startup sequence for the web UI."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all required imports."""
    print("Testing imports...")
    try:
        from src.web.app import app
        from src.engine.engine import get_engine
        from src.core import EventBus
        from src.core.template_registry import TemplateRegistry
        from src.orchestration.workflow_compiler import WorkflowCompiler
        from src.orchestration.checkpoint_manager import CheckpointManager
        from src.orchestration.job_execution_engine import JobExecutionEngine
        from src.realtime.job_control import JobController
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_initialization():
    """Test the complete initialization sequence."""
    print("\nTesting initialization sequence...")
    
    try:
        from src.engine.engine import get_engine
        from src.core import EventBus
        from src.core.template_registry import TemplateRegistry
        from src.orchestration.workflow_compiler import WorkflowCompiler
        from src.orchestration.checkpoint_manager import CheckpointManager
        from src.orchestration.job_execution_engine import JobExecutionEngine
        from src.realtime.job_control import JobController
        
        # Initialize engine
        print("  1. Initializing engine...")
        engine = get_engine()
        print("     ✓ Engine initialized")
        
        # Initialize job execution components
        print("  2. Initializing event bus...")
        event_bus = EventBus()
        print("     ✓ EventBus initialized")
        
        print("  3. Initializing template registry...")
        template_registry = TemplateRegistry()
        print(f"     ✓ TemplateRegistry initialized with {len(template_registry.templates)} templates")
        
        print("  4. Initializing workflow compiler...")
        workflow_compiler = WorkflowCompiler(template_registry, event_bus)
        print("     ✓ WorkflowCompiler initialized")
        
        print("  5. Initializing checkpoint manager...")
        checkpoint_manager = CheckpointManager()
        print("     ✓ CheckpointManager initialized")
        
        print("  6. Initializing job execution engine...")
        job_engine = JobExecutionEngine(workflow_compiler, checkpoint_manager)
        print("     ✓ JobExecutionEngine initialized")
        
        print("  7. Initializing job controller...")
        job_controller = JobController()  # No parameters!
        print("     ✓ JobController initialized")
        
        # Test web app setup
        print("  8. Setting up web app...")
        from src.web.app import set_execution_engine
        set_execution_engine(job_engine, job_controller)
        print("     ✓ Web app configured")
        
        print("\n✅ All components initialized successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_job_controller():
    """Test JobController specifically."""
    print("\nTesting JobController...")
    
    try:
        from src.realtime.job_control import JobController, get_controller
        
        # Test direct instantiation
        print("  Testing direct instantiation...")
        controller = JobController()
        print("     ✓ JobController() works")
        
        # Test singleton pattern
        print("  Testing singleton pattern...")
        singleton = get_controller()
        print("     ✓ get_controller() works")
        
        # Test job creation
        print("  Testing job operations...")
        job_control = controller.create_job("test_job_123")
        print(f"     ✓ Created job: {job_control.job_id}")
        
        # Test state management
        controller.pause_job("test_job_123")
        state = controller.states.get("test_job_123")
        print(f"     ✓ Job state: {state}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ JobController test failed: {e}")
        return False

def test_service_fixes():
    """Test that service fixes are properly integrated."""
    print("\nTesting service fixes integration...")
    
    try:
        from src.services.services import (
            NoMockGate,
            SEOSchemaGate,
            PrerequisitesNormalizer,
            PyTrendsGuard,
            TopicIdentificationFallback,
            BlogSwitchPolicy,
            RunToResultGuarantee
        )
        
        print("  ✓ NoMockGate imported")
        print("  ✓ SEOSchemaGate imported")
        print("  ✓ PrerequisitesNormalizer imported")
        print("  ✓ PyTrendsGuard imported")
        print("  ✓ TopicIdentificationFallback imported")
        print("  ✓ BlogSwitchPolicy imported")
        print("  ✓ RunToResultGuarantee imported")
        
        # Test basic functionality
        gate = NoMockGate()
        assert gate.contains_mock("TODO: Add content") == True
        assert gate.contains_mock("Real content here") == False
        print("  ✓ NoMockGate works correctly")
        
        meta = SEOSchemaGate.coerce_and_fill({"title": "Test"})
        assert "slug" in meta
        assert "seoTitle" in meta
        print("  ✓ SEOSchemaGate works correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Service fixes test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("STARTUP SEQUENCE VERIFICATION")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Initialization", test_initialization()))
    results.append(("JobController", test_job_controller()))
    results.append(("Service Fixes", test_service_fixes()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Web UI should start successfully!")
    else:
        print("❌ Some tests failed - Please check the errors above")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
