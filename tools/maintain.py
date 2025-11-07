#!/usr/bin/env python3
"""
UCOP Maintenance Script
Runs tests, coverage, and available linters for the UCOP project.
"""

import sys
import subprocess
import argparse
from pathlib import Path
import json
from datetime import datetime

class UCOPMaintainer:
    """Maintenance utilities for UCOP project."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.reports_dir = self.project_root / "reports"

    def run_command(self, cmd: list, cwd: Path = None) -> tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, f"Command failed: {e}"

    def run_tests(self) -> tuple[bool, str]:
        """Run pytest test suite."""
        print("Running tests...")
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]
        success, output = self.run_command(cmd)

        if success:
            print("Tests passed")
        else:
            print("Tests failed")

        return success, output

    def run_coverage(self) -> tuple[bool, str]:
        """Run coverage analysis."""
        print("Running coverage analysis...")
        self.reports_dir.mkdir(exist_ok=True)

        cmd = [
            sys.executable, "-m", "pytest", "tests/",
            "--cov=src", "--cov-report=term",
            f"--cov-report=json:{self.reports_dir}/coverage.json",
            f"--cov-report=html:{self.reports_dir}/htmlcov"
        ]
        success, output = self.run_command(cmd)

        if success:
            print("Coverage analysis completed")
            # Save coverage text report
            with open(self.reports_dir / "coverage.txt", "w") as f:
                f.write(output)
        else:
            print("Coverage analysis failed")

        return success, output

    def run_linters(self) -> tuple[bool, str]:
        """Run available linters."""
        print("Running linters...")

        linters_output = []
        success = True

        # Try flake8
        print("  Running flake8...")
        flake8_success, flake8_output = self.run_command(["flake8", "src/", "tests/"])
        linters_output.append(f"flake8:\n{flake8_output}")
        if not flake8_success:
            success = False

        # Try mypy
        print("  Running mypy...")
        mypy_success, mypy_output = self.run_command(["mypy", "src/"])
        linters_output.append(f"mypy:\n{mypy_output}")
        if not mypy_success:
            success = False

        # Try black (check mode)
        print("  Running black...")
        black_success, black_output = self.run_command(["black", "--check", "src/", "tests/"])
        linters_output.append(f"black:\n{black_output}")
        if not black_success:
            success = False

        combined_output = "\n\n".join(linters_output)

        if success:
            print("All linters passed")
        else:
            print("Some linters failed")

        return success, combined_output

    def check_dependencies(self) -> tuple[bool, str]:
        """Check if dependencies are installed."""
        print("Checking dependencies...")

        try:
            import pytest
            import fastapi
            import langchain
            import chromadb
            print("Core dependencies installed")
            return True, "All dependencies available"
        except ImportError as e:
            print(f"Missing dependency: {e}")
            return False, f"Missing dependency: {e}"

    def generate_report(self, results: dict) -> str:
        """Generate maintenance report."""
        report = []
        report.append("# UCOP Maintenance Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        # Overall status
        all_passed = all(results.values())
        status = "✅ PASSED" if all_passed else "❌ FAILED"
        report.append(f"Overall Status: {status}")
        report.append("")

        # Individual results
        for check, passed in results.items():
            status = "✅" if passed else "❌"
            report.append(f"{status} {check}")

        report.append("")
        report.append("## Details")
        report.append("")

        # Save detailed results
        details_file = self.reports_dir / "maintenance_details.json"
        with open(details_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        report.append(f"Detailed results saved to: {details_file}")

        return "\n".join(report)

    def run_all(self, skip_linters: bool = False) -> bool:
        """Run all maintenance checks."""
        print("🔧 Starting UCOP maintenance checks...")
        print("=" * 50)

        results = {}

        # Check dependencies
        results["dependencies"], _ = self.check_dependencies()

        # Run tests
        results["tests"], test_output = self.run_tests()

        # Run coverage
        results["coverage"], coverage_output = self.run_coverage()

        # Run linters (optional)
        if not skip_linters:
            results["linters"], linter_output = self.run_linters()
        else:
            results["linters"] = True
            linter_output = "Skipped"

        print("\n" + "=" * 50)

        # Generate report
        report = self.generate_report(results)
        report_file = self.reports_dir / "maintenance_report.md"
        with open(report_file, "w") as f:
            f.write(report)

        print(report)
        print(f"\n📄 Full report saved to: {report_file}")

        # Overall success
        all_passed = all(results.values())
        if all_passed:
            print("\n🎉 All maintenance checks passed!")
        else:
            print("\n⚠️  Some checks failed. See report for details.")

        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="UCOP Maintenance Script")
    parser.add_argument("--skip-linters", action="store_true",
                       help="Skip linter checks")
    parser.add_argument("--tests-only", action="store_true",
                       help="Run only tests")
    parser.add_argument("--coverage-only", action="store_true",
                       help="Run only coverage")

    args = parser.parse_args()

    maintainer = UCOPMaintainer()

    if args.tests_only:
        success, output = maintainer.run_tests()
        print(output)
        return 0 if success else 1

    if args.coverage_only:
        success, output = maintainer.run_coverage()
        print(output)
        return 0 if success else 1

    # Run all checks
    success = maintainer.run_all(skip_linters=args.skip_linters)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())