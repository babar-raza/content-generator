"""
Package Artifacts for ChatGPT Upload

Creates a portable tar.gz archive containing all verification artifacts.
"""

import tarfile
import json
from pathlib import Path
from datetime import datetime


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


def create_archive():
    """Create tar.gz archive of all artifacts."""
    repo_root = get_repo_root()
    report_dir = get_latest_report_dir()
    ts = report_dir.name

    archive_name = f"capability_verify_artifacts_{ts}.tar.gz"
    archive_path = repo_root / archive_name

    print(f"Creating archive: {archive_name}")
    print(f"Source: {report_dir}")
    print()

    with tarfile.open(archive_path, 'w:gz') as tar:
        # Add the entire report directory
        tar.add(report_dir, arcname=f"capability_verify_{ts}")

        # Add tools directory
        tools_dir = repo_root / 'tools'
        if tools_dir.exists():
            for tool_file in tools_dir.glob('*.py'):
                tar.add(tool_file, arcname=f"capability_verify_{ts}/tools/{tool_file.name}")

        print(f"[OK] Archive created: {archive_path}")

    return archive_path, ts


def generate_upload_manifest(archive_path: Path, ts: str):
    """Generate a manifest of what's in the archive."""
    report_dir = get_latest_report_dir()

    manifest = {
        'timestamp': ts,
        'archive_file': archive_path.name,
        'archive_size_mb': round(archive_path.stat().st_size / (1024 * 1024), 2),
        'created_at': datetime.now().isoformat(),
        'key_files_to_review': [
            '01_capabilities/capabilities.md',
            '02_individual_verification/individual_results.md',
            '03_pipeline_verification/pipeline_results.md',
            '04_e2e_verification/e2e_results.md',
            '05_failures/failure_catalog.md',
            '07_summary/FINAL_SUMMARY.md',
            'self_reviews/implementation_self_review.md',
            'self_reviews/orchestrator_review.md'
        ],
        'contents': {
            'tools': 'Reusable Python scripts for capability indexing and verification',
            '00_baseline': 'Git status, dependencies, baseline pytest results',
            '01_capabilities': 'Complete capability matrix (JSON + Markdown)',
            '02_individual_verification': 'Individual capability verification results + logs',
            '03_pipeline_verification': 'Pipeline and workflow verification',
            '04_e2e_verification': 'E2E Web API and MCP verification',
            '05_failures': 'Categorized failure catalog with remediation plans',
            '06_diffs': 'Git diff of changes made',
            '07_summary': 'Final summary and recommendations',
            'self_reviews': 'Self-assessment and orchestrator review'
        }
    }

    manifest_file = report_dir / 'UPLOAD_MANIFEST.json'
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"[OK] Manifest created: {manifest_file}")

    return manifest


def print_final_output(archive_path: Path, ts: str, manifest: dict):
    """Print final output as required."""
    repo_root = get_repo_root()
    report_dir = get_latest_report_dir()

    print()
    print("=" * 80)
    print("CAPABILITY VERIFICATION COMPLETE")
    print("=" * 80)
    print()
    print(f"1) TS: {ts}")
    print()
    print(f"2) Archive (for ChatGPT upload):")
    print(f"   {archive_path.absolute()}")
    print()
    print(f"3) Report directory:")
    print(f"   {report_dir.absolute()}")
    print()
    print(f"4) Key files to upload first:")
    for key_file in manifest['key_files_to_review']:
        full_path = report_dir / key_file
        if full_path.exists():
            print(f"   - {key_file}")
    print()
    print(f"Archive size: {manifest['archive_size_mb']} MB")
    print()
    print("=" * 80)


def main():
    """Main entry point."""
    print("=== Packaging Artifacts ===\n")

    archive_path, ts = create_archive()
    manifest = generate_upload_manifest(archive_path, ts)
    print_final_output(archive_path, ts, manifest)


if __name__ == '__main__':
    main()
