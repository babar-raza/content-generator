#!/usr/bin/env python3
"""Verification script for parallel execution implementation."""

import ast
import sys
from pathlib import Path


def verify_syntax(file_path: Path) -> bool:
    """Verify Python file has valid syntax."""
    try:
        with open(file_path, 'r') as f:
            ast.parse(f.read())
        print(f"✓ {file_path}: Valid syntax")
        return True
    except SyntaxError as e:
        print(f"✗ {file_path}: Syntax error: {e}")
        return False


def verify_config(config_path: Path) -> bool:
    """Verify config has parallel execution settings."""
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        checks = [
            ('enable_parallel_execution' in content, "enable_parallel_execution setting found"),
            ('max_parallel_agents' in content, "max_parallel_agents setting found"),
        ]
        
        all_passed = True
        for passed, message in checks:
            if passed:
                print(f"✓ {config_path}: {message}")
            else:
                print(f"✗ {config_path}: Missing {message}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ {config_path}: Error reading file: {e}")
        return False


def verify_parallel_executor(py_path: Path) -> bool:
    """Verify parallel executor has required methods."""
    try:
        with open(py_path, 'r') as f:
            content = f.read()
        
        checks = [
            ('class ParallelExecutor' in content, "ParallelExecutor class found"),
            ('def execute_parallel' in content, "execute_parallel method found"),
            ('def identify_parallel_groups' in content, "identify_parallel_groups method found"),
            ('class ThreadSafeState' in content, "ThreadSafeState class found"),
            ('ThreadPoolExecutor' in content, "ThreadPoolExecutor import found"),
            ('wait(' in content or 'wait (' in content, "wait() for better timeout handling"),
        ]
        
        all_passed = True
        for passed, message in checks:
            if passed:
                print(f"✓ {py_path}: {message}")
            else:
                print(f"✗ {py_path}: Missing {message}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ {py_path}: Error reading file: {e}")
        return False


def verify_production_engine(py_path: Path) -> bool:
    """Verify production engine integration."""
    try:
        with open(py_path, 'r') as f:
            content = f.read()
        
        checks = [
            ('_execute_parallel_pipeline' in content, "_execute_parallel_pipeline method found"),
            ('_execute_sequential_pipeline' in content, "_execute_sequential_pipeline method found"),
            ('self.parallel_executor' in content, "parallel_executor attribute found"),
            ('ParallelExecutor' in content, "ParallelExecutor import found"),
        ]
        
        # Check that the execute_pipeline method properly delegates to parallel or sequential
        # by looking for the if/else pattern
        has_proper_delegation = (
            'if use_parallel:' in content and
            '_execute_parallel_pipeline(' in content and
            'else:' in content and
            '_execute_sequential_pipeline(' in content
        )
        
        if has_proper_delegation:
            print(f"✓ {py_path}: Proper parallel/sequential delegation")
            checks.append((True, "Proper delegation pattern"))
        else:
            print(f"✗ {py_path}: Missing proper parallel/sequential delegation")
            checks.append((False, "Proper delegation pattern"))
        
        all_passed = True
        for passed, message in checks:
            if passed:
                print(f"✓ {py_path}: {message}")
            else:
                print(f"✗ {py_path}: Missing {message}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ {py_path}: Error reading file: {e}")
        return False


def verify_tests(test_path: Path) -> bool:
    """Verify test file has required tests."""
    try:
        with open(test_path, 'r') as f:
            content = f.read()
        
        checks = [
            ('test_parallel_execution_faster_than_sequential' in content, 
             "Speedup test found"),
            ('test_parallel_executor_initialization' in content, 
             "Initialization test found"),
            ('test_thread_safe_state' in content, 
             "Thread safety test found"),
            ('test_parallel_with_failure' in content, 
             "Failure handling test found"),
            ('test_benchmark_3_agents_parallel' in content, 
             "Benchmark test found"),
            ('assertGreater(speedup, 2.0' in content, 
             "2× speedup assertion found"),
        ]
        
        all_passed = True
        for passed, message in checks:
            if passed:
                print(f"✓ {test_path}: {message}")
            else:
                print(f"✗ {test_path}: Missing {message}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ {test_path}: Error reading file: {e}")
        return False


def main():
    """Run all verifications."""
    print("="*70)
    print("PARALLEL EXECUTION IMPLEMENTATION VERIFICATION")
    print("="*70)
    print()
    
    base_path = Path(__file__).parent
    
    files_to_check = [
        (base_path / 'src' / 'orchestration' / 'parallel_executor.py', verify_syntax),
        (base_path / 'src' / 'orchestration' / 'parallel_executor.py', verify_parallel_executor),
        (base_path / 'src' / 'orchestration' / 'production_execution_engine.py', verify_syntax),
        (base_path / 'src' / 'orchestration' / 'production_execution_engine.py', verify_production_engine),
        (base_path / 'tests' / 'performance' / 'test_parallel_speedup.py', verify_syntax),
        (base_path / 'tests' / 'performance' / 'test_parallel_speedup.py', verify_tests),
        (base_path / 'config' / 'main.yaml', verify_config),
    ]
    
    all_passed = True
    for file_path, verify_func in files_to_check:
        if not file_path.exists():
            print(f"✗ {file_path}: File not found")
            all_passed = False
            continue
        
        if not verify_func(file_path):
            all_passed = False
        print()
    
    # Check for documentation
    docs = [
        base_path / 'PARALLEL_EXECUTION_RUNBOOK.md',
        base_path / 'CHANGES.md',
    ]
    
    print("="*70)
    print("DOCUMENTATION")
    print("="*70)
    for doc in docs:
        if doc.exists():
            print(f"✓ {doc.name}: Found")
        else:
            print(f"✗ {doc.name}: Missing")
            all_passed = False
    print()
    
    # Final result
    print("="*70)
    if all_passed:
        print("✓ ALL CHECKS PASSED")
        print("="*70)
        print()
        print("Next steps:")
        print("1. Review CHANGES.md for detailed changes")
        print("2. Review PARALLEL_EXECUTION_RUNBOOK.md for usage guide")
        print("3. Run tests: pytest tests/performance/test_parallel_speedup.py -v")
        print("4. Enable parallel execution in config/main.yaml")
        print("5. Benchmark your workflow to measure speedup")
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print("="*70)
        print()
        print("Please review the errors above and ensure all files are present and correct.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
