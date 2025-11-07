#!/usr/bin/env python3
"""Import validation script for Phase 7."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def validate_imports():
    """Validate all critical imports."""
    print("="*60)
    print("IMPORT VALIDATION - Phase 7")
    print("="*60)
    
    results = []
    
    tests = [
        ("Core contracts", "from src.core.contracts import AgentEvent, AgentContract, DataContract, CapabilitySpec, Bid"),
        ("Core event bus", "from src.core.event_bus import EventBus"),
        ("Core agent base", "from src.core.agent_base import Agent, SelfCorrectingAgent"),
        ("Core config", "from src.core.config import Config, LLMConfig, DatabaseConfig, MeshConfig, OrchestrationConfig"),
        ("Core unified", "from src.core import AgentEvent, EventBus, Agent, Config"),
        ("Services - LLM", "from src.services.services import LLMService"),
        ("Services - Database", "from src.services.services import DatabaseService"),
        ("Services - Full", "from src.services.services import LLMService, DatabaseService, EmbeddingService, GistService"),
        ("MCP Service", "from src.services.mcp_service import MCPService"),
        ("Mesh - Registry", "from src.mesh.capability_registry import CapabilityRegistry"),
        ("Mesh - Runtime", "from src.mesh.runtime_async import AsyncRuntime"),
        ("Mesh - Cache", "from src.mesh.cache.cache import CacheManager"),
        ("Mesh - All", "from src.mesh import CapabilityRegistry, AsyncRuntime, CacheManager"),
        ("Orchestration - Compiler", "from src.orchestration.workflow_compiler import WorkflowCompiler"),
        ("Orchestration - Engine", "from src.orchestration.job_execution_engine import JobExecutionEngine"),
        ("Orchestration - Console", "from src.orchestration.ops_console import OpsConsole"),
        ("Utils - Content", "from src.utils.content_utils import extract_code_blocks"),
        ("Utils - Resilience", "from src.utils.resilience import ResilienceManager"),
        ("Main module", "import src.main"),
    ]
    
    print()
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✓ {name}")
            results.append((name, True, ""))
        except Exception as e:
            error_msg = str(e)[:80]
            print(f"✗ {name}: {error_msg}")
            results.append((name, False, error_msg))
    
    # Summary
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print()
    print("="*60)
    print(f"Import Validation: {passed}/{total} successful")
    
    if passed == total:
        print("✓ ALL IMPORTS PASSED")
    else:
        print("✗ SOME IMPORTS FAILED")
        print("\nFailed imports:")
        for name, success, error in results:
            if not success:
                print(f"  - {name}: {error}")
    
    print("="*60)
    return passed == total

if __name__ == "__main__":
    success = validate_imports()
    sys.exit(0 if success else 1)
