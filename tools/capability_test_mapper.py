"""
Capability Test Mapper

Maps capabilities from capabilities.json to existing tests in the tests/ directory.
Uses pytest --collect-only to get reliable test node IDs.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Set

# Import helpers from _env module
from _env import get_repo_root, get_pytest_command


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


def collect_pytest_tests() -> List[str]:
    """
    Collect all pytest test node IDs using pytest --collect-only.

    Parses the pytest 9.x tree-format output to extract node IDs.
    Returns list of node IDs in format: tests/path/file.py::Class::test_method
    """
    repo_root = get_repo_root()

    # Use venv pytest from _env module
    pytest_cmd = get_pytest_command()

    try:
        # Set PYTHONPATH to repo root for proper imports
        env = {**os.environ, 'PYTHONPATH': str(repo_root)}
        result = subprocess.run(
            pytest_cmd + ['--collect-only', '-q', '--tb=no', 'tests/'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )

        # Check for collection errors
        if result.returncode != 0 and 'collected' not in result.stdout:
            print(f"ERROR: pytest collection failed with return code {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return []

        # Parse the tree format output (pytest 9.x)
        # Example:
        # <Module test_foo.py>
        #   <Class TestBar>
        #     <Function test_baz>
        test_ids = []
        current_package = ''
        current_module = ''
        current_class = ''

        for line in result.stdout.split('\n'):
            stripped = line.strip()

            # Track package depth for nested packages
            if '<Package ' in line:
                pkg = stripped.split('<Package ')[-1].rstrip('>')
                # Handle nested package paths based on indentation
                indent = len(line) - len(line.lstrip())
                if indent <= 2:  # Root package (tests)
                    current_package = pkg
                else:
                    # Nested package - append to path
                    current_package = pkg
            elif '<Module ' in stripped:
                # Extract module name: <Module test_mesh_adapter.py>
                module = stripped.split('<Module ')[-1].rstrip('>')
                # Build full path based on package structure from line indentation
                indent = len(line) - len(line.lstrip())
                if indent <= 4:  # tests/module.py
                    current_module = f'tests/{module}'
                else:  # tests/subdir/module.py - need to track directory
                    # For nested modules, parse from tree structure
                    current_module = f'tests/{module}'
                current_class = ''
            elif '<Dir ' in stripped:
                # Track directory for proper path construction
                # Example: <Dir e2e_mock>
                pass  # We'll handle this by tracking the full path in Module
            elif '<Class ' in stripped:
                cls = stripped.split('<Class ')[-1].rstrip('>')
                current_class = cls
            elif '<Function ' in stripped:
                func = stripped.split('<Function ')[-1].rstrip('>')
                if current_module:
                    if current_class:
                        node_id = f'{current_module}::{current_class}::{func}'
                    else:
                        node_id = f'{current_module}::{func}'
                    test_ids.append(node_id)

        # Enhanced path reconstruction using directory stack
        # Re-parse with directory tracking
        test_ids_enhanced = []
        dir_stack = []
        current_module_base = ''
        current_class = ''
        skip_first_dir = True  # Skip the root directory name (e.g., content-generator)

        for line in result.stdout.split('\n'):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())

            if '<Package ' in stripped or '<Dir ' in stripped:
                if '<Package ' in stripped:
                    name = stripped.split('<Package ')[-1].rstrip('>')
                else:
                    name = stripped.split('<Dir ')[-1].rstrip('>')

                # Skip the first directory level (root directory)
                if skip_first_dir and indent <= 2:
                    skip_first_dir = False
                    continue

                # Adjust stack based on indent
                # Indent 2 = depth 1 (tests), Indent 4 = depth 2 (e2e, e2e_mock, debug), etc.
                # Since we skipped root dir, depth = (indent // 2) - 1
                expected_depth = (indent // 2) - 1
                # Pop until stack has expected_depth elements (to handle siblings at same level)
                while len(dir_stack) > expected_depth:
                    dir_stack.pop()
                dir_stack.append(name)
            elif '<Module ' in stripped:
                module = stripped.split('<Module ')[-1].rstrip('>')
                # Build path from dir_stack
                if dir_stack:
                    current_module_base = '/'.join(dir_stack) + '/' + module
                else:
                    current_module_base = module
                current_class = ''
            elif '<Class ' in stripped:
                current_class = stripped.split('<Class ')[-1].rstrip('>')
            elif '<Function ' in stripped:
                func = stripped.split('<Function ')[-1].rstrip('>')
                if current_module_base:
                    if current_class:
                        node_id = f'{current_module_base}::{current_class}::{func}'
                    else:
                        node_id = f'{current_module_base}::{func}'
                    test_ids_enhanced.append(node_id)

        return test_ids_enhanced if test_ids_enhanced else test_ids

    except subprocess.TimeoutExpired as e:
        print(f"ERROR: pytest collection timed out after 60s: {e}")
        return []
    except subprocess.CalledProcessError as e:
        print(f"ERROR: pytest collection failed: {e}")
        print(f"STDOUT: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
        print(f"STDERR: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        return []
    except FileNotFoundError as e:
        print(f"ERROR: pytest command not found: {e}")
        print(f"Attempted command: {pytest_cmd}")
        return []
    except Exception as e:
        print(f"ERROR: Unexpected error during pytest collection: {type(e).__name__}: {e}")
        return []


def scan_test_files() -> tuple[Dict[str, List[str]], List[str]]:
    """Scan test files and categorize tests by keywords. Returns (keyword_map, test_file_paths)."""
    repo_root = get_repo_root()
    tests_dir = repo_root / 'tests'

    test_files_by_keyword = {}
    all_test_files = []

    if not tests_dir.exists():
        return test_files_by_keyword, all_test_files

    for test_file in tests_dir.rglob('test_*.py'):
        rel_path = str(test_file.relative_to(repo_root)).replace('\\', '/')
        all_test_files.append(rel_path)

        # Extract keywords from path and filename
        path_parts = test_file.stem.replace('test_', '').split('_')
        keywords = set(path_parts)

        # Add parent directory names as keywords
        for parent in test_file.parents:
            if parent == tests_dir or parent == repo_root:
                break
            keywords.add(parent.name)

        # Store by each keyword
        for keyword in keywords:
            if keyword not in test_files_by_keyword:
                test_files_by_keyword[keyword] = []
            test_files_by_keyword[keyword].append(rel_path)

    return test_files_by_keyword, all_test_files


def normalize_name(name: str) -> str:
    """Normalize name for matching (remove underscores, hyphens, lowercase)."""
    return re.sub(r'[_\-]', '', name.lower())


def load_capability_overrides() -> Dict[str, str]:
    """Load explicit capability-to-test mapping overrides from capability_overrides.json."""
    repo_root = get_repo_root()
    overrides_file = repo_root / 'tools' / 'capability_overrides.json'

    if not overrides_file.exists():
        print("Warning: capability_overrides.json not found, using fuzzy matching only")
        return {}

    try:
        with open(overrides_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        overrides = data.get('overrides', {})
        print(f"Loaded {len(overrides)} capability override mappings")
        return overrides
    except Exception as e:
        print(f"Warning: Could not load capability_overrides.json: {e}")
        return {}


def validate_overrides(overrides: Dict[str, str], test_node_ids: List[str]) -> tuple[bool, List[str]]:
    """
    Validate that all override node IDs exist in the collected test node IDs.

    Returns:
        (all_valid, invalid_overrides) where all_valid is True if all overrides are valid,
        and invalid_overrides is a list of (cap_id, node_id) tuples for invalid overrides.
    """
    invalid = []
    test_node_ids_set = set(test_node_ids)

    for cap_id, node_id in overrides.items():
        if node_id not in test_node_ids_set:
            invalid.append((cap_id, node_id))

    return len(invalid) == 0, invalid


def map_capability_to_tests(
    cap: Dict[str, Any],
    test_node_ids: List[str],
    test_files_by_keyword: Dict[str, List[str]],
    overrides: Dict[str, str]
) -> Dict[str, Any]:
    """Map a single capability to relevant tests."""
    matched_tests = []
    confidence = 0.0
    notes = []

    cap_id = cap['cap_id']

    # Check for explicit override first
    if cap_id in overrides:
        override_node_id = overrides[cap_id]
        matched_tests.append(override_node_id)
        confidence = 1.0
        notes.append(f"Explicit override mapping to {override_node_id}")
        return {
            'tests': matched_tests,
            'confidence': confidence,
            'notes': '; '.join(notes)
        }

    cap_type = cap_id.split('-')[1]  # AGENT, PIPE, WF, etc.

    # Strategy 1: Direct match by agent_id, step_name, workflow_id, etc.
    search_terms = []

    if 'agent_id' in cap:
        search_terms.append(normalize_name(cap['agent_id']))
    if 'step_name' in cap:
        search_terms.append(normalize_name(cap['step_name']))
    if 'workflow_id' in cap:
        search_terms.append(normalize_name(cap['workflow_id']))
    if 'route_group' in cap:
        search_terms.append(normalize_name(cap['route_group']))

    # Search in test node IDs
    for test_id in test_node_ids:
        normalized_test_id = normalize_name(test_id)

        for term in search_terms:
            if term in normalized_test_id:
                matched_tests.append(test_id)
                confidence = max(confidence, 0.8)
                notes.append(f"Matched by term '{term}'")
                break

    # Strategy 2: Match by category/type
    if cap_type == 'AGENT':
        # Look for unit tests for this agent
        for test_id in test_node_ids:
            if 'unit' in normalize_name(test_id):
                for term in search_terms:
                    if term in normalize_name(test_id):
                        if test_id not in matched_tests:
                            matched_tests.append(test_id)
                            confidence = max(confidence, 0.7)
                            notes.append(f"Matched unit test by agent name")

    elif cap_type == 'PIPE' or cap_type == 'WF':
        # Look for integration/pipeline tests
        for test_id in test_node_ids:
            if 'integration' in normalize_name(test_id) or 'pipeline' in normalize_name(test_id) or 'workflow' in normalize_name(test_id):
                for term in search_terms:
                    if term in normalize_name(test_id):
                        if test_id not in matched_tests:
                            matched_tests.append(test_id)
                            confidence = max(confidence, 0.6)
                            notes.append(f"Matched pipeline/workflow test")

    elif cap_type == 'WEB':
        # Look for web/API tests
        for test_id in test_node_ids:
            if 'web' in normalize_name(test_id) or 'api' in normalize_name(test_id) or 'routes' in normalize_name(test_id):
                for term in search_terms:
                    if term in normalize_name(test_id):
                        if test_id not in matched_tests:
                            matched_tests.append(test_id)
                            confidence = max(confidence, 0.7)
                            notes.append(f"Matched web/API test")

    elif cap_type == 'MCP':
        # Look for MCP tests
        for test_id in test_node_ids:
            if 'mcp' in normalize_name(test_id):
                if test_id not in matched_tests:
                    matched_tests.append(test_id)
                    confidence = max(confidence, 0.5)
                    notes.append(f"Matched MCP test")

    # Remove duplicates while preserving order
    matched_tests = list(dict.fromkeys(matched_tests))

    return {
        'tests': matched_tests,
        'confidence': round(confidence, 2),
        'notes': '; '.join(notes) if notes else 'No tests matched'
    }


def build_test_mapping() -> Dict[str, Any]:
    """Build complete test mapping."""
    report_dir = get_latest_report_dir()
    capabilities_file = report_dir / '01_capabilities' / 'capabilities.json'

    if not capabilities_file.exists():
        raise FileNotFoundError(f"Capabilities file not found: {capabilities_file}")

    with open(capabilities_file, 'r', encoding='utf-8') as f:
        capabilities_data = json.load(f)

    print("Collecting pytest tests...")
    test_node_ids = collect_pytest_tests()
    print(f"Found {len(test_node_ids)} test node IDs")

    # STOP-THE-LINE: If no tests collected, fail immediately
    if not test_node_ids:
        raise RuntimeError("CRITICAL: Collected 0 test node IDs. Cannot proceed. Check pytest collection.")

    print("Scanning test files...")
    test_files_by_keyword, all_test_files = scan_test_files()
    print(f"Indexed {len(test_files_by_keyword)} keywords, {len(all_test_files)} test files")

    print("Loading capability overrides...")
    overrides = load_capability_overrides()

    print("Validating override node IDs...")
    all_valid, invalid_overrides = validate_overrides(overrides, test_node_ids)
    if not all_valid:
        print(f"\nERROR: {len(invalid_overrides)} override node IDs are invalid:")
        for cap_id, node_id in invalid_overrides:
            print(f"  {cap_id} -> {node_id} (NOT FOUND)")
        raise RuntimeError(f"Invalid override node IDs detected. Fix capability_overrides.json before proceeding.")

    print("All override node IDs validated successfully!")

    print("Mapping capabilities to tests...")
    mapping = {}
    stats = {
        'total_capabilities': len(capabilities_data['capabilities']),
        'mapped_with_high_confidence': 0,
        'mapped_with_low_confidence': 0,
        'unmapped': 0,
        'explicit_overrides': 0
    }

    for cap in capabilities_data['capabilities']:
        cap_id = cap['cap_id']
        test_mapping = map_capability_to_tests(cap, test_node_ids, test_files_by_keyword, overrides)
        mapping[cap_id] = test_mapping

        # Update stats
        if test_mapping['tests']:
            if test_mapping['confidence'] >= 1.0:
                stats['explicit_overrides'] += 1
                stats['mapped_with_high_confidence'] += 1
            elif test_mapping['confidence'] >= 0.7:
                stats['mapped_with_high_confidence'] += 1
            else:
                stats['mapped_with_low_confidence'] += 1
        else:
            stats['unmapped'] += 1

    return {
        'generated_at': str(Path.cwd()),
        'total_test_nodes': len(test_node_ids),
        'stats': stats,
        'mapping': mapping
    }


def main():
    """Main entry point."""
    print("Building capability-to-test mapping...")

    mapping_data = build_test_mapping()

    # Write output
    report_dir = get_latest_report_dir()
    output_file = report_dir / '01_capabilities' / 'test_mapping.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, indent=2)

    print(f"[OK] Wrote {output_file}")
    print(f"\nStats:")
    print(f"  Total capabilities: {mapping_data['stats']['total_capabilities']}")
    print(f"  Explicit overrides: {mapping_data['stats'].get('explicit_overrides', 0)}")
    print(f"  Mapped (high confidence): {mapping_data['stats']['mapped_with_high_confidence']}")
    print(f"  Mapped (low confidence): {mapping_data['stats']['mapped_with_low_confidence']}")
    print(f"  Unmapped: {mapping_data['stats']['unmapped']}")


if __name__ == '__main__':
    main()
