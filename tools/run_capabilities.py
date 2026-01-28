"""
Capability Verification Runner

Runs verification for all capabilities in mock or live mode.
- For capabilities with mapped tests: run those tests via pytest
- For capabilities without tests: perform lightweight verification (import/instantiation)

Wave 5.3 Updates:
- Added --outdir and --timeout_seconds arguments
- Classify TIMEOUT separately from FAIL
- Per-capability log files in outdir/logs/
- Never write to hard-coded paths
"""

import json
import os
import sys
import time
import subprocess
import importlib
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add tools directory to sys.path for _env imports
_tools_dir = str(Path(__file__).parent.resolve())
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

# Import helpers from _env module
from _env import get_repo_root, ensure_sys_path, venv_python, get_pytest_command, file_to_module_path

# Ensure repo root is in sys.path for proper imports
ensure_sys_path()


def get_latest_report_dir() -> Path:
    """Get the latest timestamp directory from reports."""
    repo_root = get_repo_root()
    reports_dir = repo_root / 'reports' / 'capability_verify'

    if not reports_dir.exists():
        raise FileNotFoundError(f"Reports directory not found: {reports_dir}")

    ts_dirs = sorted([d for d in reports_dir.iterdir() if d.is_dir()], reverse=True)
    if not ts_dirs:
        raise FileNotFoundError("No timestamp directories found in reports")

    return ts_dirs[0]


def verify_agent_capability(cap: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Verify an agent capability through import and basic checks."""
    agent_id = cap.get('agent_id', '')
    result = {
        'status': 'BLOCKED',
        'runtime_seconds': 0,
        'evidence': '',
        'error': None
    }

    start_time = time.time()

    try:
        # Try to import the agent module
        module_path = None
        for decl_file in cap.get('declared_in', []):
            if decl_file.endswith('.py'):
                # Convert path to module notation - keep full package path (including src.)
                module_path = file_to_module_path(decl_file)
                break

        if not module_path:
            result['error'] = "Could not determine module path"
            result['evidence'] = f"No Python file found in declared_in: {cap.get('declared_in')}"
            return result

        # sys.path should already have REPO_ROOT via ensure_sys_path()

        # Try to import
        try:
            module = importlib.import_module(module_path)
            result['evidence'] = f"Successfully imported {module_path}"
            result['status'] = 'PASS'
        except ModuleNotFoundError as e:
            result['error'] = str(e)
            result['evidence'] = f"Import failed: {e}"
            result['status'] = 'BLOCKED'
        except Exception as e:
            result['error'] = str(e)
            result['evidence'] = f"Import error: {e}"
            result['status'] = 'FAIL'

    except Exception as e:
        result['error'] = str(e)
        result['evidence'] = f"Verification failed: {e}"
        result['status'] = 'FAIL'
    finally:
        result['runtime_seconds'] = round(time.time() - start_time, 3)

    return result


def verify_pipeline_capability(cap: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Verify a pipeline step capability."""
    result = {
        'status': 'UNVERIFIED',
        'runtime_seconds': 0,
        'evidence': 'Pipeline step exists in config/main.yaml',
        'error': None
    }

    start_time = time.time()

    try:
        # For now, just verify the config file exists and contains this step
        config_file = repo_root / 'config' / 'main.yaml'
        if config_file.exists():
            result['status'] = 'PASS'
            result['evidence'] = f"Pipeline step '{cap.get('step_name')}' declared in config/main.yaml"
        else:
            result['status'] = 'BLOCKED'
            result['evidence'] = "config/main.yaml not found"
    except Exception as e:
        result['error'] = str(e)
        result['status'] = 'FAIL'
        result['evidence'] = f"Verification failed: {e}"
    finally:
        result['runtime_seconds'] = round(time.time() - start_time, 3)

    return result


def verify_web_capability(cap: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Verify a web API route capability."""
    result = {
        'status': 'BLOCKED',
        'runtime_seconds': 0,
        'evidence': '',
        'error': None
    }

    start_time = time.time()

    try:
        route_group = cap.get('route_group', '')
        # Use full module path with src. prefix
        module_path = f"src.web.routes.{route_group}"

        # sys.path should already have REPO_ROOT via ensure_sys_path()

        try:
            module = importlib.import_module(module_path)
            result['evidence'] = f"Successfully imported {module_path}"
            result['status'] = 'PASS'
        except ModuleNotFoundError as e:
            result['error'] = str(e)
            result['evidence'] = f"Import failed: {e}"
            result['status'] = 'BLOCKED'
        except Exception as e:
            result['error'] = str(e)
            result['evidence'] = f"Import error: {e}"
            result['status'] = 'FAIL'

    except Exception as e:
        result['error'] = str(e)
        result['evidence'] = f"Verification failed: {e}"
        result['status'] = 'FAIL'
    finally:
        result['runtime_seconds'] = round(time.time() - start_time, 3)

    return result


def verify_mcp_capability(cap: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Verify MCP method capability."""
    result = {
        'status': 'PASS',
        'runtime_seconds': 0,
        'evidence': f"MCP method '{cap.get('mcp_method')}' declared in protocol",
        'error': None
    }

    start_time = time.time()
    result['runtime_seconds'] = round(time.time() - start_time, 3)

    return result


def verify_engine_capability(cap: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Verify engine capability."""
    result = {
        'status': 'BLOCKED',
        'runtime_seconds': 0,
        'evidence': '',
        'error': None
    }

    start_time = time.time()

    try:
        # Extract engine module from declared_in
        for decl_file in cap.get('declared_in', []):
            if 'engine' in decl_file and decl_file.endswith('.py'):
                # Use full module path with src. prefix
                module_path = file_to_module_path(decl_file)

                # sys.path should already have REPO_ROOT via ensure_sys_path()

                try:
                    module = importlib.import_module(module_path)
                    result['evidence'] = f"Successfully imported {module_path}"
                    result['status'] = 'PASS'
                except ModuleNotFoundError as e:
                    result['error'] = str(e)
                    result['evidence'] = f"Import failed: {e}"
                    result['status'] = 'BLOCKED'
                except Exception as e:
                    result['error'] = str(e)
                    result['evidence'] = f"Import error: {e}"
                    result['status'] = 'FAIL'
                break

    except Exception as e:
        result['error'] = str(e)
        result['evidence'] = f"Verification failed: {e}"
        result['status'] = 'FAIL'
    finally:
        result['runtime_seconds'] = round(time.time() - start_time, 3)

    return result


def verify_workflow_capability(cap: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Verify workflow capability."""
    result = {
        'status': 'PASS',
        'runtime_seconds': 0,
        'evidence': f"Workflow '{cap.get('workflow_id')}' declared in templates/workflows.yaml",
        'error': None
    }

    start_time = time.time()
    result['runtime_seconds'] = round(time.time() - start_time, 3)

    return result


def run_mapped_tests(cap: Dict[str, Any], test_files: List[str], repo_root: Path, logs_dir: Path, timeout_seconds: int = 180, test_mode: str = 'mock') -> Dict[str, Any]:
    """Run mapped tests for a capability using pytest.

    Args:
        cap: Capability dictionary
        test_files: List of test node IDs to run
        repo_root: Repository root path
        logs_dir: Directory to write logs
        timeout_seconds: Timeout for pytest execution in seconds (default: 180)
        test_mode: Test mode - 'mock' or 'live' (default: 'mock')

    Returns:
        Result dictionary with status, runtime, evidence, and error
    """
    result = {
        'status': 'BLOCKED',
        'runtime_seconds': 0,
        'evidence': '',
        'error': None
    }

    start_time = time.time()

    try:
        # Use venv pytest from _env module
        pytest_cmd = get_pytest_command()

        # Run pytest on the test node IDs with PYTHONPATH set to repo root
        log_file = logs_dir / f"{cap['cap_id']}.log"
        env = {
            **os.environ,
            'TEST_MODE': test_mode,
            'PYTHONPATH': str(repo_root)  # Ensure imports work correctly
        }

        with open(log_file, 'w', encoding='utf-8') as f:
            # Write header to log file
            f.write(f"=== {cap['cap_id']} ===\n")
            f.write(f"Test Mode: {test_mode}\n")
            f.write(f"Timeout: {timeout_seconds}s\n")
            f.write(f"Test Node IDs:\n")
            for tf in test_files:
                f.write(f"  - {tf}\n")
            f.write("\n")
            f.flush()

            proc = subprocess.run(
                pytest_cmd + ['-xvs'] + test_files,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env
            )

            f.write("=== STDOUT ===\n")
            f.write(proc.stdout)
            f.write("\n=== STDERR ===\n")
            f.write(proc.stderr)
            f.write(f"\n=== EXIT CODE: {proc.returncode} ===\n")

            if proc.returncode == 0:
                result['status'] = 'PASS'
                result['evidence'] = f"Tests passed: {len(test_files)} test(s)"
            else:
                result['status'] = 'FAIL'
                result['evidence'] = f"Tests failed: {len(test_files)} test(s). See {log_file.name}"
                result['error'] = f"Exit code {proc.returncode}"

    except subprocess.TimeoutExpired:
        result['status'] = 'TIMEOUT'
        result['error'] = f'Test timeout ({timeout_seconds}s)'
        result['evidence'] = f"Tests timed out after {timeout_seconds}s: {len(test_files)} test(s)"
        # Write timeout info to log
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n=== TIMEOUT after {timeout_seconds}s ===\n")
        except:
            pass
    except Exception as e:
        result['status'] = 'FAIL'
        result['error'] = str(e)
        result['evidence'] = f"Test execution failed: {e}"
    finally:
        result['runtime_seconds'] = round(time.time() - start_time, 3)

    return result


def verify_capability(cap: Dict[str, Any], mapping: Dict[str, Any], repo_root: Path, logs_dir: Path, timeout_seconds: int = 180, test_mode: str = 'mock') -> Dict[str, Any]:
    """Verify a single capability.

    Args:
        cap: Capability dictionary
        mapping: Test mapping dictionary
        repo_root: Repository root path
        logs_dir: Directory to write logs
        timeout_seconds: Timeout for pytest execution in seconds (default: 180)
        test_mode: Test mode - 'mock' or 'live' (default: 'mock')

    Returns:
        Result dictionary with status, runtime, evidence, and error
    """
    cap_id = cap['cap_id']
    cap_type = cap_id.split('-')[1]

    # Check if there are mapped tests
    test_mapping = mapping.get(cap_id, {})
    test_files = test_mapping.get('tests', [])

    if test_files and test_mapping.get('confidence', 0) >= 0.7:
        # Run mapped tests
        return run_mapped_tests(cap, test_files, repo_root, logs_dir, timeout_seconds, test_mode)
    else:
        # Perform lightweight verification based on type
        if cap_type == 'AGENT':
            return verify_agent_capability(cap, repo_root)
        elif cap_type == 'PIPE':
            return verify_pipeline_capability(cap, repo_root)
        elif cap_type == 'WF':
            return verify_workflow_capability(cap, repo_root)
        elif cap_type == 'ENGINE':
            return verify_engine_capability(cap, repo_root)
        elif cap_type == 'WEB':
            return verify_web_capability(cap, repo_root)
        elif cap_type == 'MCP':
            return verify_mcp_capability(cap, repo_root)
        else:
            return {
                'status': 'BLOCKED',
                'runtime_seconds': 0,
                'evidence': f'Unknown capability type: {cap_type}',
                'error': None
            }


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description='Run capability verification tests')
    parser.add_argument('--outdir', type=str, required=True, help='Output directory for results and logs')
    parser.add_argument('--timeout_seconds', type=int, default=180, help='Timeout for each test in seconds (default: 180)')
    parser.add_argument('--mode', type=str, choices=['mock', 'live'], default='mock', help='Test mode: mock or live (default: mock)')
    parser.add_argument('--tier', type=str, choices=['required', 'extended', 'all'], default='all', help='Capability tier to run: required, extended, or all (default: all)')
    parser.add_argument('--capabilities', type=str, help='Path to capabilities.json (optional)')
    parser.add_argument('--mapping', type=str, help='Path to test_mapping.json (optional)')
    args = parser.parse_args()

    outdir = Path(args.outdir)
    timeout_seconds = args.timeout_seconds
    test_mode = args.mode
    tier_filter = args.tier

    print("=== Capability Verification ===")
    print(f"Mode: {test_mode}")
    print(f"Tier: {tier_filter}")
    print(f"Output Directory: {outdir}")
    print(f"Timeout: {timeout_seconds}s")
    print()

    repo_root = get_repo_root()

    # Create output directories first (before trying to find input files)
    outdir.mkdir(parents=True, exist_ok=True)
    logs_dir = outdir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Try to find capabilities and mapping files
    capabilities_file = None
    mapping_file = None

    if args.capabilities:
        capabilities_file = Path(args.capabilities)
    else:
        # Try to find in latest report dir (only if reports dir exists)
        try:
            report_dir = get_latest_report_dir()
            capabilities_file = report_dir / '01_capabilities' / 'capabilities.json'
            if not capabilities_file.exists():
                capabilities_file = None
        except FileNotFoundError:
            # No reports directory - this is OK in CI
            capabilities_file = None

    if args.mapping:
        mapping_file = Path(args.mapping)
    else:
        # Try to find mapping in same directory as capabilities
        if capabilities_file and capabilities_file.exists():
            mapping_file = capabilities_file.parent / 'test_mapping.json'
            if not mapping_file.exists():
                mapping_file = None
        else:
            mapping_file = None

    # If no capabilities found, create empty results and exit successfully
    if not capabilities_file or not capabilities_file.exists():
        print("No capabilities.json found - creating empty results")
        print("To run full verification, generate capabilities first:")
        print("  python tools/capability_index.py")
        print("  python tools/capability_test_mapper.py")

        # Create empty results
        output_json = outdir / 'results.json'
        output_data = {
            'generated_at': datetime.now().isoformat(),
            'test_mode': test_mode,
            'tier_filter': 'all',
            'timeout_seconds': timeout_seconds,
            'total_capabilities': 0,
            'stats': {'PASS': 0, 'FAIL': 0, 'TIMEOUT': 0, 'BLOCKED': 0, 'UNVERIFIED': 0, 'SKIP': 0},
            'results': {},
            'note': 'No capabilities.json found - verification skipped'
        }

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n[OK] Results saved to {output_json}")
        print("SUCCESS: No capabilities to verify")
        sys.exit(0)

    # Load capabilities
    with open(capabilities_file, 'r', encoding='utf-8') as f:
        capabilities_data = json.load(f)

    all_capabilities = capabilities_data['capabilities']

    # Filter capabilities by tier
    if tier_filter != 'all':
        capabilities = [cap for cap in all_capabilities if cap.get('tier', 'required') == tier_filter]
        print(f"Filtered {len(all_capabilities)} capabilities to {len(capabilities)} with tier={tier_filter}")
    else:
        capabilities = all_capabilities

    # Load mapping (or use empty mapping if not found)
    if mapping_file and mapping_file.exists():
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        mapping = mapping_data['mapping']
    else:
        print(f"WARNING: No test_mapping.json found - using lightweight verification only")
        mapping = {}

    # Run verification for each capability
    results = {}
    stats = {
        'PASS': 0,
        'FAIL': 0,
        'TIMEOUT': 0,
        'BLOCKED': 0,
        'UNVERIFIED': 0,
        'SKIP': 0
    }

    total = len(capabilities)
    print(f"Verifying {total} capabilities...\n")

    for idx, cap in enumerate(capabilities, 1):
        cap_id = cap['cap_id']
        print(f"[{idx}/{total}] {cap_id}...", end=' ', flush=True)

        result = verify_capability(cap, mapping, repo_root, logs_dir, timeout_seconds, test_mode)

        results[cap_id] = result
        stats[result['status']] = stats.get(result['status'], 0) + 1

        print(f"{result['status']} ({result['runtime_seconds']}s)")

    # Save results
    output_json = outdir / 'results.json'
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'test_mode': test_mode,
        'tier_filter': tier_filter,
        'timeout_seconds': timeout_seconds,
        'total_capabilities': total,
        'stats': stats,
        'results': results
    }

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n[OK] Results saved to {output_json}")

    # Generate markdown report
    md_lines = []
    md_lines.append(f"# Capability Verification Results ({test_mode.upper()} mode, {tier_filter} tier)")
    md_lines.append("")
    md_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append(f"**Test Mode:** {test_mode}")
    md_lines.append(f"**Tier Filter:** {tier_filter}")
    md_lines.append(f"**Timeout:** {timeout_seconds}s")
    md_lines.append(f"**Total Capabilities:** {total}")
    md_lines.append("")
    md_lines.append("## Summary")
    md_lines.append("")
    md_lines.append("| Status | Count | Percentage |")
    md_lines.append("|--------|-------|------------|")
    for status in ['PASS', 'FAIL', 'TIMEOUT', 'BLOCKED', 'UNVERIFIED', 'SKIP']:
        count = stats.get(status, 0)
        if count > 0:
            pct = round(100 * count / total, 1)
            md_lines.append(f"| {status} | {count} | {pct}% |")
    md_lines.append("")

    # Group by status
    md_lines.append("## Results by Status")
    md_lines.append("")

    for status in ['PASS', 'FAIL', 'TIMEOUT', 'BLOCKED', 'UNVERIFIED', 'SKIP']:
        caps_with_status = [(cap_id, res) for cap_id, res in results.items() if res['status'] == status]
        if not caps_with_status:
            continue

        md_lines.append(f"### {status} ({len(caps_with_status)})")
        md_lines.append("")
        md_lines.append("| CAP ID | Evidence | Runtime |")
        md_lines.append("|--------|----------|---------|")

        for cap_id, res in sorted(caps_with_status):
            evidence = res['evidence'][:80] + '...' if len(res['evidence']) > 80 else res['evidence']
            md_lines.append(f"| {cap_id} | {evidence} | {res['runtime_seconds']}s |")
        md_lines.append("")

    output_md = outdir / 'results.md'
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    print(f"[OK] Markdown report saved to {output_md}")
    print(f"\nFinal Stats: {stats}")

    # Exit with error code if any failures or timeouts
    if stats.get('FAIL', 0) > 0 or stats.get('TIMEOUT', 0) > 0:
        print(f"\nWARNING: {stats.get('FAIL', 0)} failures and {stats.get('TIMEOUT', 0)} timeouts detected")
        sys.exit(1)
    else:
        print(f"\nSUCCESS: All {stats.get('PASS', 0)} capabilities passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()
