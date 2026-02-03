#!/usr/bin/env python3
"""Quality gate batch runner v2.0.

Runs quality_gate.py evaluation on multiple outputs and aggregates results.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from quality_gate import evaluate_output


def safe_print(text):
    """Print text safely, handling Unicode errors."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))


def run_quality_audit(jobs_jsonl_path: str, output_base_dir: str = None) -> Dict:
    """Run quality audit on a set of job outputs.

    Args:
        jobs_jsonl_path: Path to jobs.jsonl file with job records
        output_base_dir: Base directory for outputs (optional, can be in job records)

    Returns:
        dict with aggregated results
    """
    jobs_file = Path(jobs_jsonl_path)

    if not jobs_file.exists():
        raise FileNotFoundError(f"Jobs file not found: {jobs_file}")

    # Load jobs
    jobs = []
    with open(jobs_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                jobs.append(json.loads(line))

    safe_print(f"Loaded {len(jobs)} job records from {jobs_file}")

    # Audit each output
    results = []
    pass_count = 0
    fail_count = 0

    for i, job in enumerate(jobs, 1):
        job_id = job['job_id']
        topic = job.get('topic', 'unknown')
        output_path = job.get('output_path', '')

        # Resolve output path
        if output_base_dir and not Path(output_path).is_absolute():
            output_path = str(Path(output_base_dir) / output_path)

        safe_print(f"\n--- Auditing Job {i}/{len(jobs)} ---")
        safe_print(f"Job ID: {job_id}")
        safe_print(f"Topic: {topic[:60]}")
        safe_print(f"Output: {output_path}")

        # Evaluate
        evaluation = evaluate_output(output_path)

        # Augment with job metadata
        result = {
            "job_id": job_id,
            "topic": topic,
            "output_path": output_path,
            **evaluation
        }

        # Print summary
        if result["pass"]:
            safe_print(f"  ✓ PASS")
            pass_count += 1
        else:
            safe_print(f"  ❌ FAIL")
            safe_print(f"  Failures: {', '.join(result['failures'])}")
            fail_count += 1

        safe_print(f"  Metrics: size={result['metrics']['size_bytes']}B, " +
                  f"headings={result['metrics']['heading_count']}, " +
                  f"sections={result['metrics']['section_count']}, " +
                  f"refs={result['metrics']['reference_count']}")

        results.append(result)

    # Summary
    safe_print(f"\n{'=' * 60}")
    safe_print(f"QUALITY AUDIT SUMMARY (v2.0)")
    safe_print(f"Total outputs: {len(results)}")
    safe_print(f"Passed: {pass_count}/{len(results)}")
    safe_print(f"Failed: {fail_count}/{len(results)}")

    if len(results) > 0:
        pass_rate = (pass_count / len(results)) * 100
        safe_print(f"Pass rate: {pass_rate:.1f}%")

    if fail_count > 0:
        safe_print(f"\nFailed outputs:")
        for r in results:
            if not r["pass"]:
                safe_print(f"  - {r['job_id']}: {', '.join(r['failures'][:2])}")

    # Aggregate stats
    aggregated = {
        "timestamp": datetime.now().isoformat(),
        "rubric_version": "2.0",
        "total": len(results),
        "passed": pass_count,
        "failed": fail_count,
        "pass_rate": (pass_count / len(results) * 100) if results else 0,
        "results": results
    }

    return aggregated


def write_results(aggregated: Dict, output_dir: str):
    """Write aggregated results to JSON and markdown."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write JSON
    json_file = output_path / "quality_results_v2.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(aggregated, f, indent=2)

    safe_print(f"\nResults written to {json_file}")

    # Write markdown report
    md_file = output_path / "quality_results_v2.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# Quality Audit Results (Rubric v2.0)\n\n")
        f.write(f"**Timestamp**: {aggregated['timestamp']}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total outputs: {aggregated['total']}\n")
        f.write(f"- Passed: {aggregated['passed']}/{aggregated['total']}\n")
        f.write(f"- Failed: {aggregated['failed']}/{aggregated['total']}\n")
        f.write(f"- Pass rate: {aggregated['pass_rate']:.1f}%\n\n")

        f.write(f"## Rubric v2.0 Criteria\n\n")
        f.write(f"**REQUIRED** (all must pass):\n")
        f.write(f"- A) Frontmatter: Valid YAML between `---` delimiters\n")
        f.write(f"- B) Structure: ≥3 markdown headings\n")
        f.write(f"- C) Completeness: ≥2 substantial content sections\n")
        f.write(f"- D) Grounding: ≥2 references/citations (RAG evidence)\n")
        f.write(f"- E) Size: ≥1800 bytes (hard min), target 2200+\n")
        f.write(f"- F) Safety: No fenced frontmatter blocks\n\n")

        if aggregated['failed'] > 0:
            f.write(f"## Failed Outputs\n\n")
            for r in aggregated['results']:
                if not r['pass']:
                    f.write(f"### Job {r['job_id']}\n\n")
                    f.write(f"- **Topic**: {r['topic']}\n")
                    f.write(f"- **Failures**: {', '.join(r['failures'])}\n")
                    f.write(f"- **Metrics**:\n")
                    f.write(f"  - Size: {r['metrics']['size_bytes']} bytes\n")
                    f.write(f"  - Headings: {r['metrics']['heading_count']}\n")
                    f.write(f"  - Sections: {r['metrics']['section_count']}\n")
                    f.write(f"  - References: {r['metrics']['reference_count']}\n\n")

        f.write(f"## All Results\n\n")
        for i, r in enumerate(aggregated['results'], 1):
            status = "✓ PASS" if r['pass'] else "❌ FAIL"
            f.write(f"{i}. **{status}** - Job {r['job_id'][:8]}\n")
            f.write(f"   - Topic: {r['topic'][:50]}\n")
            f.write(f"   - Size: {r['metrics']['size_bytes']}B, ")
            f.write(f"Headings: {r['metrics']['heading_count']}, ")
            f.write(f"Sections: {r['metrics']['section_count']}, ")
            f.write(f"Refs: {r['metrics']['reference_count']}\n")
            if r['failures']:
                f.write(f"   - Issues: {', '.join(r['failures'][:2])}\n")
            f.write(f"\n")

    safe_print(f"Report written to {md_file}")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: quality_gate_runner.py <jobs_jsonl_path> [output_dir] [output_base_dir]")
        print("  jobs_jsonl_path: Path to jobs.jsonl file")
        print("  output_dir: Directory to write results (default: quality/)")
        print("  output_base_dir: Base dir for resolving relative output paths (optional)")
        sys.exit(1)

    jobs_jsonl_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "quality"
    output_base_dir = sys.argv[3] if len(sys.argv) > 3 else None

    # Run audit
    aggregated = run_quality_audit(jobs_jsonl_path, output_base_dir)

    # Write results
    write_results(aggregated, output_dir)

    # Exit code: 0 if all pass, 1 if any fail
    sys.exit(0 if aggregated['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
