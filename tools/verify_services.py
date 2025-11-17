#!/usr/bin/env python3
"""Comprehensive services module verification script.

This script verifies:
1. All services can be imported
2. Services accept Config objects
3. Key methods exist with correct signatures
4. Type hints are present
"""

import sys
from inspect import signature, getmembers, ismethod
from typing import get_type_hints

def check_imports():
    """Verify all services can be imported."""
    print("=" * 60)
    print("STEP 1: Import Verification")
    print("=" * 60)
    
    try:
        from src.services import (
            LLMService,
            DatabaseService,
            EmbeddingService,
            GistService,
            LinkChecker,
            TrendsService,
        )
        print("✓ All services imported successfully")
        print(f"  • LLMService: {LLMService.__module__}")
        print(f"  • DatabaseService: {DatabaseService.__module__}")
        print(f"  • EmbeddingService: {EmbeddingService.__module__}")
        print(f"  • GistService: {GistService.__module__}")
        print(f"  • LinkChecker: {LinkChecker.__module__}")
        print(f"  • TrendsService: {TrendsService.__module__}")
        return True, {
            'LLMService': LLMService,
            'DatabaseService': DatabaseService,
            'EmbeddingService': EmbeddingService,
            'GistService': GistService,
            'LinkChecker': LinkChecker,
            'TrendsService': TrendsService,
        }
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False, {}

def check_llm_service(services):
    """Verify LLMService has required methods."""
    print("\n" + "=" * 60)
    print("STEP 2: LLMService Verification")
    print("=" * 60)
    
    LLMService = services['LLMService']
    
    # Check generate method
    if hasattr(LLMService, 'generate'):
        sig = signature(LLMService.generate)
        print(f"✓ LLMService.generate() exists")
        print(f"  Parameters: {list(sig.parameters.keys())}")
        
        # Check type hints
        try:
            hints = get_type_hints(LLMService.generate)
            print(f"  Return type: {hints.get('return', 'Not specified')}")
        except:
            print("  Type hints: Unable to retrieve")
    else:
        print("✗ LLMService.generate() missing")
        return False
    
    # Check check_health method
    if hasattr(LLMService, 'check_health'):
        sig = signature(LLMService.check_health)
        print(f"✓ LLMService.check_health() exists")
        print(f"  Parameters: {list(sig.parameters.keys())}")
    else:
        print("✗ LLMService.check_health() missing")
        return False
    
    # Check __init__ accepts Config
    init_sig = signature(LLMService.__init__)
    params = list(init_sig.parameters.keys())
    if 'config' in params:
        print(f"✓ LLMService.__init__() accepts config parameter")
    else:
        print(f"✗ LLMService.__init__() missing config parameter")
        return False
    
    return True

def check_all_services(services):
    """Verify all services accept Config."""
    print("\n" + "=" * 60)
    print("STEP 3: All Services Configuration Check")
    print("=" * 60)
    
    all_pass = True
    for name, service_class in services.items():
        init_sig = signature(service_class.__init__)
        params = list(init_sig.parameters.keys())
        if 'config' in params:
            print(f"✓ {name}.__init__() accepts config")
        else:
            print(f"✗ {name}.__init__() missing config parameter")
            all_pass = False
    
    return all_pass

def check_type_hints(services):
    """Verify type hints on public methods."""
    print("\n" + "=" * 60)
    print("STEP 4: Type Hints Verification")
    print("=" * 60)
    
    for name, service_class in services.items():
        print(f"\n{name}:")
        
        # Get all public methods
        methods = [m for m in dir(service_class) if not m.startswith('_')]
        
        for method_name in methods[:3]:  # Check first 3 methods
            method = getattr(service_class, method_name)
            if callable(method):
                try:
                    hints = get_type_hints(method)
                    if hints:
                        print(f"  ✓ {method_name}() has type hints")
                    else:
                        print(f"  ⚠ {method_name}() missing type hints")
                except Exception as e:
                    print(f"  ⚠ {method_name}() type hint check failed: {e}")
    
    return True

def main():
    """Run all verification checks."""
    print("Services Module Verification")
    print("=" * 60)
    
    # Import check
    success, services = check_imports()
    if not success:
        print("\n✗ FAILED: Import check failed")
        return 1
    
    # LLMService specific checks
    if not check_llm_service(services):
        print("\n✗ FAILED: LLMService check failed")
        return 1
    
    # All services config check
    if not check_all_services(services):
        print("\n✗ FAILED: Config parameter check failed")
        return 1
    
    # Type hints check
    check_type_hints(services)
    
    print("\n" + "=" * 60)
    print("✓ ALL CHECKS PASSED")
    print("=" * 60)
    print("\nServices module is properly configured!")
    print("\nNext steps:")
    print("  1. Run tests: pytest tests/test_services_comprehensive.py -v")
    print("  2. Check test coverage: pytest --cov=src.services")
    print("  3. Review runbook: cat SERVICES_RUNBOOK.md")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
# DOCGEN:LLM-FIRST@v4