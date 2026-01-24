"""
Pipeline Verification

Verifies that pipeline and workflow configurations are valid and can be loaded.
"""

import json
import yaml
from pathlib import Path
from datetime import datetime

# Import helpers from _env module
from _env import get_repo_root


def get_latest_report_dir() -> Path:
    """Get the latest timestamp directory from reports."""
    repo_root = get_repo_root()
    reports_dir = repo_root / 'reports' / 'capability_verify'
    ts_dirs = sorted([d for d in reports_dir.iterdir() if d.is_dir()], reverse=True)
    return ts_dirs[0]


def verify_main_config_pipeline():
    """Verify config/main.yaml pipeline."""
    repo_root = get_repo_root()
    config_file = repo_root / 'config' / 'main.yaml'

    result = {
        'pipeline': 'config/main.yaml',
        'status': 'FAIL',
        'evidence': '',
        'workflows_tested': [],
        'errors': []
    }

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Check main pipeline
        if 'pipeline' in config:
            result['evidence'] = f"Found {len(config['pipeline'])} pipeline steps"
            result['status'] = 'PASS'

        # Check workflows
        if 'workflows' in config:
            for wf_key, wf_value in config['workflows'].items():
                if isinstance(wf_value, dict) and 'steps' in wf_value:
                    result['workflows_tested'].append(wf_key)

    except Exception as e:
        result['status'] = 'FAIL'
        result['errors'].append(str(e))

    return result


def verify_template_workflows():
    """Verify templates/workflows.yaml."""
    repo_root = get_repo_root()
    workflows_file = repo_root / 'templates' / 'workflows.yaml'

    result = {
        'pipeline': 'templates/workflows.yaml',
        'status': 'FAIL',
        'evidence': '',
        'workflows_tested': [],
        'errors': []
    }

    try:
        with open(workflows_file, 'r') as f:
            workflows = yaml.safe_load(f)

        if 'workflows' in workflows:
            workflow_ids = list(workflows['workflows'].keys())
            result['workflows_tested'] = workflow_ids
            result['evidence'] = f"Found {len(workflow_ids)} workflows: {', '.join(workflow_ids)}"
            result['status'] = 'PASS'

    except Exception as e:
        result['status'] = 'FAIL'
        result['errors'].append(str(e))

    return result


def main():
    """Main entry point."""
    print("=== Pipeline Verification ===\n")

    results = {
        'main_config': verify_main_config_pipeline(),
        'template_workflows': verify_template_workflows()
    }

    # Calculate stats
    stats = {
        'PASS': sum(1 for r in results.values() if r['status'] == 'PASS'),
        'FAIL': sum(1 for r in results.values() if r['status'] == 'FAIL')
    }

    # Save results
    report_dir = get_latest_report_dir()
    output_json = report_dir / '03_pipeline_verification' / 'pipeline_results.json'
    output_json.parent.mkdir(parents=True, exist_ok=True)

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
        "# Pipeline Verification Results",
        "",
        "## Summary",
        "",
        f"- PASS: {stats['PASS']}",
        f"- FAIL: {stats['FAIL']}",
        "",
        "## Details",
        ""
    ]

    for pipeline_name, result in results.items():
        md_lines.append(f"### {pipeline_name}")
        md_lines.append(f"- **Status:** {result['status']}")
        md_lines.append(f"- **Evidence:** {result['evidence']}")
        if result['workflows_tested']:
            md_lines.append(f"- **Workflows Tested:** {', '.join(result['workflows_tested'])}")
        if result['errors']:
            md_lines.append(f"- **Errors:** {'; '.join(result['errors'])}")
        md_lines.append("")

    output_md = report_dir / '03_pipeline_verification' / 'pipeline_results.md'
    with open(output_md, 'w') as f:
        f.write('\n'.join(md_lines))

    print(f"[OK] Markdown saved to {output_md}")
    print(f"\nStats: {stats}")


if __name__ == '__main__':
    main()
