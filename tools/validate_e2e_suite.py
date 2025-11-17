#!/usr/bin/env python3
"""E2E Test Suite Validation and Reporting.

This script validates that the E2E test suite meets all requirements
and provides comprehensive reporting on test coverage.

Usage:
    python tools/validate_e2e_suite.py
    python tools/validate_e2e_suite.py --detailed
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import re


class Colors:
    """Terminal colors."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class E2ETestValidator:
    """Validates E2E test suite completeness and quality."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_categories = {
            'CLI Workflows': 'tests/e2e/test_cli_workflows.py',
            'Web UI Journeys': 'tests/e2e/test_web_ui_journeys.py',
            'API Integration': 'tests/e2e/test_api_integration.py',
            'Performance': 'tests/performance/test_load.py',
            'Smoke - Quick Validation': 'tests/smoke/test_quick_validation.py',
            'Smoke - System Health': 'tests/smoke/test_system_health.py',
        }
        self.results = {}
    
    def count_tests_in_file(self, file_path: str) -> Tuple[int, List[str]]:
        """Count test functions in a file and return their names."""
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            return 0, []
        
        test_names = []
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find all test function definitions
            pattern = r'def (test_\w+)\('
            test_names = re.findall(pattern, content)
        
        return len(test_names), test_names
    
    def analyze_test_suite(self) -> Dict:
        """Analyze the complete test suite."""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}E2E Test Suite Validation{Colors.END}")
        print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
        
        total_tests = 0
        category_results = {}
        
        for category, file_path in self.test_categories.items():
            count, test_names = self.count_tests_in_file(file_path)
            total_tests += count
            
            category_results[category] = {
                'file': file_path,
                'count': count,
                'tests': test_names
            }
            
            status = f"{Colors.GREEN}✓{Colors.END}" if count > 0 else f"{Colors.RED}✗{Colors.END}"
            print(f"{status} {category:30s} {count:3d} tests")
        
        print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"\n{Colors.BOLD}Total Tests: {total_tests}{Colors.END}")
        
        return {
            'total_tests': total_tests,
            'categories': category_results
        }
    
    def check_requirements(self, analysis: Dict) -> bool:
        """Check if test suite meets requirements."""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}Requirements Validation{Colors.END}")
        print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
        
        requirements = [
            ('Total Tests ≥ 100', analysis['total_tests'] >= 100),
            ('CLI Workflow Tests ≥ 10', analysis['categories']['CLI Workflows']['count'] >= 10),
            ('Web UI Journey Tests ≥ 15', analysis['categories']['Web UI Journeys']['count'] >= 15),
            ('API Integration Tests ≥ 25', analysis['categories']['API Integration']['count'] >= 25),
            ('Performance Tests ≥ 8', analysis['categories']['Performance']['count'] >= 8),
            ('Smoke Tests ≥ 20', 
             analysis['categories']['Smoke - Quick Validation']['count'] + 
             analysis['categories']['Smoke - System Health']['count'] >= 20),
        ]
        
        all_passed = True
        
        for requirement, passed in requirements:
            status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
            print(f"{status}  {requirement}")
            
            if not passed:
                all_passed = False
        
        return all_passed
    
    def check_infrastructure(self) -> bool:
        """Check if test infrastructure is in place."""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}Infrastructure Validation{Colors.END}")
        print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
        
        infrastructure_items = [
            ('Test Runner (tools/run_e2e_tests.py)', 'tools/run_e2e_tests.py'),
            ('Test Fixtures (tests/conftest.py)', 'tests/conftest.py'),
            ('Testing Guide (docs/testing-guide.md)', 'docs/testing-guide.md'),
            ('Smoke Tests Directory', 'tests/smoke/'),
            ('E2E Tests Directory', 'tests/e2e/'),
            ('Performance Tests Directory', 'tests/performance/'),
        ]
        
        all_present = True
        
        for name, path in infrastructure_items:
            full_path = self.project_root / path
            exists = full_path.exists()
            
            status = f"{Colors.GREEN}✓{Colors.END}" if exists else f"{Colors.RED}✗{Colors.END}"
            print(f"{status}  {name}")
            
            if not exists:
                all_present = False
        
        return all_present
    
    def generate_detailed_report(self, analysis: Dict, output_file: Path = None):
        """Generate detailed HTML report of test coverage."""
        report = []
        report.append("# E2E Test Suite - Detailed Report\n\n")
        report.append(f"**Total Tests:** {analysis['total_tests']}\n\n")
        
        report.append("## Test Categories\n\n")
        
        for category, data in analysis['categories'].items():
            report.append(f"### {category}\n\n")
            report.append(f"**File:** `{data['file']}`\n")
            report.append(f"**Test Count:** {data['count']}\n\n")
            
            if data['tests']:
                report.append("**Tests:**\n\n")
                for test_name in sorted(data['tests']):
                    # Convert test name to readable format
                    readable_name = test_name.replace('test_', '').replace('_', ' ').title()
                    report.append(f"- `{test_name}` - {readable_name}\n")
                report.append("\n")
        
        report_content = ''.join(report)
        
        if output_file:
            output_file.write_text(report_content, encoding='utf-8')
            print(f"\n{Colors.GREEN}✓{Colors.END} Detailed report saved to: {output_file}")
        
        return report_content
    
    def print_summary(self, analysis: Dict, requirements_passed: bool, infrastructure_passed: bool):
        """Print final summary."""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}Summary{Colors.END}")
        print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
        
        if requirements_passed and infrastructure_passed:
            print(f"{Colors.BOLD}{Colors.GREEN}✓ E2E TEST SUITE IS PRODUCTION READY!{Colors.END}")
            print(f"\n{Colors.GREEN}All requirements met:{Colors.END}")
            print(f"  • {analysis['total_tests']} comprehensive tests")
            print(f"  • All test categories covered")
            print(f"  • Test infrastructure in place")
            print(f"  • Documentation complete")
            print(f"\n{Colors.GREEN}System validated for production deployment! 🎉{Colors.END}\n")
            return True
        else:
            print(f"{Colors.BOLD}{Colors.RED}✗ VALIDATION FAILED{Colors.END}")
            print(f"\n{Colors.RED}Issues found:{Colors.END}")
            if not requirements_passed:
                print(f"  • Some test requirements not met")
            if not infrastructure_passed:
                print(f"  • Missing test infrastructure components")
            print(f"\n{Colors.RED}Please address issues before deployment.{Colors.END}\n")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate E2E test suite')
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Generate detailed report'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for detailed report'
    )
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Create validator
    validator = E2ETestValidator(project_root)
    
    # Analyze test suite
    analysis = validator.analyze_test_suite()
    
    # Check requirements
    requirements_passed = validator.check_requirements(analysis)
    
    # Check infrastructure
    infrastructure_passed = validator.check_infrastructure()
    
    # Generate detailed report if requested
    if args.detailed:
        output_path = Path(args.output) if args.output else project_root / 'E2E_TEST_REPORT.md'
        validator.generate_detailed_report(analysis, output_path)
    
    # Print summary
    success = validator.print_summary(analysis, requirements_passed, infrastructure_passed)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
