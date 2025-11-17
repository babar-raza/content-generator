#!/usr/bin/env python3
"""System Validation Script - Phase 7

Validates the integrated system without requiring external dependencies to be installed.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_core_imports():
    """Test core module imports."""
    print("\n" + "="*60)
    print("CORE MODULES")
    print("="*60)
    
    results = []
    
    try:
        from src.core import Config, EventBus, Agent, AgentEvent, AgentContract
        print("✓ Core imports successful")
        results.append(True)
    except Exception as e:
        print(f"✗ Core imports failed: {e}")
        results.append(False)
    
    try:
        from src.core.contracts import CapabilitySpec, Bid, WorkSpec
        print("✓ Core contracts extended features")
        results.append(True)
    except Exception as e:
        print(f"✗ Core contracts failed: {e}")
        results.append(False)
    
    try:
        from src.core.event_bus import EventBus
        from src.core.agent_base import Agent
        from src.core.config import Config
        print("✓ Core individual modules")
        results.append(True)
    except Exception as e:
        print(f"✗ Core modules failed: {e}")
        results.append(False)
    
    return all(results)

def test_mesh_imports():
    """Test mesh layer imports - ARCHIVED."""
    print("\n" + "="*60)
    print("MESH LAYER (ARCHIVED)")
    print("="*60)
    print("⚠ Mesh system archived 2025-11-13 - skipping tests")
    return True

def test_agents_structure():
    """Test agent structure."""
    print("\n" + "="*60)
    print("AGENTS STRUCTURE")
    print("="*60)
    
    agent_dirs = [
        "src/agents/ingestion",
        "src/agents/research",
        "src/agents/content",
        "src/agents/code",
        "src/agents/seo",
        "src/agents/publishing",
        "src/agents/support"
    ]
    
    results = []
    for agent_dir in agent_dirs:
        exists = Path(agent_dir).is_dir()
        status = "✓" if exists else "✗"
        print(f"{status} {agent_dir}")
        results.append(exists)
    
    return all(results)

def test_utils_imports():
    """Test utility imports."""
    print("\n" + "="*60)
    print("UTILITIES")
    print("="*60)
    
    results = []
    
    try:
        from src.utils.content_utils import extract_code_blocks
        print("✓ Utils - Content utilities")
        results.append(True)
    except Exception as e:
        print(f"✗ Utils - Content: {e}")
        results.append(False)
    
    try:
        from src.utils.resilience import ResilienceManager
        print("✓ Utils - Resilience")
        results.append(True)
    except Exception as e:
        print(f"✗ Utils - Resilience: {e}")
        results.append(False)
    
    try:
        from src.utils.tone_utils import get_section_config
        print("✓ Utils - Tone")
        results.append(True)
    except Exception as e:
        print(f"✗ Utils - Tone: {e}")
        results.append(False)
    
    return all(results)

def test_file_structure():
    """Test file structure."""
    print("\n" + "="*60)
    print("FILE STRUCTURE")
    print("="*60)
    
    required_files = {
        "Core": [
            "src/core/contracts.py",
            "src/core/event_bus.py",
            "src/core/agent_base.py",
            "src/core/config.py",
        ],
        "Mesh": [
            "src/mesh/capability_registry.py",
            "src/mesh/runtime_async.py",
            "src/mesh/cache/cache.py",
        ],
        "Orchestration": [
            "src/orchestration/workflow_compiler.py",
            "src/orchestration/job_execution_engine.py",
            "src/orchestration/ops_console.py",
        ],
        "Services": [
            "src/services/services.py",
        ],
        "Config": [
            "config/tone.json",
            "templates/blog_templates.yaml",
        ],
        "Root": [
            "src/main.py",
            "requirements.txt",
            "setup.py",
        ]
    }
    
    all_passed = True
    for category, files in required_files.items():
        print(f"\n{category}:")
        for file_path in files:
            exists = Path(file_path).exists()
            status = "✓" if exists else "✗"
            print(f"  {status} {file_path}")
            if not exists:
                all_passed = False
    
    return all_passed

def test_main_module():
    """Test that main module can be imported."""
    print("\n" + "="*60)
    print("MAIN MODULE")
    print("="*60)
    
    try:
        # This will fail if sentence_transformers is missing, but syntax should be OK
        import src.main
        print("✓ Main module syntax OK")
        return True
    except ModuleNotFoundError as e:
        # Expected if dependencies not installed
        if "sentence_transformers" in str(e) or "langgraph" in str(e):
            print(f"⚠ Main module syntax OK (missing dependency: {e})")
            return True
        else:
            print(f"✗ Main module failed: {e}")
            return False
    except Exception as e:
        print(f"✗ Main module syntax error: {e}")
        return False

def count_files():
    """Count project files."""
    print("\n" + "="*60)
    print("PROJECT STATISTICS")
    print("="*60)
    
    py_files = list(Path("src").rglob("*.py"))
    test_files = list(Path("tests").rglob("*.py"))
    config_files = list(Path("config").glob("*")) + list(Path("templates").glob("*"))
    
    print(f"Python files: {len(py_files)}")
    print(f"Test files: {len(test_files)}")
    print(f"Config files: {len(config_files)}")
    
    # Count LOC
    total_lines = 0
    for py_file in py_files:
        try:
            with open(py_file) as f:
                total_lines += len(f.readlines())
        except:
            pass
    
    print(f"Total Python LOC: {total_lines:,}")

def main():
    """Run all validations."""
    print("="*60)
    print("PHASE 7: TESTING & VALIDATION")
    print("System Validation Script")
    print("="*60)
    
    results = {
        "Core Imports": test_core_imports(),
        "Mesh Imports": test_mesh_imports(),
        "Agents Structure": test_agents_structure(),
        "Utils Imports": test_utils_imports(),
        "File Structure": test_file_structure(),
        "Main Module": test_main_module(),
    }
    
    count_files()
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    for category, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{category}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL VALIDATIONS PASSED")
        print("System is ready for Phase 8 (Documentation)")
    else:
        print("⚠ SOME VALIDATIONS FAILED")
        print("Review errors above")
    print("="*60)
    
    # Update integration state
    state = {
        "phase": 7,
        "status": "testing_complete" if all_passed else "testing_with_warnings",
        "validation_results": results,
        "ready_for_phase_8": all_passed
    }
    
    with open(".integration-state.json", "w") as f:
        json.dump(state, f, indent=2)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
# DOCGEN:LLM-FIRST@v4