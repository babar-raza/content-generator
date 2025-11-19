#!/usr/bin/env python3
"""UCOP Deployment Readiness Checklist

Runs comprehensive checks to validate deployment readiness.
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")


def print_check(name, passed, details=""):
    """Print check result."""
    if passed:
        symbol = f"{Colors.GREEN}✓{Colors.END}"
        status = f"{Colors.GREEN}PASS{Colors.END}"
    else:
        symbol = f"{Colors.RED}✗{Colors.END}"
        status = f"{Colors.RED}FAIL{Colors.END}"

    print(f"{symbol} {name:<50} {status}")
    if details:
        print(f"  {Colors.YELLOW}{details}{Colors.END}")


def run_command(cmd, timeout=300):
    """Run command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def check_python_version():
    """Check Python version."""
    print_header("Environment Checks")

    success, stdout, _ = run_command("python --version")
    if success and "3.1" in stdout:
        print_check("Python 3.10+ installed", True, stdout.strip())
        return True
    else:
        print_check("Python 3.10+ installed", False, "Python 3.10+ required")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    required = [
        'langgraph', 'fastapi', 'uvicorn', 'chromadb',
        'sentence_transformers', 'pydantic', 'pytest',
        'pytest-cov', 'httpx'
    ]

    success, stdout, _ = run_command("pip list")
    installed = stdout.lower()

    all_installed = True
    for pkg in required:
        is_installed = pkg.replace('_', '-').lower() in installed
        print_check(f"Package: {pkg}", is_installed)
        all_installed = all_installed and is_installed

    return all_installed


def check_syntax():
    """Check for Python syntax errors."""
    print_header("Code Quality Checks")

    success, stdout, stderr = run_command("python -m py_compile src/**/*.py")

    if "SyntaxError" in stderr or "invalid syntax" in stderr:
        print_check("No syntax errors", False, "Syntax errors found")
        return False
    else:
        print_check("No syntax errors", True)
        return True


def check_imports():
    """Check if main modules can be imported."""
    test_imports = [
        "import src.core",
        "import src.engine",
        "import src.orchestration",
        "import src.services",
        "import src.web",
    ]

    all_passed = True
    for test_import in test_imports:
        success, stdout, stderr = run_command(f"python -c \"{test_import}\"")
        module = test_import.split()[1]

        if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
            print_check(f"Import: {module}", False, stderr[:100])
            all_passed = False
        else:
            print_check(f"Import: {module}", True)

    return all_passed


def check_merge_conflicts():
    """Check for unresolved merge conflicts."""
    conflict_markers = ["<<<<<<<", "=======", ">>>>>>>"]

    all_clean = True
    for marker in conflict_markers:
        success, stdout, _ = run_command(f"find src -name '*.py' -exec grep -l '{marker}' {{}} \\;")
        if stdout.strip():
            print_check(f"No merge conflicts ({marker})", False, f"Found in: {stdout[:100]}")
            all_clean = False

    if all_clean:
        print_check("No merge conflicts", True)

    return all_clean


def run_tests():
    """Run test suite."""
    print_header("Test Execution")

    # Run tests with coverage
    success, stdout, stderr = run_command(
        "python -m pytest tests/ --co -q",
        timeout=60
    )

    if not success:
        print_check("Test collection", False, "Failed to collect tests")
        return False

    # Extract test count
    lines = stdout.strip().split('\n')
    test_count = 0
    for line in lines:
        if "tests collected" in line or "test collected" in line:
            parts = line.split()
            test_count = int(parts[0])
            break

    print_check("Test collection", test_count > 0, f"{test_count} tests collected")

    if test_count == 0:
        return False

    # Run actual tests
    print(f"\n{Colors.YELLOW}Running {test_count} tests... (this may take a while){Colors.END}")

    success, stdout, stderr = run_command(
        "python -m pytest tests/ --cov=src --cov-report=term --ignore=tests/e2e/ -q --tb=no",
        timeout=600
    )

    # Parse results
    passed = failed = skipped = errors = 0
    coverage = 0

    for line in stdout.split('\n'):
        if "passed" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if "passed" in part and i > 0:
                    try:
                        passed = int(parts[i-1])
                    except:
                        pass
                elif "failed" in part and i > 0:
                    try:
                        failed = int(parts[i-1])
                    except:
                        pass
                elif "skipped" in part and i > 0:
                    try:
                        skipped = int(parts[i-1])
                    except:
                        pass
                elif "error" in part and i > 0:
                    try:
                        errors = int(parts[i-1])
                    except:
                        pass

        if "TOTAL" in line and "%" in line:
            parts = line.split()
            for part in parts:
                if "%" in part:
                    try:
                        coverage = int(part.replace('%', ''))
                    except:
                        pass

    total = passed + failed + skipped + errors
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"\n{Colors.BOLD}Test Results:{Colors.END}")
    print(f"  Passed:  {passed}/{total} ({pass_rate:.1f}%)")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")
    print(f"  Coverage: {coverage}%")

    print_check("Tests passing > 90%", pass_rate >= 90, f"{pass_rate:.1f}% pass rate")
    print_check("Code coverage > 85%", coverage >= 85, f"{coverage}% coverage")

    return pass_rate >= 90 and coverage >= 85


def check_config_files():
    """Check for required configuration files."""
    print_header("Configuration Checks")

    required_configs = [
        "config/agents.yaml",
        "config/workflows.yaml",
        "config/prompts.yaml",
    ]

    all_exist = True
    for config_file in required_configs:
        path = Path(config_file)
        exists = path.exists()
        print_check(f"Config: {config_file}", exists)
        all_exist = all_exist and exists

    return all_exist


def check_cli():
    """Check if CLI works."""
    print_header("CLI Checks")

    success, stdout, stderr = run_command("python ucop_cli.py --help", timeout=30)

    if success and "usage" in stdout.lower():
        print_check("CLI help command", True)
        return True
    else:
        print_check("CLI help command", False, stderr[:100])
        return False


def check_documentation():
    """Check if documentation exists."""
    print_header("Documentation Checks")

    docs = [
        "README.md",
        "docs/README.md",
        "docs/getting-started.md",
        "docs/architecture.md",
    ]

    all_exist = True
    for doc in docs:
        path = Path(doc)
        exists = path.exists()
        print_check(f"Doc: {doc}", exists)
        all_exist = all_exist and exists

    return all_exist


def generate_report(results):
    """Generate final deployment readiness report."""
    print_header("Deployment Readiness Summary")

    total = len(results)
    passed = sum(results.values())
    percentage = (passed / total * 100) if total > 0 else 0

    print(f"\n{Colors.BOLD}Overall Score: {passed}/{total} ({percentage:.1f}%){Colors.END}\n")

    for check, result in results.items():
        print_check(check, result)

    print(f"\n{Colors.BOLD}Deployment Status:{Colors.END}")

    if percentage >= 95:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ READY FOR PRODUCTION DEPLOYMENT{Colors.END}")
        return 0
    elif percentage >= 80:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ READY FOR STAGING DEPLOYMENT{Colors.END}")
        print(f"{Colors.YELLOW}  Minor issues need to be resolved before production{Colors.END}")
        return 1
    elif percentage >= 60:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ NOT READY - IN PROGRESS{Colors.END}")
        print(f"{Colors.YELLOW}  Significant work remaining{Colors.END}")
        return 2
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ NOT READY FOR DEPLOYMENT{Colors.END}")
        print(f"{Colors.RED}  Critical issues must be resolved{Colors.END}")
        return 3


def main():
    """Run all deployment readiness checks."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║           UCOP DEPLOYMENT READINESS CHECKLIST                      ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {}

    # Run all checks
    results["Python 3.10+"] = check_python_version()
    results["Dependencies installed"] = check_dependencies()
    results["No syntax errors"] = check_syntax()
    results["Imports working"] = check_imports()
    results["No merge conflicts"] = check_merge_conflicts()
    results["Configuration files"] = check_config_files()
    results["CLI functional"] = check_cli()
    results["Documentation exists"] = check_documentation()
    results["Tests passing"] = run_tests()

    # Generate final report
    exit_code = generate_report(results)

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
