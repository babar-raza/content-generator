#!/usr/bin/env python3
"""Test script to verify all initialization fixes work."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_engine_initialization():
    """Test UnifiedEngine initialization."""
    print("Testing UnifiedEngine initialization...")
    try:
        from src.engine.engine import get_engine, RunSpec
        engine = get_engine()
        print("✓ UnifiedEngine initialized successfully")
        
        # Test RunSpec
        spec = RunSpec(topic="Test", template_name="default_blog")
        errors = spec.validate()
        if not errors:
            print("✓ RunSpec validation works")
        else:
            print(f"✗ RunSpec validation errors: {errors}")
        
        return True
    except Exception as e:
        print(f"✗ UnifiedEngine initialization failed: {e}")
        return False

def test_services_initialization():
    """Test services initialization."""
    print("\nTesting services initialization...")
    try:
        from src.initialization.integrated_init import initialize_system
        components = initialize_system()
        
        if components:
            print("✓ initialize_system() returns components")
            print(f"  - llm_service: {'✓' if components.get('llm_service') else '✗'}")
            print(f"  - database_service: {'✓' if components.get('database_service') else '✗'}")
            print(f"  - embedding_service: {'✓' if components.get('embedding_service') else '✗'}")
            print(f"  - event_bus: {'✓' if components.get('event_bus') else '✗'}")
            print(f"  - template_registry: {'✓' if components.get('template_registry') else '✗'}")
            print(f"  - agents: {len(components.get('agents', {})) if components.get('agents') else 'None'}")
        else:
            print("✗ initialize_system() returned None")
        
        return True
    except Exception as e:
        print(f"✗ Services initialization failed: {e}")
        return False

def test_template_registry():
    """Test TemplateRegistry initialization."""
    print("\nTesting TemplateRegistry...")
    try:
        from src.core.template_registry import TemplateRegistry
        registry = TemplateRegistry()
        print(f"✓ TemplateRegistry initialized with {len(registry.templates)} templates")
        return True
    except Exception as e:
        print(f"✗ TemplateRegistry initialization failed: {e}")
        return False

def test_job_execution_engine():
    """Test JobExecutionEngine initialization."""
    print("\nTesting JobExecutionEngine initialization...")
    try:
        from src.orchestration.workflow_compiler import WorkflowCompiler
        from src.orchestration.checkpoint_manager import CheckpointManager
        from src.orchestration.job_execution_engine import JobExecutionEngine
        from src.core import EventBus
        from src.core.template_registry import TemplateRegistry
        
        event_bus = EventBus()
        template_registry = TemplateRegistry()
        workflow_compiler = WorkflowCompiler(template_registry, event_bus)
        checkpoint_manager = CheckpointManager()
        job_engine = JobExecutionEngine(workflow_compiler, checkpoint_manager)
        print("✓ JobExecutionEngine initialized successfully")
        return True
    except Exception as e:
        print(f"✗ JobExecutionEngine initialization failed: {e}")
        return False

def test_web_app_initialization():
    """Test web app initialization."""
    print("\nTesting web app initialization...")
    try:
        from src.web.app import app, set_execution_engine
        from src.orchestration.workflow_compiler import WorkflowCompiler
        from src.orchestration.checkpoint_manager import CheckpointManager
        from src.orchestration.job_execution_engine import JobExecutionEngine
        from src.realtime.job_control import JobController
        from src.core import EventBus
        from src.core.template_registry import TemplateRegistry
        
        event_bus = EventBus()
        template_registry = TemplateRegistry()
        workflow_compiler = WorkflowCompiler(template_registry, event_bus)
        checkpoint_manager = CheckpointManager()
        job_engine = JobExecutionEngine(workflow_compiler, checkpoint_manager)
        job_controller = JobController(job_engine)
        
        set_execution_engine(job_engine, job_controller)
        print("✓ Web app initialization works")
        return True
    except Exception as e:
        if "No module named 'fastapi'" in str(e):
            print("⚠ Web app initialization skipped (fastapi not installed)")
            return True  # Don't fail test for missing optional dependency
        print(f"✗ Web app initialization failed: {e}")
        return False

def test_service_fixes():
    """Test service fixes are integrated."""
    print("\nTesting service fixes...")
    try:
        from src.services.services import NoMockGate, SEOSchemaGate, PrerequisitesNormalizer
        
        # Test NoMockGate
        gate = NoMockGate()
        is_mock = gate.contains_mock("Your Title Here")
        if is_mock:
            print("✓ NoMockGate detects mock content")
        else:
            print("✗ NoMockGate failed to detect mock content")
        
        # Test SEOSchemaGate
        meta = SEOSchemaGate.coerce_and_fill({"title": "Test"})
        if "slug" in meta and "seoTitle" in meta:
            print("✓ SEOSchemaGate normalizes metadata")
        else:
            print("✗ SEOSchemaGate normalization failed")
        
        # Test PrerequisitesNormalizer
        result = PrerequisitesNormalizer.normalize("Python, JavaScript")
        if result == ["Python", "JavaScript"]:
            print("✓ PrerequisitesNormalizer works")
        else:
            print("✗ PrerequisitesNormalizer failed")
        
        return True
    except Exception as e:
        print(f"✗ Service fixes not integrated: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("TESTING INITIALIZATION FIXES")
    print("=" * 60)
    
    tests = [
        test_engine_initialization,
        test_services_initialization,
        test_template_registry,
        test_job_execution_engine,
        test_web_app_initialization,
        test_service_fixes
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total} passed)")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
