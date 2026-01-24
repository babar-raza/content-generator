"""
Failure Catalog Builder

Analyzes all verification results and categorizes failures with remediation plans.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def get_repo_root() -> Path:
    """Get repository root directory."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    return Path.cwd()


def get_latest_report_dir() -> Path:
    """Get the latest timestamp directory from reports."""
    repo_root = get_repo_root()
    reports_dir = repo_root / 'reports' / 'capability_verify'
    ts_dirs = sorted([d for d in reports_dir.iterdir() if d.is_dir()], reverse=True)
    return ts_dirs[0]


def categorize_failure(cap_id: str, result: dict, cap_data: dict) -> dict:
    """Categorize a failure and suggest remediation."""
    evidence = result.get('evidence', '').lower()
    error = str(result.get('error', '')).lower()

    category = 'UNKNOWN'
    remediation = ''

    # Analyze evidence and error to categorize
    if 'no module named' in evidence or 'import failed' in evidence or 'modulenotfounderror' in error:
        category = 'MISSING-DEP'
        remediation = 'Install missing dependencies from requirements.txt or check import paths'

    elif 'test' in evidence and ('failed' in evidence or 'error' in error):
        category = 'LOGIC-BUG'
        remediation = 'Fix test failures - review test logs for specific issues'

    elif 'blocked' in result.get('status', '').lower():
        if 'import' in evidence:
            category = 'MISSING-DEP'
            remediation = 'Ensure all dependencies are installed and module paths are correct'
        else:
            category = 'ENV-INFRA'
            remediation = 'May require external services (DB, Redis, ChromaDB) - consider mocking or docker-compose'

    elif 'timeout' in error:
        category = 'FLAKY'
        remediation = 'Test timeout - may need longer timeout or optimization'

    else:
        category = 'LOGIC-BUG'
        remediation = 'Review error details and fix implementation issues'

    return {
        'cap_id': cap_id,
        'cap_title': cap_data.get('title', ''),
        'status': result.get('status'),
        'category': category,
        'evidence': result.get('evidence', '')[:200],
        'error': str(result.get('error', ''))[:200] if result.get('error') else None,
        'remediation': remediation
    }


def main():
    """Main entry point."""
    print("=== Building Failure Catalog ===\n")

    report_dir = get_latest_report_dir()

    # Load all results
    with open(report_dir / '01_capabilities' / 'capabilities.json') as f:
        capabilities_data = json.load(f)

    with open(report_dir / '02_individual_verification' / 'individual_results.json') as f:
        individual_results = json.load(f)

    # Create cap_id to cap_data mapping
    cap_map = {cap['cap_id']: cap for cap in capabilities_data['capabilities']}

    # Collect all failures and blocked items
    failures = []

    for cap_id, result in individual_results['results'].items():
        if result['status'] in ['FAIL', 'BLOCKED']:
            cap_data = cap_map.get(cap_id, {})
            failure = categorize_failure(cap_id, result, cap_data)
            failures.append(failure)

    # Group by category
    by_category = defaultdict(list)
    for failure in failures:
        by_category[failure['category']].append(failure)

    # Generate stats
    stats = {
        'total_failures': len(failures),
        'by_category': {cat: len(items) for cat, items in by_category.items()}
    }

    # Save JSON
    output_json = report_dir / '05_failures' / 'failure_catalog.json'
    output_json.parent.mkdir(parents=True, exist_ok=True)

    catalog_data = {
        'generated_at': datetime.now().isoformat(),
        'stats': stats,
        'failures_by_category': dict(by_category),
        'all_failures': failures
    }

    with open(output_json, 'w') as f:
        json.dump(catalog_data, f, indent=2)

    print(f"[OK] Failure catalog saved to {output_json}")

    # Generate markdown
    md_lines = [
        "# Failure Catalog",
        "",
        f"**Total Failures:** {stats['total_failures']}",
        "",
        "## Summary by Category",
        "",
        "| Category | Count | Description |",
        "|----------|-------|-------------|",
    ]

    category_descriptions = {
        'MISSING-DEP': 'Missing dependencies or import errors',
        'ENV-INFRA': 'Requires external infrastructure (DB, Redis, etc.)',
        'LOGIC-BUG': 'Logic errors or test failures',
        'FLAKY': 'Flaky tests or timeouts',
        'LIVE-ONLY': 'Requires live external services',
        'UNKNOWN': 'Unknown category'
    }

    for category, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        desc = category_descriptions.get(category, 'Unknown')
        md_lines.append(f"| {category} | {count} | {desc} |")

    md_lines.append("")
    md_lines.append("## Failures by Category")
    md_lines.append("")

    for category in sorted(by_category.keys()):
        items = by_category[category]
        md_lines.append(f"### {category} ({len(items)} failures)")
        md_lines.append("")
        md_lines.append("| CAP ID | Title | Evidence | Remediation |")
        md_lines.append("|--------|-------|----------|-------------|")

        for item in sorted(items, key=lambda x: x['cap_id']):
            title = item['cap_title'][:40]
            evidence = item['evidence'][:60].replace('|', '\\|').replace('\n', ' ')
            remediation = item['remediation'][:80].replace('|', '\\|')
            md_lines.append(f"| {item['cap_id']} | {title} | {evidence} | {remediation} |")

        md_lines.append("")

    md_lines.append("## Recommended Actions")
    md_lines.append("")
    md_lines.append("### Wave 1: Environment Setup")
    md_lines.append("1. Install all dependencies: `pip install -r requirements.txt`")
    md_lines.append("2. Set up virtual environment if not already done")
    md_lines.append("3. Fix import paths and module structure issues")
    md_lines.append("")
    md_lines.append("### Wave 2: Infrastructure Dependencies")
    md_lines.append("1. Set up docker-compose for external services (PostgreSQL, Redis, ChromaDB)")
    md_lines.append("2. Create comprehensive mocks for services not needed in dev/test")
    md_lines.append("3. Update test fixtures to use mocks by default")
    md_lines.append("")
    md_lines.append("### Wave 3: Fix Logic Bugs")
    md_lines.append("1. Review test failure logs and fix implementation issues")
    md_lines.append("2. Ensure all agents handle mock mode correctly")
    md_lines.append("3. Add missing test coverage")

    output_md = report_dir / '05_failures' / 'failure_catalog.md'
    with open(output_md, 'w') as f:
        f.write('\n'.join(md_lines))

    print(f"[OK] Markdown catalog saved to {output_md}")
    print(f"\nStats by category: {stats['by_category']}")


if __name__ == '__main__':
    main()
