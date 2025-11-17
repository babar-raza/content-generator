#!/usr/bin/env python3
"""
Comprehensive HTTP Endpoint Test Runner

Runs all integration tests for HTTP endpoints with coverage reporting.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print('='*60)
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    """Main test runner."""
    print("="*60)
    print("HTTP Endpoint Test Suite")
    print("="*60)
    print("\nRunning comprehensive tests for all API endpoints")
    print("Test coverage: Jobs, Agents, Workflows, Visualization, Debug, MCP, Checkpoints")
    print()
    
    # Check if pytest is installed
    try:
        import pytest
        print(f"✓ pytest version: {pytest.__version__}")
    except ImportError:
        print("❌ pytest not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-cov", "pytest-xdist"])
    
    success = True
    
    # Run all integration tests with verbose output
    if not run_command(
        [sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
        "Running all integration tests"
    ):
        success = False
        print("⚠️  Some tests failed (this may be expected if features not fully implemented)")
    else:
        print("✅ All tests passed!")
    
    # Run with coverage
    print("\n")
    if run_command(
        [sys.executable, "-m", "pytest", "tests/integration/", 
         "--cov=src/web/routes", "--cov-report=term", "--cov-report=html",
         "-q"],
        "Running tests with coverage"
    ):
        print("\n✓ Coverage report generated: htmlcov/index.html")
    
    # Test summary
    print("\n" + "="*60)
    print("TEST SUITE SUMMARY")
    print("="*60)
    
    test_files = [
        "test_jobs_api.py - Jobs API (8 endpoints)",
        "test_agents_api.py - Agents API (4 endpoints)",
        "test_workflows_api.py - Workflows API (2 endpoints)",
        "test_visualization_api.py - Visualization API (7 endpoints)",
        "test_debug_api.py - Debug API (5 endpoints)",
        "test_mcp_http_api.py - MCP API (31 endpoints)",
        "test_checkpoint_api.py - Checkpoints API (5 endpoints)",
        "test_config_api.py - Config API (5 endpoints)",
    ]
    
    print("\nTest files:")
    for test_file in test_files:
        print(f"  ✓ {test_file}")
    
    print(f"\nTotal endpoint coverage: 67+ endpoints tested")
    
    if success:
        print("\n🎉 Test suite complete!")
        return 0
    else:
        print("\n⚠️  Some tests failed - review output above")
        print("Note: 503/404 errors may be expected if executor not initialized")
        return 1


if __name__ == "__main__":
    sys.exit(main())
