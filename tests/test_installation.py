#!/usr/bin/env python3
"""
UCOP v10 Installation Verification Script
Verifies that all v10 components are properly installed and accessible.
"""

import sys
from pathlib import Path
from typing import List, Tuple

def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")

def check_file_exists(file_path: str) -> Tuple[bool, str]:
    """Check if a file exists."""
    path = Path(file_path)
    if path.exists():
        return True, f"[OK] {file_path}"
    else:
        return False, f"[FAIL] {file_path} - MISSING"

def check_import(module_path: str, item: str) -> Tuple[bool, str]:
    """Check if a module can be imported."""
    try:
        exec(f"from {module_path} import {item}")
        return True, f"[OK] {module_path}.{item}"
    except ImportError as e:
        return False, f"[FAIL] {module_path}.{item} - {str(e)}"

def main():
    """Run all installation checks."""
    print_header("UCOP v10 Installation Verification")
    
    all_passed = True
    
    # Check 1: Core v10 Engine Files
    print_header("1. Checking v10 Engine Files")
    engine_files = [
        "src/engine/__init__.py",
        "src/engine/executor.py",
        "src/engine/input_resolver.py",
        "src/engine/aggregator.py",
        "src/engine/completeness_gate.py",
        "src/engine/context_merger.py",
        "src/engine/agent_tracker.py",
        "src/engine/exceptions.py",
    ]
    
    for file in engine_files:
        passed, message = check_file_exists(file)
        print(message)
        all_passed = all_passed and passed
    
    # Check 2: Enhanced Utilities
    print_header("2. Checking Enhanced Utilities")
    util_files = [
        "src/utils/citation_tracker.py",
        "src/utils/duplication_detector.py",
    ]
    
    for file in util_files:
        passed, message = check_file_exists(file)
        print(message)
        all_passed = all_passed and passed
    
    # Check 3: API Validator
    print_header("3. Checking API Validator")
    validator_files = [
        "src/agents/code/api_validator.py",
    ]
    
    for file in validator_files:
        passed, message = check_file_exists(file)
        print(message)
        all_passed = all_passed and passed
    
    # Check 4: Template Schemas
    print_header("4. Checking Template Schemas")
    schema_files = [
        "templates/schema/blog_template.yaml",
        "templates/schema/code_template.yaml",
    ]
    
    for file in schema_files:
        passed, message = check_file_exists(file)
        print(message)
        all_passed = all_passed and passed
    
    # Check 5: API Reference Data
    print_header("5. Checking API Reference Data")
    data_files = [
        "data/api_reference/python_stdlib.json",
    ]
    
    for file in data_files:
        passed, message = check_file_exists(file)
        print(message)
        all_passed = all_passed and passed
    
    # Check 6: Test Files
    print_header("6. Checking Test Suite")
    test_files = [
        "tests/unit/test_engine.py",
        "tests/integration/test_unified_executor.py",
    ]
    
    for file in test_files:
        passed, message = check_file_exists(file)
        print(message)
        all_passed = all_passed and passed
    
    # Check 7: Modified Files
    print_header("7. Checking Modified Files")
    modified_files = [
        "ucop_cli.py",
        "src/orchestration/job_execution_engine.py",
        "src/web/app.py",
    ]
    
    for file in modified_files:
        passed, message = check_file_exists(file)
        print(message)
        all_passed = all_passed and passed
    
    # Check 8: Import Tests
    print_header("8. Testing Imports")
    
    # Add current directory to path
    sys.path.insert(0, str(Path.cwd()))
    
    imports_to_test = [
        ("src.engine", "UnifiedJobExecutor"),
        ("src.engine", "JobConfig"),
        ("src.engine", "CompletenessGate"),
        ("src.engine", "InputResolver"),
        ("src.engine", "OutputAggregator"),
        ("src.engine", "AgentTracker"),
        ("src.utils.citation_tracker", "CitationTracker"),
        ("src.utils.duplication_detector", "EnhancedDuplicationDetector"),
    ]
    
    for module, item in imports_to_test:
        passed, message = check_import(module, item)
        print(message)
        all_passed = all_passed and passed
    
    # Final Result
    print_header("Installation Verification Result")
    
    if all_passed:
        print("[SUCCESS] All v10 components are properly installed.\n")
        print("Next Steps:")
        print("  1. Run tests: pytest tests/unit/test_engine.py -v")
        print("  2. Try direct CLI: python ucop_cli.py create blog_generation --input 'Test Topic'")
        print("  3. Start web UI: python start_web_ui.py")
        print(f"\n{'=' * 60}\n")
        return 0
    else:
        print("[FAIL] Some components are missing or cannot be imported.\n")
        print("Troubleshooting:")
        print("  1. Ensure you're in the project root directory")
        print("  2. Reinstall: pip install -r requirements.txt")
        print("  3. Check extraction: unzip -l unified_generator_v10_implementation.zip")
        print(f"\n{'=' * 60}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
