#!/usr/bin/env python3
"""Cluster failures by category and generate reports."""
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
import sys


def cluster_failures(failures: List[Dict]) -> Dict[str, List[Dict]]:
    """Group failures by category."""
    clusters = defaultdict(list)
    for failure in failures:
        clusters[failure["category"]].append(failure)
    return dict(clusters)


def generate_cluster_report(clusters: Dict[str, List[Dict]]) -> str:
    """Generate markdown report of clustered failures."""
    report = "# Failure Clusters\n\n"
    report += f"Total unique categories: {len(clusters)}\n\n"
    report += "## Summary by Category\n\n"

    # Sort by count descending
    sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)

    report += "| Category | Count | Impact |\n"
    report += "|----------|-------|--------|\n"

    for category, failures in sorted_clusters:
        impact = "HIGH" if len(failures) >= 10 else "MEDIUM" if len(failures) >= 5 else "LOW"
        report += f"| {category} | {len(failures)} | {impact} |\n"

    report += "\n## Detailed Clusters\n\n"

    for category, failures in sorted_clusters:
        report += f"### {category} ({len(failures)} failures)\n\n"

        # Show sample nodeids
        report += "**Failed tests:**\n"
        for failure in failures[:10]:  # Limit to 10 per cluster
            report += f"- `{failure['nodeid']}`\n"
        if len(failures) > 10:
            report += f"- (...and {len(failures) - 10} more)\n"

        # Show common error pattern
        if failures:
            report += f"\n**Sample error:**\n```\n{failures[0]['headline']}\n```\n\n"

    return report


def main():
    if len(sys.argv) != 2:
        print("Usage: cluster_failures.py <failures_json>")
        sys.exit(1)

    failures_json = Path(sys.argv[1])
    output_dir = failures_json.parent

    with open(failures_json, "r", encoding="utf-8") as f:
        failures = json.load(f)

    clusters = cluster_failures(failures)

    # Save JSON
    clusters_json = output_dir / "failure_clusters.json"
    with open(clusters_json, "w", encoding="utf-8") as f:
        json.dump(clusters, f, indent=2)

    # Save Markdown
    report = generate_cluster_report(clusters)
    clusters_md = output_dir / "failure_clusters.md"
    with open(clusters_md, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Clustered {len(failures)} failures into {len(clusters)} categories")
    print(f"Saved to: {clusters_json} and {clusters_md}")


if __name__ == "__main__":
    main()
