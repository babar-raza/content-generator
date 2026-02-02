#!/usr/bin/env python3
"""Aspose-specific Production Try Runner - Pipeline Validation Matrix

Runs 3 scenarios × 3 topics = 9 total validations using existing Aspose collection.
"""
import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import re

# Configure environment BEFORE imports
os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["ALLOW_NETWORK"] = "0"
os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ["OLLAMA_MODEL"] = os.getenv("OLLAMA_MODEL", "phi4-mini:latest")
os.environ["CHROMA_HOST"] = os.getenv("CHROMA_HOST", "localhost")
os.environ["CHROMA_PORT"] = os.getenv("CHROMA_PORT", "9100")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.frontmatter_normalize import normalize_frontmatter, has_valid_frontmatter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

MIN_SIZE = 2048  # 2KB minimum
MIN_HEADINGS = 3
MIN_RETRIEVAL = 1


def slugify(text: str) -> str:
    """Convert topic to slug."""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def validate_output(file_path: Path, retrieval_file: Optional[Path] = None) -> Tuple[bool, Dict[str, Any]]:
    """Validate output file meets all requirements."""
    details = {
        "exists": False,
        "size": 0,
        "has_frontmatter": False,
        "frontmatter_normalized": False,
        "heading_count": 0,
        "retrieval_count": 0,
        "errors": []
    }

    if not file_path.exists():
        details["errors"].append(f"File not found: {file_path}")
        return False, details

    details["exists"] = True
    size = file_path.stat().st_size
    details["size"] = size

    if size < MIN_SIZE:
        details["errors"].append(f"Size {size} < {MIN_SIZE} bytes")

    try:
        content = file_path.read_text(encoding='utf-8')

        # Check frontmatter
        if has_valid_frontmatter(content):
            details["has_frontmatter"] = True
            details["frontmatter_normalized"] = True
        else:
            details["errors"].append("Missing or invalid YAML frontmatter")

        # Count headings
        heading_count = content.count('\n#')
        details["heading_count"] = heading_count
        if heading_count < MIN_HEADINGS:
            details["errors"].append(f"Headings {heading_count} < {MIN_HEADINGS}")

    except Exception as e:
        details["errors"].append(f"Read error: {e}")

    # Check retrieval evidence
    if retrieval_file and retrieval_file.exists():
        try:
            with open(retrieval_file) as f:
                retrieval_data = json.load(f)
            retrieval_count = len(retrieval_data.get("results", []))
            details["retrieval_count"] = retrieval_count
            if retrieval_count < MIN_RETRIEVAL:
                details["errors"].append(f"Retrieval {retrieval_count} < {MIN_RETRIEVAL}")
        except Exception as e:
            details["errors"].append(f"Retrieval parse error: {e}")
    else:
        details["errors"].append("No retrieval evidence file")

    passed = len(details["errors"]) == 0
    return passed, details


def run_engine_scenario(
    topic: str,
    topic_slug: str,
    ts: str,
    collection: str,
    report_dir: Path,
    run_dir: Path
) -> Dict[str, Any]:
    """S1: Engine - in-process workflow execution."""
    print(f"  Running S1 (Engine) for: {topic}")
    start_time = time.time()

    output_dir = Path(f".live_e2e_data/{ts}/outputs/engine/{topic_slug}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "scenario": "S1_engine",
        "topic": topic,
        "topic_slug": topic_slug,
        "status": "UNKNOWN",
        "duration_sec": 0,
        "output_path": str(output_dir / "generated_content.md"),
        "output_size": 0,
        "validation": {},
        "retrieval_count": 0,
        "error": None
    }

    # Run engine workflow via run_live_workflow_v2
    cmd = [
        sys.executable, "tools/live_e2e/run_live_workflow_v2.py",
        "--topic", topic,
        "--output-dir", str(output_dir),
        "--report-dir", str(run_dir),
        "--collection", collection
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start_time
        result["duration_sec"] = round(duration, 2)

        # Save logs
        log_file = run_dir / "engine.log"
        log_file.write_text(proc.stdout + "\n" + proc.stderr)

        if proc.returncode != 0:
            result["status"] = "FAIL"
            result["error"] = f"Engine failed with code {proc.returncode}"
            return result

        # Find and validate output
        output_file = output_dir / "generated_content.md"
        retrieval_file = run_dir / "retrieval_used.json"

        # Normalize frontmatter if needed
        if output_file.exists():
            content = output_file.read_text(encoding='utf-8')
            normalized = normalize_frontmatter(content)
            if normalized != content:
                output_file.write_text(normalized, encoding='utf-8')

        passed, validation = validate_output(output_file, retrieval_file)
        result["validation"] = validation
        result["output_size"] = validation.get("size", 0)
        result["retrieval_count"] = validation.get("retrieval_count", 0)
        result["status"] = "PASS" if passed else "FAIL"
        if not passed:
            result["error"] = "; ".join(validation.get("errors", []))

    except subprocess.TimeoutExpired:
        result["status"] = "FAIL"
        result["error"] = "Timeout after 300s"
    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)

    return result


def run_rest_scenario(
    topic: str,
    topic_slug: str,
    ts: str,
    collection: str,
    report_dir: Path,
    run_dir: Path
) -> Dict[str, Any]:
    """S2: REST API - POST /api/jobs."""
    print(f"  Running S2 (REST API) for: {topic}")
    start_time = time.time()

    output_dir = Path(f".live_e2e_data/{ts}/outputs/rest/{topic_slug}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "scenario": "S2_rest",
        "topic": topic,
        "topic_slug": topic_slug,
        "status": "UNKNOWN",
        "duration_sec": 0,
        "output_path": "",
        "output_size": 0,
        "validation": {},
        "retrieval_count": 0,
        "error": None
    }

    result_file = run_dir / "rest_result.json"

    cmd = [
        sys.executable, "tools/live_e2e/rest_phase_aspose.py",
        "--topic", topic,
        "--output-dir", str(output_dir),
        "--collection", collection,
        "--result-file", str(result_file)
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start_time
        result["duration_sec"] = round(duration, 2)

        log_file = run_dir / "rest.log"
        log_file.write_text(proc.stdout + "\n" + proc.stderr)

        if result_file.exists():
            with open(result_file) as f:
                sub_result = json.load(f)
            result.update(sub_result)
        else:
            result["status"] = "FAIL"
            result["error"] = "No result file from subprocess"

    except subprocess.TimeoutExpired:
        result["status"] = "FAIL"
        result["error"] = "Timeout after 300s"
    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)

    return result


def run_mcp_scenario(
    topic: str,
    topic_slug: str,
    ts: str,
    collection: str,
    report_dir: Path,
    run_dir: Path
) -> Dict[str, Any]:
    """S3: MCP workflow.execute."""
    print(f"  Running S3 (MCP) for: {topic}")
    start_time = time.time()

    output_dir = Path(f".live_e2e_data/{ts}/outputs/mcp/{topic_slug}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "scenario": "S3_mcp",
        "topic": topic,
        "topic_slug": topic_slug,
        "status": "UNKNOWN",
        "duration_sec": 0,
        "output_path": "",
        "output_size": 0,
        "validation": {},
        "retrieval_count": 0,
        "error": None
    }

    result_file = run_dir / "mcp_result.json"

    cmd = [
        sys.executable, "tools/live_e2e/mcp_phase_aspose.py",
        "--topic", topic,
        "--output-dir", str(output_dir),
        "--collection", collection,
        "--result-file", str(result_file)
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start_time
        result["duration_sec"] = round(duration, 2)

        log_file = run_dir / "mcp.log"
        log_file.write_text(proc.stdout + "\n" + proc.stderr)

        if result_file.exists():
            with open(result_file) as f:
                sub_result = json.load(f)
            result.update(sub_result)
        else:
            result["status"] = "FAIL"
            result["error"] = "No result file from subprocess"

    except subprocess.TimeoutExpired:
        result["status"] = "FAIL"
        result["error"] = "Timeout after 300s"
    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)

    return result


def main():
    """Main runner."""
    import argparse
    parser = argparse.ArgumentParser(description='Aspose Matrix Runner')
    parser.add_argument('--collection', required=True, help='ChromaDB collection name')
    parser.add_argument('--output-dir', required=True, help='Output directory for reports')
    parser.add_argument('--topics', nargs='+', required=True, help='Topics to test')
    args = parser.parse_args()

    collection = args.collection
    report_dir = Path(args.output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    # Get timestamp
    utc_now = datetime.utcnow()
    karachi_time = utc_now + timedelta(hours=5)
    ts = karachi_time.strftime("%Y%m%d-%H%M")

    topics = args.topics
    print(f"\n{'='*80}")
    print(f"ASPOSE PIPELINE VALIDATION MATRIX")
    print(f"{'='*80}")
    print(f"Timestamp: {ts}")
    print(f"Collection: {collection}")
    print(f"Topics: {', '.join(topics)}")
    print(f"Output: {report_dir}")
    print(f"{'='*80}\n")

    # Define scenarios
    scenarios = [
        ("S1_engine", run_engine_scenario),
        ("S2_rest", run_rest_scenario),
        ("S3_mcp", run_mcp_scenario)
    ]

    all_results = []
    total_runs = len(topics) * len(scenarios)
    pass_count = 0

    for topic in topics:
        topic_slug = slugify(topic)
        for scenario_id, scenario_func in scenarios:
            print(f"\n[{len(all_results)+1}/{total_runs}] {scenario_id} × {topic}")

            run_dir = report_dir / "runs" / scenario_id / topic_slug
            run_dir.mkdir(parents=True, exist_ok=True)

            result = scenario_func(topic, topic_slug, ts, collection, report_dir, run_dir)
            all_results.append(result)

            status_icon = "[PASS]" if result["status"] == "PASS" else "[FAIL]"
            print(f"  {status_icon} {result['status']}")
            if result.get("error"):
                print(f"    Error: {result['error']}")

            if result["status"] == "PASS":
                pass_count += 1

    # Write results
    matrix_results = {
        "timestamp": ts,
        "collection": collection,
        "total_runs": total_runs,
        "pass_count": pass_count,
        "fail_count": total_runs - pass_count,
        "status": "PASS" if pass_count == total_runs else "FAIL",
        "results": all_results
    }

    with open(report_dir / "matrix_results.json", "w") as f:
        json.dump(matrix_results, f, indent=2)

    # Write markdown summary
    md_lines = [
        "# Aspose Pipeline Validation Matrix Results",
        "",
        f"**Timestamp:** {ts}",
        f"**Collection:** {collection}",
        f"**Total Runs:** {total_runs}",
        f"**Passed:** {pass_count}",
        f"**Failed:** {total_runs - pass_count}",
        f"**Status:** {matrix_results['status']}",
        "",
        "## Results by Scenario × Topic",
        ""
    ]

    for result in all_results:
        status_icon = "✅" if result["status"] == "PASS" else "❌"
        md_lines.append(
            f"- {status_icon} **{result['scenario']}** × `{result['topic']}`: "
            f"{result['status']} ({result['duration_sec']}s, "
            f"{result['output_size']} bytes, "
            f"{result['retrieval_count']} retrievals)"
        )
        if result.get("error"):
            md_lines.append(f"  - Error: `{result['error']}`")

    with open(report_dir / "matrix_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Final summary
    print(f"\n{'='*80}")
    print(f"MATRIX COMPLETE: {pass_count}/{total_runs} PASS")
    print(f"{'='*80}")
    print(f"Results: {report_dir / 'matrix_results.json'}")
    print(f"Summary: {report_dir / 'matrix_results.md'}")

    if pass_count < total_runs:
        print(f"\n[FAIL] STOP-THE-LINE: {total_runs - pass_count} runs failed")
        sys.exit(1)
    else:
        print(f"\n[PASS] All {total_runs} runs succeeded")
        sys.exit(0)


if __name__ == "__main__":
    main()
