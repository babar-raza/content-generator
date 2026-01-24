"""
E2E Mock Verification - Real TestClient Tests

Runs E2E mock tests using pytest on tests/e2e_mock/ and reports results.
Wave 2 Prep - strengthened from import-only to real HTTP calls.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import re

# Import helpers from _env module
from _env import get_repo_root, ensure_sys_path, get_pytest_command

# Ensure repo root is in sys.path for proper imports
ensure_sys_path()


def run_e2e_mock_tests():
    """Run E2E mock tests using pytest and capture results."""
    repo_root = get_repo_root()
    tests_path = repo_root / 'tests' / 'e2e_mock'

    result = {
        'component': 'E2E Mock Tests (TestClient)',
        'status': 'BLOCKED',
        'evidence': '',
        'tests_run': [],
        'passed': 0,
        'failed': 0,
        'errors': 0,
        'output': ''
    }

    if not tests_path.exists():
        result['evidence'] = f'E2E mock tests directory not found: {tests_path}'
        result['status'] = 'BLOCKED'
        return result

    try:
        # Run pytest on e2e_mock tests
        pytest_cmd = get_pytest_command()  # Returns list
        cmd = pytest_cmd + [
            '-v',
            '--tb=short',
            '-q',
            str(tests_path)
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(repo_root)
        )

        output = proc.stdout + proc.stderr
        result['output'] = output

        # Parse pytest output
        # Look for test node IDs and outcomes
        passed_pattern = r'PASSED|passed'
        failed_pattern = r'FAILED|failed'
        error_pattern = r'ERROR|error'

        passed_count = len(re.findall(passed_pattern, output, re.IGNORECASE))
        failed_count = len(re.findall(failed_pattern, output, re.IGNORECASE))
        error_count = len(re.findall(error_pattern, output, re.IGNORECASE))

        # Try to extract summary line
        summary_pattern = r'(\d+) passed|(\d+) failed|(\d+) error'
        summary_matches = re.findall(summary_pattern, output, re.IGNORECASE)

        if summary_matches:
            for match in summary_matches:
                if match[0]:  # passed
                    result['passed'] = int(match[0])
                if match[1]:  # failed
                    result['failed'] = int(match[1])
                if match[2]:  # error
                    result['errors'] = int(match[2])
        else:
            # Fallback to pattern counts
            result['passed'] = passed_count
            result['failed'] = failed_count
            result['errors'] = error_count

        # Determine status
        if result['passed'] > 0 and result['failed'] == 0 and result['errors'] == 0:
            result['status'] = 'PASS'
            result['evidence'] = f"All {result['passed']} E2E mock tests passed"
        elif result['failed'] > 0 or result['errors'] > 0:
            result['status'] = 'FAIL'
            result['evidence'] = f"E2E mock tests: {result['passed']} passed, {result['failed']} failed, {result['errors']} errors"
        else:
            result['status'] = 'BLOCKED'
            result['evidence'] = 'Could not determine test results'

        # Extract test node IDs
        test_nodes = re.findall(r'tests/e2e_mock/[^\s]+::\S+', output)
        result['tests_run'] = test_nodes[:50]  # Limit to first 50

    except Exception as e:
        result['evidence'] = f'E2E mock test execution failed: {e}'
        result['status'] = 'FAIL'

    return result


def main():
    """Main entry point."""
    print("=== E2E Mock Verification (Wave 2 Prep) ===\n")
    print("Running real TestClient tests on web routes and MCP endpoints...\n")

    results = {
        'e2e_mock_tests': run_e2e_mock_tests()
    }

    # Calculate stats
    stats = {
        'PASS': sum(1 for r in results.values() if r['status'] == 'PASS'),
        'FAIL': sum(1 for r in results.values() if r['status'] == 'FAIL'),
        'BLOCKED': sum(1 for r in results.values() if r['status'] == 'BLOCKED')
    }

    # Save results to current wave2_prep directory
    repo_root = get_repo_root()

    # Try to find wave2_prep directory
    wave2_dirs = sorted((repo_root / 'reports' / 'wave2_prep').glob('*'), reverse=True)
    if wave2_dirs:
        report_dir = wave2_dirs[0] / '02_e2e_mock'
    else:
        # Fallback to creating in reports root
        report_dir = repo_root / 'reports' / 'e2e_mock_verification'

    report_dir.mkdir(parents=True, exist_ok=True)

    output_json = report_dir / 'e2e_mock_results.json'
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'stats': stats,
        'results': results
    }

    with open(output_json, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"[OK] Results saved to {output_json}")

    # Generate markdown
    md_lines = [
        "# E2E Mock Verification Results (Wave 2 Prep)",
        "",
        "## Summary",
        "",
        f"- PASS: {stats['PASS']}",
        f"- FAIL: {stats['FAIL']}",
        f"- BLOCKED: {stats['BLOCKED']}",
        "",
        "## Test Details",
        ""
    ]

    for component_name, result in results.items():
        md_lines.append(f"### {component_name}")
        md_lines.append(f"- **Status:** {result['status']}")
        md_lines.append(f"- **Evidence:** {result['evidence']}")
        md_lines.append(f"- **Tests Passed:** {result.get('passed', 0)}")
        md_lines.append(f"- **Tests Failed:** {result.get('failed', 0)}")
        md_lines.append(f"- **Errors:** {result.get('errors', 0)}")

        if result.get('tests_run'):
            md_lines.append("")
            md_lines.append("**Test Nodes Run:**")
            for test_node in result['tests_run'][:20]:
                md_lines.append(f"- {test_node}")

        md_lines.append("")
        md_lines.append("**Output Excerpt:**")
        md_lines.append("```")
        output_lines = result.get('output', '').split('\n')
        md_lines.extend(output_lines[-50:])  # Last 50 lines
        md_lines.append("```")
        md_lines.append("")

    output_md = report_dir / 'e2e_mock_results.md'
    with open(output_md, 'w') as f:
        f.write('\n'.join(md_lines))

    print(f"[OK] Markdown saved to {output_md}")
    print(f"\nStats: {stats}")

    # Save full pytest output
    if results.get('e2e_mock_tests', {}).get('output'):
        output_txt = report_dir / 'pytest_output.txt'
        with open(output_txt, 'w') as f:
            f.write(results['e2e_mock_tests']['output'])
        print(f"[OK] Full pytest output saved to {output_txt}")


if __name__ == '__main__':
    main()
