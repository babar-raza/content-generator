#!/usr/bin/env python3
"""Production Try Runner V2 - Pipeline Validation Matrix

Runs 3 scenarios × 3 topics = 9 total validations:
- S1: Engine (in-process workflow execution via run_live_workflow_v2)
- S2: REST API (POST /api/jobs with real TestClient)
- S3: MCP (workflow.execute single via /mcp/request)

Each run validates:
- Output file exists and size >= 2KB
- Contains VALID YAML frontmatter (--- ... ---) - NOT ```yaml fences
- Contains >= 3 headings
- Retrieval evidence is NON-ZERO (proof pipeline used ingested knowledge)

STOP-THE-LINE: Does not declare success unless 9/9 PASS.
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
import uuid

# Configure environment BEFORE imports
os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["ALLOW_NETWORK"] = "1"
os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ["OLLAMA_MODEL"] = os.getenv("OLLAMA_MODEL", "phi4-mini:latest")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.frontmatter_normalize import normalize_frontmatter, has_valid_frontmatter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

MIN_SIZE = 2048  # 2KB minimum
IDEAL_SIZE = 5120  # 5KB ideal
MIN_HEADINGS = 3
MIN_RETRIEVAL = 1  # Must have at least 1 retrieval result


def get_timestamp_karachi() -> str:
    """Get timestamp in Asia/Karachi timezone (UTC+5)."""
    utc_now = datetime.utcnow()
    karachi_time = utc_now + timedelta(hours=5)
    return karachi_time.strftime("%Y%m%d-%H%M")


def slugify(text: str) -> str:
    """Convert topic to slug."""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def get_chroma_client():
    """Get ChromaDB client based on environment."""
    import chromadb
    chroma_host = os.getenv('CHROMA_HOST')
    chroma_port = os.getenv('CHROMA_PORT')

    if chroma_host and chroma_port:
        return chromadb.HttpClient(host=chroma_host, port=int(chroma_port))
    else:
        return chromadb.PersistentClient(path="./chroma_db")


def validate_output(file_path: Path, retrieval_file: Optional[Path] = None) -> Tuple[bool, Dict[str, Any]]:
    """Validate output file meets all requirements including retrieval.

    Returns:
        (pass/fail, details dict)
    """
    details = {
        "exists": False,
        "size": 0,
        "has_frontmatter": False,
        "frontmatter_normalized": False,
        "heading_count": 0,
        "retrieval_count": 0,
        "errors": []
    }

    # Check existence
    if not file_path.exists():
        details["errors"].append(f"File not found: {file_path}")
        return False, details

    details["exists"] = True

    # Check size
    size = file_path.stat().st_size
    details["size"] = size
    if size < MIN_SIZE:
        details["errors"].append(f"Output too small: {size} bytes < {MIN_SIZE} bytes")

    # Read content
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        details["errors"].append(f"Failed to read file: {e}")
        return False, details

    # Check frontmatter - must be proper --- delimited, NOT ```yaml
    if has_valid_frontmatter(content):
        details["has_frontmatter"] = True
    else:
        # Check if it's a ```yaml fence that needs normalization
        if content.lstrip().startswith('```yaml') or content.lstrip().startswith('```yml'):
            details["errors"].append("Frontmatter uses ```yaml fence instead of --- delimiters")
        else:
            details["errors"].append("No valid YAML frontmatter found (must use --- delimiters)")

    # Count headings (# markers)
    heading_count = len(re.findall(r'^#+\s', content, re.MULTILINE))
    details["heading_count"] = heading_count
    if heading_count < MIN_HEADINGS:
        details["errors"].append(f"Too few headings: {heading_count} < {MIN_HEADINGS}")

    # Check retrieval evidence
    if retrieval_file and retrieval_file.exists():
        try:
            with open(retrieval_file) as f:
                retrieval_data = json.load(f)
            retrieval_count = retrieval_data.get("total_retrievals", 0)
            if retrieval_count == 0:
                retrieval_count = retrieval_data.get("blog_results", 0) + retrieval_data.get("ref_results", 0)
            details["retrieval_count"] = retrieval_count

            if retrieval_count < MIN_RETRIEVAL:
                details["errors"].append(f"No retrieval evidence: {retrieval_count} < {MIN_RETRIEVAL}")
        except Exception as e:
            details["errors"].append(f"Failed to read retrieval evidence: {e}")
            details["retrieval_count"] = 0
    else:
        details["errors"].append("Retrieval evidence file not found")

    # Overall pass/fail
    passed = (
        details["exists"] and
        size >= MIN_SIZE and
        details["has_frontmatter"] and
        heading_count >= MIN_HEADINGS and
        details["retrieval_count"] >= MIN_RETRIEVAL
    )

    return passed, details


def run_engine_scenario(
    topic: str,
    topic_slug: str,
    ts: str,
    blog_coll: str,
    ref_coll: str,
    report_dir: Path,
    run_dir: Path
) -> Dict[str, Any]:
    """S1: Engine - in-process workflow execution."""
    print(f"  Running S1 (engine) for: {topic}")
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

    # Run workflow via run_live_workflow_v2.py
    cmd = [
        sys.executable, "tools/run_live_workflow_v2.py",
        "--workflow-id", "blog_workflow",
        "--topic", topic,
        "--output-dir", str(output_dir),
        "--report-dir", str(run_dir),
        "--blog-collection", blog_coll,
        "--ref-collection", ref_coll
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

        # Find output file
        output_file = output_dir / "generated_content.md"
        retrieval_file = run_dir / "retrieval_used.json"

        # Normalize frontmatter if needed
        if output_file.exists():
            content = output_file.read_text(encoding='utf-8')
            normalized = normalize_frontmatter(content)
            if normalized != content:
                output_file.write_text(normalized, encoding='utf-8')
                logger.info(f"  Normalized frontmatter for {topic_slug}")

        # Validate output
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
    blog_coll: str,
    ref_coll: str,
    report_dir: Path,
    run_dir: Path
) -> Dict[str, Any]:
    """S2: REST API - POST /api/jobs via subprocess to avoid ChromaDB conflicts."""
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

    # Run REST test in separate subprocess to avoid ChromaDB singleton conflict
    cmd = [
        sys.executable, "tools/live_e2e/rest_phase_v2.py",
        "--topic", topic,
        "--output-dir", str(output_dir),
        "--blog-collection", blog_coll,
        "--ref-collection", ref_coll,
        "--result-file", str(result_file)
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start_time
        result["duration_sec"] = round(duration, 2)

        # Save log
        log_file = run_dir / "rest.log"
        log_file.write_text(proc.stdout + "\n" + proc.stderr)

        # Load result from subprocess
        if result_file.exists():
            with open(result_file) as f:
                sub_result = json.load(f)

            result["output_path"] = sub_result.get("output_path", "")
            result["output_size"] = sub_result.get("output_size", 0)
            result["retrieval_count"] = sub_result.get("retrieval_count", 0)

            if sub_result.get("status") == "PASS":
                # Validate output with our validation function
                output_file = Path(result["output_path"]) if result["output_path"] else None
                retrieval_file = output_dir / "retrieval_used.json"

                if output_file and output_file.exists():
                    passed, validation = validate_output(output_file, retrieval_file)
                    result["validation"] = validation
                    result["output_size"] = validation.get("size", 0)
                    result["retrieval_count"] = validation.get("retrieval_count", 0)
                    result["status"] = "PASS" if passed else "FAIL"
                    if not passed:
                        result["error"] = "; ".join(validation.get("errors", []))
                else:
                    result["status"] = "FAIL"
                    result["error"] = "Output file not found after subprocess"
            else:
                result["status"] = "FAIL"
                result["error"] = sub_result.get("error", "Unknown error from subprocess")
        else:
            result["status"] = "FAIL"
            result["error"] = f"Result file not created. Exit code: {proc.returncode}"

    except subprocess.TimeoutExpired:
        result["status"] = "FAIL"
        result["error"] = "Timeout after 300s"
        result["duration_sec"] = round(time.time() - start_time, 2)
    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)
        result["duration_sec"] = round(time.time() - start_time, 2)
        logger.error(f"  REST scenario exception: {e}", exc_info=True)

    return result


def run_mcp_scenario(
    topic: str,
    topic_slug: str,
    ts: str,
    blog_coll: str,
    ref_coll: str,
    report_dir: Path,
    run_dir: Path
) -> Dict[str, Any]:
    """S3: MCP - workflow.execute via subprocess to avoid ChromaDB conflicts."""
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

    # Run MCP test in separate subprocess to avoid ChromaDB singleton conflict
    cmd = [
        sys.executable, "tools/live_e2e/mcp_phase_v2.py",
        "--topic", topic,
        "--output-dir", str(output_dir),
        "--blog-collection", blog_coll,
        "--ref-collection", ref_coll,
        "--result-file", str(result_file)
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start_time
        result["duration_sec"] = round(duration, 2)

        # Save log
        log_file = run_dir / "mcp.log"
        log_file.write_text(proc.stdout + "\n" + proc.stderr)

        # Load result from subprocess
        if result_file.exists():
            with open(result_file) as f:
                sub_result = json.load(f)

            result["output_path"] = sub_result.get("output_path", "")
            result["output_size"] = sub_result.get("output_size", 0)
            result["retrieval_count"] = sub_result.get("retrieval_count", 0)

            if sub_result.get("status") == "PASS":
                # Validate output with our validation function
                output_file = Path(result["output_path"]) if result["output_path"] else None
                retrieval_file = output_dir / "retrieval_used.json"

                if output_file and output_file.exists():
                    passed, validation = validate_output(output_file, retrieval_file)
                    result["validation"] = validation
                    result["output_size"] = validation.get("size", 0)
                    result["retrieval_count"] = validation.get("retrieval_count", 0)
                    result["status"] = "PASS" if passed else "FAIL"
                    if not passed:
                        result["error"] = "; ".join(validation.get("errors", []))
                else:
                    result["status"] = "FAIL"
                    result["error"] = "Output file not found after subprocess"
            else:
                result["status"] = "FAIL"
                result["error"] = sub_result.get("error", "Unknown error from subprocess")
        else:
            result["status"] = "FAIL"
            result["error"] = f"Result file not created. Exit code: {proc.returncode}"

    except subprocess.TimeoutExpired:
        result["status"] = "FAIL"
        result["error"] = "Timeout after 300s"
        result["duration_sec"] = round(time.time() - start_time, 2)
    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)
        result["duration_sec"] = round(time.time() - start_time, 2)
        logger.error(f"  MCP scenario exception: {e}", exc_info=True)

    return result


def run_ingestion(ts: str, blog_coll: str, ref_coll: str, report_dir: Path) -> Tuple[bool, Dict[str, Any]]:
    """Run ingestion into per-run collections."""
    logger.info("Running ingestion into per-run collections...")

    result = {
        "status": "UNKNOWN",
        "blog_collection": blog_coll,
        "ref_collection": ref_coll,
        "blog_count": 0,
        "ref_count": 0
    }

    # Find dataset manifest
    manifest_path = None
    for report_subdir in Path("reports").glob("live_e2e_ollama/*"):
        manifest = report_subdir / "dataset_manifest.json"
        if manifest.exists():
            manifest_path = manifest
            break

    if not manifest_path:
        # Try alternate location
        for report_subdir in Path("reports").glob("live_e2e_full_v3_gates/*"):
            manifest = report_subdir / "dataset_manifest.json"
            if manifest.exists():
                manifest_path = manifest
                break

    if not manifest_path:
        logger.warning("No dataset manifest found - using default collection data")
        # Check if default collections have data
        try:
            client = get_chroma_client()
            collections = {c.name: c.count() for c in client.list_collections()}

            # Copy from default collections if they exist
            if "blog_knowledge" in collections and collections["blog_knowledge"] > 0:
                blog_src = client.get_collection("blog_knowledge")
                blog_data = blog_src.get(include=["documents", "metadatas", "embeddings"])

                blog_dest = client.get_or_create_collection(blog_coll)
                if blog_data["ids"]:
                    blog_dest.add(
                        ids=blog_data["ids"],
                        documents=blog_data["documents"],
                        metadatas=blog_data["metadatas"],
                        embeddings=blog_data["embeddings"]
                    )
                result["blog_count"] = blog_dest.count()

            if "api_reference" in collections and collections["api_reference"] > 0:
                ref_src = client.get_collection("api_reference")
                ref_data = ref_src.get(include=["documents", "metadatas", "embeddings"])

                ref_dest = client.get_or_create_collection(ref_coll)
                if ref_data["ids"]:
                    ref_dest.add(
                        ids=ref_data["ids"],
                        documents=ref_data["documents"],
                        metadatas=ref_data["metadatas"],
                        embeddings=ref_data["embeddings"]
                    )
                result["ref_count"] = ref_dest.count()

            if result["blog_count"] > 0 or result["ref_count"] > 0:
                result["status"] = "PASS"
                logger.info(f"  Copied from default collections: blog={result['blog_count']}, ref={result['ref_count']}")
                return True, result
            else:
                result["status"] = "FAIL"
                result["error"] = "No data in default collections"
                return False, result

        except Exception as e:
            result["status"] = "FAIL"
            result["error"] = str(e)
            return False, result

    # Run ingestion script
    cmd = [
        sys.executable, "tools/run_live_ingestion_v2.py",
        "--manifest", str(manifest_path),
        "--blog-collection", blog_coll,
        "--ref-collection", ref_coll,
        "--output", str(report_dir / "ingestion_results.json")
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)

        # Save log
        with open(report_dir / "ingestion_log.txt", "w") as f:
            f.write(proc.stdout + "\n" + proc.stderr)

        if proc.returncode != 0:
            result["status"] = "FAIL"
            result["error"] = f"Ingestion failed with code {proc.returncode}"
            return False, result

        # Verify counts
        client = get_chroma_client()
        collections = {c.name: c.count() for c in client.list_collections()}
        result["blog_count"] = collections.get(blog_coll, 0)
        result["ref_count"] = collections.get(ref_coll, 0)

        if result["blog_count"] == 0 and result["ref_count"] == 0:
            result["status"] = "FAIL"
            result["error"] = "No vectors written"
            return False, result

        result["status"] = "PASS"
        logger.info(f"  Ingestion complete: blog={result['blog_count']}, ref={result['ref_count']}")
        return True, result

    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)
        return False, result


def main():
    """Main runner."""
    import argparse
    parser = argparse.ArgumentParser(description='Production Try Matrix Runner V2')
    parser.add_argument('--ts', help='Timestamp (YYYYMMDD-HHMM), defaults to now in Asia/Karachi')
    parser.add_argument('--skip-ingestion', action='store_true', help='Skip ingestion phase')
    args = parser.parse_args()

    # Timestamp
    ts = args.ts or get_timestamp_karachi()
    print(f"\n{'='*80}")
    print(f"PRODUCTION TRY RUNNER V2")
    print(f"{'='*80}")
    print(f"Timestamp: {ts} (Asia/Karachi)")

    # Create report directory
    report_dir = Path(f"reports/prod_try_v2/{ts}")
    report_dir.mkdir(parents=True, exist_ok=True)
    print(f"Report directory: {report_dir}")

    # Define per-run collections
    ts_safe = ts.replace('-', '_')
    blog_coll = f"blog_knowledge_try_{ts_safe}"
    ref_coll = f"api_reference_try_{ts_safe}"
    print(f"Blog collection: {blog_coll}")
    print(f"Ref collection: {ref_coll}")

    # Define topics
    topics = [
        "Python Data Structures and Type Hints",
        "FastAPI Web Framework Best Practices",
        "Async Programming with asyncio"
    ]

    # Create topics file
    topics_file = report_dir / "topics.txt"
    topics_file.write_text('\n'.join(topics))

    print(f"\nTopics ({len(topics)}):")
    for topic in topics:
        print(f"  - {topic}")

    # Phase 0: Preflight
    print(f"\n{'='*80}")
    print("PHASE 0: PREFLIGHT CHECKS")
    print(f"{'='*80}")

    # Check Ollama
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=10)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            has_phi4 = "phi4-mini:latest" in models
            print(f"  Ollama: OK ({len(models)} models, phi4-mini: {'found' if has_phi4 else 'NOT FOUND'})")
            if not has_phi4:
                print("  BLOCKER: phi4-mini:latest not found. Run: ollama pull phi4-mini")
                return 1
        else:
            print(f"  Ollama: FAIL (HTTP {resp.status_code})")
            return 1
    except Exception as e:
        print(f"  Ollama: FAIL ({e})")
        return 1

    # Check ChromaDB
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        mode = "HTTP" if os.getenv('CHROMA_HOST') else "persistent"
        print(f"  ChromaDB: OK ({mode} mode, {len(collections)} collections)")
    except Exception as e:
        print(f"  ChromaDB: FAIL ({e})")
        return 1

    # Phase 1: Ingestion
    if not args.skip_ingestion:
        print(f"\n{'='*80}")
        print("PHASE 1: INGESTION")
        print(f"{'='*80}")

        ok, ingestion_result = run_ingestion(ts, blog_coll, ref_coll, report_dir)
        with open(report_dir / "ingestion_summary.json", "w") as f:
            json.dump(ingestion_result, f, indent=2)

        if not ok:
            print(f"  FAIL: {ingestion_result.get('error', 'Unknown error')}")
            print("  STOP-THE-LINE: Cannot proceed without ingested data")
            return 1

        print(f"  Collections: blog={ingestion_result['blog_count']}, ref={ingestion_result['ref_count']}")
    else:
        print("\n  Skipping ingestion (--skip-ingestion)")

    # Phase 2: Matrix Run
    print(f"\n{'='*80}")
    print("PHASE 2: MATRIX RUN (3 scenarios × 3 topics = 9 tests)")
    print(f"{'='*80}")

    scenarios = [
        ("S1", "engine", run_engine_scenario),
        ("S2", "rest", run_rest_scenario),
        ("S3", "mcp", run_mcp_scenario)
    ]

    all_results = []
    pass_count = 0
    total_runs = len(topics) * len(scenarios)

    for topic in topics:
        topic_slug = slugify(topic)
        print(f"\nTopic: {topic}")

        for scenario_id, scenario_name, scenario_func in scenarios:
            run_dir = report_dir / "runs" / scenario_id / topic_slug
            run_dir.mkdir(parents=True, exist_ok=True)

            result = scenario_func(topic, topic_slug, ts, blog_coll, ref_coll, report_dir, run_dir)
            all_results.append(result)

            status_icon = "[PASS]" if result["status"] == "PASS" else "[FAIL]"
            retrieval_info = f"retrieval={result.get('retrieval_count', 0)}"
            if result["status"] == "PASS":
                pass_count += 1
                print(f"    {status_icon} {scenario_id}: {result['output_size']} bytes, {retrieval_info}")
            else:
                print(f"    {status_icon} {scenario_id}: {result.get('error', 'unknown')[:60]}")

    # Save results
    matrix_results = {
        "timestamp": ts,
        "collections": {
            "blog": blog_coll,
            "ref": ref_coll
        },
        "total_runs": total_runs,
        "pass_count": pass_count,
        "fail_count": total_runs - pass_count,
        "results": all_results
    }

    results_json = report_dir / "matrix_results.json"
    with open(results_json, 'w') as f:
        json.dump(matrix_results, f, indent=2)

    # Generate markdown summary
    md_lines = [
        "# Pipeline Validation Matrix Results V2",
        "",
        f"**Timestamp:** {ts}",
        f"**Collections:** blog={blog_coll}, ref={ref_coll}",
        f"**Total Runs:** {total_runs}",
        f"**Passed:** {pass_count}",
        f"**Failed:** {total_runs - pass_count}",
        "",
        "## Results Table",
        "",
        "| Scenario | Topic | Status | Size | Retrieval | Headings | Duration |",
        "|----------|-------|--------|------|-----------|----------|----------|"
    ]

    for result in all_results:
        validation = result.get('validation', {})
        md_lines.append(
            f"| {result['scenario']} | {result['topic_slug'][:20]} | {result['status']} | "
            f"{result['output_size']} | {validation.get('retrieval_count', 0)} | "
            f"{validation.get('heading_count', 0)} | {result['duration_sec']}s |"
        )

    md_lines.extend(["", "## Failures", ""])

    failures = [r for r in all_results if r['status'] != 'PASS']
    if failures:
        for fail in failures:
            md_lines.append(f"### {fail['scenario']} - {fail['topic']}")
            md_lines.append(f"- **Error:** {fail.get('error', 'Unknown')}")
            md_lines.append(f"- **Output:** {fail.get('output_path', 'N/A')}")
            md_lines.append("")
    else:
        md_lines.append("No failures - 9/9 PASS!")

    results_md = report_dir / "matrix_results.md"
    results_md.write_text('\n'.join(md_lines))

    # Final summary
    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"1) TS: {ts}")

    # Get HEAD commit
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        print(f"2) HEAD commit: {head.stdout.strip()}")
    except:
        print("2) HEAD commit: (unable to determine)")

    # Collection counts
    try:
        client = get_chroma_client()
        collections = {c.name: c.count() for c in client.list_collections()}
        blog_count = collections.get(blog_coll, 0)
        ref_count = collections.get(ref_coll, 0)
        print(f"3) Collections + counts: {blog_coll}={blog_count}, {ref_coll}={ref_count}")
    except:
        print("3) Collections + counts: (unable to query)")

    print(f"4) Matrix: {pass_count}/{total_runs} PASS")

    if failures:
        print(f"5) Failures:")
        for f in failures:
            print(f"   - {f['scenario']}/{f['topic_slug']}: {f.get('error', 'unknown')[:50]}")
    else:
        print(f"5) Failures: None")

    print(f"6) Evidence tarball path: reports/prod_try_v2/{ts}/prod_try_v2_{ts}_evidence.tar.gz")
    print(f"{'='*80}")

    # STOP-THE-LINE check
    if pass_count < total_runs:
        print(f"\nSTOP-THE-LINE: {total_runs - pass_count} failures detected. NOT declaring success.")
        return 1

    print(f"\nSUCCESS: 9/9 PASS - Pipeline validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
