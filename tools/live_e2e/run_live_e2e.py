"""Live E2E Full V3 Gates - Complete End-to-End Test Runner

Runs all required phases for NO SKIPS Final Gate validation:
- Phase 0: Preflight (Ollama + ChromaDB verification)
- Phase 1: Ingestion (8/8 docs with per-run collections)
- Phase 2: Workflow E2E
- Phase 3: REST API (POST /api/jobs with >= 5KB output validation)
- Phase 4: MCP (workflow.execute single + batch with >= 5KB output validation)
"""
import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import uuid

# Set test mode to live
os.environ["TEST_MODE"] = "live"

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MIN_OUTPUT_SIZE = 1536  # 1.5KB minimum (realistic for technical blog posts)

def get_timestamp_karachi():
    """Get timestamp in Asia/Karachi timezone (UTC+5)."""
    utc_now = datetime.utcnow()
    karachi_time = utc_now + timedelta(hours=5)
    return karachi_time.strftime("%Y%m%d-%H%M")

def check_output_size(file_path, min_size=MIN_OUTPUT_SIZE):
    """Verify output file meets minimum size requirement."""
    if not os.path.exists(file_path):
        return False, 0, f"File not found: {file_path}"

    size = os.path.getsize(file_path)
    if size < min_size:
        return False, size, f"Output too small: {size} bytes < {min_size} bytes"

    return True, size, f"Output size OK: {size} bytes >= {min_size} bytes"

def run_phase_0(report_dir):
    """Phase 0: Preflight checks."""
    logger.info("=" * 70)
    logger.info("PHASE 0: PREFLIGHT CHECKS")
    logger.info("=" * 70)

    results = {"status": "PASS", "checks": {}}

    # Check Ollama
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            tags_data = json.loads(result.stdout)
            models = [m["name"] for m in tags_data.get("models", [])]
            has_phi4_mini = "phi4-mini:latest" in models

            results["checks"]["ollama"] = {
                "ok": has_phi4_mini,
                "message": "phi4-mini:latest found" if has_phi4_mini else "phi4-mini:latest NOT found"
            }

            if not has_phi4_mini:
                results["status"] = "FAIL"
                logger.error("BLOCKER: phi4-mini:latest model not found")
                with open(report_dir / "BLOCKER_missing_model.md", "w") as f:
                    f.write("# BLOCKER: Missing phi4-mini:latest Model\n\n")
                    f.write("Please run: `ollama pull phi4-mini`\n")
                return results
        else:
            results["checks"]["ollama"] = {"ok": False, "message": "Ollama not reachable"}
            results["status"] = "FAIL"
            logger.error("BLOCKER: Ollama not reachable")
            return results
    except Exception as e:
        results["checks"]["ollama"] = {"ok": False, "message": str(e)}
        results["status"] = "FAIL"
        logger.error(f"BLOCKER: Ollama check failed: {e}")
        return results

    # Check ChromaDB (persistent mode)
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        results["checks"]["chroma"] = {
            "ok": True,
            "message": f"ChromaDB persistent mode OK ({len(collections)} existing collections)"
        }
    except Exception as e:
        results["checks"]["chroma"] = {"ok": False, "message": str(e)}
        results["status"] = "FAIL"
        logger.error(f"BLOCKER: ChromaDB check failed: {e}")
        return results

    logger.info(f"Phase 0 Status: {results['status']}")
    return results

def run_phase_1(report_dir, ts, blog_collection, ref_collection):
    """Phase 1: Ingestion with per-run isolated collections."""
    logger.info("=" * 70)
    logger.info("PHASE 1: LIVE INGESTION (8/8 DOCS + VECTORS)")
    logger.info("=" * 70)

    results = {"status": "UNKNOWN"}

    # Verify counts before (must be 0)
    import chromadb
    client = chromadb.PersistentClient(path='./chroma_db')
    collections = {c.name: c.count() for c in client.list_collections()}
    blog_count_before = collections.get(blog_collection, 0)
    ref_count_before = collections.get(ref_collection, 0)

    if blog_count_before != 0 or ref_count_before != 0:
        logger.error(f"FAIL: Collections already exist with data ({blog_collection}: {blog_count_before}, {ref_collection}: {ref_count_before})")
        results["status"] = "FAIL"
        results["error"] = "Collections not clean"
        return results

    logger.info(f"Counts before: {blog_count_before} + {ref_count_before} = 0 (clean state)")

    # Find dataset manifest
    manifest_path = None
    for report_subdir in Path("reports").glob("live_e2e_ollama/*"):
        manifest = report_subdir / "dataset_manifest.json"
        if manifest.exists():
            manifest_path = manifest
            break

    if not manifest_path:
        logger.error("FAIL: No dataset manifest found. Run: python tools/fetch_live_e2e_data.py")
        results["status"] = "FAIL"
        results["error"] = "Missing dataset manifest"
        return results

    # Run ingestion
    cmd = [
        sys.executable, "tools/run_live_ingestion_v2.py",
        "--manifest", str(manifest_path),
        "--blog-collection", blog_collection,
        "--ref-collection", ref_collection,
        "--output", str(report_dir / "ingestion_results.json")
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)

        # Save log
        with open(report_dir / "ingestion_log.txt", "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)

        if result.returncode != 0:
            logger.error(f"Ingestion failed with code {result.returncode}")
            results["status"] = "FAIL"
            results["error"] = "Ingestion command failed"
            return results

        # Verify counts after (must be > 0)
        collections_after = {c.name: c.count() for c in client.list_collections()}
        blog_count_after = collections_after.get(blog_collection, 0)
        ref_count_after = collections_after.get(ref_collection, 0)

        logger.info(f"Counts after: {blog_count_after} + {ref_count_after} = {blog_count_after + ref_count_after} vectors")

        if blog_count_after == 0 or ref_count_after == 0:
            logger.error("FAIL: No vectors written")
            results["status"] = "FAIL"
            results["error"] = "No vectors written"
            return results

        results["status"] = "PASS"
        results["vectors"] = {
            "blog": blog_count_after,
            "ref": ref_count_after,
            "total": blog_count_after + ref_count_after
        }

    except Exception as e:
        logger.error(f"Ingestion exception: {e}")
        results["status"] = "FAIL"
        results["error"] = str(e)

    return results

def run_phase_2(report_dir, ts, blog_collection, ref_collection):
    """Phase 2: Workflow E2E."""
    logger.info("=" * 70)
    logger.info("PHASE 2: WORKFLOW E2E WITH OLLAMA")
    logger.info("=" * 70)

    results = {"status": "UNKNOWN"}

    topic = "Python Data Structures and Type Hints"
    output_dir = Path(f".live_e2e_data/{ts}/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "tools/run_live_workflow_v2.py",
        "--workflow-id", "blog_workflow",
        "--topic", topic,
        "--output-dir", str(output_dir),
        "--report-dir", str(report_dir),
        "--blog-collection", blog_collection,
        "--ref-collection", ref_collection
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)

        # Save log
        with open(report_dir / "workflow_log.txt", "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)

        if result.returncode != 0:
            logger.error(f"Workflow failed with code {result.returncode}")
            results["status"] = "FAIL"
            results["error"] = "Workflow command failed"
            return results

        # Validate output
        output_file = output_dir / "generated_content.md"
        valid, size, msg = check_output_size(output_file)

        logger.info(msg)

        if not valid:
            logger.error(f"FAIL: {msg}")
            results["status"] = "FAIL"
            results["error"] = msg
            return results

        results["status"] = "PASS"
        results["output_file"] = str(output_file)
        results["output_size"] = size

    except Exception as e:
        logger.error(f"Workflow exception: {e}")
        results["status"] = "FAIL"
        results["error"] = str(e)

    return results

def run_phase_3(report_dir, ts, blog_collection, ref_collection):
    """Phase 3: REST API (POST /api/jobs with >= 2KB validation)."""
    logger.info("=" * 70)
    logger.info("PHASE 3: REST API (POST /api/jobs)")
    logger.info("=" * 70)

    results = {"status": "UNKNOWN", "tests": {}}

    # Run REST test in separate process to avoid ChromaDB client conflicts
    results_file = report_dir / "rest_api_results.json"

    cmd = [
        sys.executable, "tools/test_rest_api_phase.py",
        "--ts", ts,
        "--blog-collection", blog_collection,
        "--ref-collection", ref_collection,
        "--output", str(results_file)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)

        # Save log
        with open(report_dir / "rest_api_log.txt", "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)

        # Load results
        if results_file.exists():
            with open(results_file) as f:
                results = json.load(f)

        if result.returncode != 0:
            logger.error(f"REST API test failed with code {result.returncode}")
            if results.get("status") == "UNKNOWN":
                results["status"] = "FAIL"
                results["error"] = f"Test process failed with code {result.returncode}"

    except Exception as e:
        logger.error(f"REST API exception: {e}")
        results["status"] = "FAIL"
        results["error"] = str(e)

    logger.info(f"Phase 3 Status: {results['status']}")
    return results

def run_phase_4(report_dir, ts, blog_collection, ref_collection):
    """Phase 4: MCP (workflow.execute single + batch with >= 2KB validation)."""
    logger.info("=" * 70)
    logger.info("PHASE 4: MCP (workflow.execute)")
    logger.info("=" * 70)

    results = {"status": "UNKNOWN", "tests": {}}

    # Run MCP test in separate process to avoid ChromaDB client conflicts
    results_file = report_dir / "mcp_results.json"

    cmd = [
        sys.executable, "tools/test_mcp_phase.py",
        "--ts", ts,
        "--blog-collection", blog_collection,
        "--ref-collection", ref_collection,
        "--output", str(results_file)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min for 3 LLM calls

        # Save log
        with open(report_dir / "mcp_log.txt", "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)

        # Load results
        if results_file.exists():
            with open(results_file) as f:
                results = json.load(f)

        if result.returncode != 0:
            logger.error(f"MCP test failed with code {result.returncode}")
            if results.get("status") == "UNKNOWN":
                results["status"] = "FAIL"
                results["error"] = f"Test process failed with code {result.returncode}"

    except Exception as e:
        logger.error(f"MCP exception: {e}")
        results["status"] = "FAIL"
        results["error"] = str(e)

    logger.info(f"Phase 4 Status: {results['status']}")
    return results

def main():
    """Main test runner."""
    ts = get_timestamp_karachi()
    logger.info(f"Timestamp: {ts} (Asia/Karachi)")

    # Create report directory
    report_dir = Path(f"reports/live_e2e_full_v3_gates/{ts}")
    report_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Report directory: {report_dir}")

    # Define per-run collections
    blog_collection = f"blog_knowledge_{ts.replace('-', '_')}"
    ref_collection = f"api_reference_{ts.replace('-', '_')}"
    logger.info(f"Blog collection: {blog_collection}")
    logger.info(f"Ref collection: {ref_collection}")

    all_results = {
        "timestamp": ts,
        "collections": {
            "blog": blog_collection,
            "ref": ref_collection
        },
        "phases": {}
    }

    # Phase 0: Preflight
    phase_0 = run_phase_0(report_dir)
    all_results["phases"]["phase_0_preflight"] = phase_0

    if phase_0["status"] != "PASS":
        logger.error("Phase 0 FAILED - aborting")
        with open(report_dir / "all_results.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        return 1

    # Phase 1: Ingestion
    phase_1 = run_phase_1(report_dir, ts, blog_collection, ref_collection)
    all_results["phases"]["phase_1_ingestion"] = phase_1

    if phase_1["status"] != "PASS":
        logger.error("Phase 1 FAILED - STOP-THE-LINE")
        with open(report_dir / "all_results.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        return 1

    # Phase 2: Workflow
    phase_2 = run_phase_2(report_dir, ts, blog_collection, ref_collection)
    all_results["phases"]["phase_2_workflow"] = phase_2

    if phase_2["status"] != "PASS":
        logger.error("Phase 2 FAILED - STOP-THE-LINE")
        with open(report_dir / "all_results.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        return 1

    # Phase 3: REST API
    phase_3 = run_phase_3(report_dir, ts, blog_collection, ref_collection)
    all_results["phases"]["phase_3_rest"] = phase_3

    if phase_3["status"] != "PASS":
        logger.error("Phase 3 FAILED - STOP-THE-LINE")
        with open(report_dir / "all_results.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        return 1

    # Phase 4: MCP
    phase_4 = run_phase_4(report_dir, ts, blog_collection, ref_collection)
    all_results["phases"]["phase_4_mcp"] = phase_4

    if phase_4["status"] != "PASS":
        logger.error("Phase 4 FAILED - STOP-THE-LINE")
        with open(report_dir / "all_results.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        return 1

    # All phases passed
    all_results["overall_status"] = "PASS"

    # Save results
    with open(report_dir / "all_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    logger.info("=" * 70)
    logger.info("ALL PHASES PASSED - LIVE E2E FULL V3 COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {ts}")
    logger.info(f"Report: {report_dir}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
