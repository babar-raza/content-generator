#!/usr/bin/env python3
"""
Verification script for hot reload implementation.
Checks that all required components are present and functional.
"""

import sys
from pathlib import Path

def check_file_exists(path: str) -> bool:
    """Check if file exists."""
    p = Path(path)
    exists = p.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {path}")
    return exists

def check_imports() -> bool:
    """Check that all modules can be imported."""
    print("\n Checking imports...")
    
    modules = [
        ('src.orchestration.hot_reload', ['HotReloadMonitor', 'ReloadEvent', 'ConfigValidator']),
        ('src.orchestration.agent_scanner', ['AgentScanner']),
    ]
    
    all_ok = True
    for module_name, classes in modules:
        try:
            module = __import__(module_name, fromlist=classes)
            for cls in classes:
                if hasattr(module, cls):
                    print(f"  ✓ {module_name}.{cls}")
                else:
                    print(f"  ✗ {module_name}.{cls} not found")
                    all_ok = False
        except ImportError as e:
            print(f"  ✗ Failed to import {module_name}: {e}")
            all_ok = False
    
    return all_ok

def check_hot_reload_features() -> bool:
    """Check that HotReloadMonitor has required features."""
    print("\n Checking HotReloadMonitor features...")
    
    try:
        from src.orchestration.hot_reload import HotReloadMonitor
        from pathlib import Path
        
        # Check class methods
        required_methods = [
            '__init__',
            'start',
            'stop',
            'register_callback',
            'reload_config_file',
            'get_stats',
            'force_reload',
            '_validate_config',
            '_rollback_config',
            'is_monitored_file',
        ]
        
        all_ok = True
        for method in required_methods:
            if hasattr(HotReloadMonitor, method):
                print(f"  ✓ HotReloadMonitor.{method}")
            else:
                print(f"  ✗ HotReloadMonitor.{method} missing")
                all_ok = False
        
        # Test instantiation
        try:
            monitor = HotReloadMonitor(paths=[Path('.')])
            print(f"  ✓ HotReloadMonitor instantiation")
        except Exception as e:
            print(f"  ✗ HotReloadMonitor instantiation failed: {e}")
            all_ok = False
        
        return all_ok
        
    except ImportError as e:
        print(f"  ✗ Failed to import HotReloadMonitor: {e}")
        return False

def check_validator() -> bool:
    """Check ConfigValidator functionality."""
    print("\n Checking ConfigValidator...")
    
    try:
        from src.orchestration.hot_reload import ConfigValidator
        
        # Test agents config validation
        valid_config = {
            'agents': {
                'test': {'class': 'TestAgent'}
            }
        }
        
        is_valid, error = ConfigValidator.validate_agents_config(valid_config)
        if is_valid:
            print(f"  ✓ ConfigValidator.validate_agents_config")
        else:
            print(f"  ✗ ConfigValidator.validate_agents_config failed: {error}")
            return False
        
        # Test workflows config validation
        valid_workflow = {
            'workflows': {
                'test': {'steps': []}
            }
        }
        
        is_valid, error = ConfigValidator.validate_workflows_config(valid_workflow)
        if is_valid:
            print(f"  ✓ ConfigValidator.validate_workflows_config")
        else:
            print(f"  ✗ ConfigValidator.validate_workflows_config failed: {error}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ ConfigValidator checks failed: {e}")
        return False

def check_agent_scanner() -> bool:
    """Check AgentScanner has trigger_reload method."""
    print("\n Checking AgentScanner integration...")
    
    try:
        from src.orchestration.agent_scanner import AgentScanner
        
        scanner = AgentScanner()
        
        if hasattr(scanner, 'trigger_reload'):
            print(f"  ✓ AgentScanner.trigger_reload")
            return True
        else:
            print(f"  ✗ AgentScanner.trigger_reload missing")
            return False
            
    except Exception as e:
        print(f"  ✗ AgentScanner check failed: {e}")
        return False

def check_tests() -> bool:
    """Check test file structure."""
    print("\n Checking tests...")
    
    test_file = Path('tests/test_config_behavior.py')
    if not test_file.exists():
        print(f"  ✗ Test file not found: {test_file}")
        return False
    
    with open(test_file) as f:
        content = f.read()
    
    test_count = content.count('def test_')
    print(f"  ✓ Found {test_count} test methods")
    
    required_tests = [
        'test_hot_reload',
        'test_debouncing',
        'test_validation_before_apply',
        'test_rollback_on_validation_failure',
        'test_thread_safety',
        'test_websocket_notification',
        'test_no_service_interruption',
    ]
    
    all_found = True
    for test in required_tests:
        if test in content:
            print(f"  ✓ {test}")
        else:
            print(f"  ✗ {test} missing")
            all_found = False
    
    return all_found

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Hot Reload Implementation Verification")
    print("=" * 60)
    
    results = []
    
    # Check files exist
    print("\n Checking files...")
    results.append(check_file_exists('src/orchestration/hot_reload.py'))
    results.append(check_file_exists('src/orchestration/agent_scanner.py'))
    results.append(check_file_exists('start_web.py'))
    results.append(check_file_exists('tests/test_config_behavior.py'))
    results.append(check_file_exists('RUNBOOK_hot_reload.sh'))
    
    # Check imports
    results.append(check_imports())
    
    # Check features
    results.append(check_hot_reload_features())
    results.append(check_validator())
    results.append(check_agent_scanner())
    results.append(check_tests())
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100 if total > 0 else 0
    
    print(f"Verification Results: {passed}/{total} checks passed ({success_rate:.0f}%)")
    
    if all(results):
        print("✓ All verification checks passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some verification checks failed")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
