"""REST API Phase Test - Isolated Process

Tests POST /api/jobs with output validation.
"""
import os
import sys
import json
import logging
from pathlib import Path

os.environ["TEST_MODE"] = "live"
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from tools.live_executor_factory import create_live_executor
from src.web.app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MIN_OUTPUT_SIZE = 1536  # 1.5KB minimum (realistic for technical blog posts)

def check_output_size(file_path, min_size=MIN_OUTPUT_SIZE):
    """Verify output file meets minimum size requirement."""
    if not os.path.exists(file_path):
        return False, 0, f"File not found: {file_path}"

    size = os.path.getsize(file_path)
    if size < min_size:
        return False, size, f"Output too small: {size} bytes < {min_size} bytes"

    return True, size, f"Output size OK: {size} bytes >= {min_size} bytes"

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ts", required=True)
    parser.add_argument("--blog-collection", required=True)
    parser.add_argument("--ref-collection", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    results = {"status": "UNKNOWN", "tests": {}}

    try:
        # Create executor and app
        executor = create_live_executor(
            blog_collection=args.blog_collection,
            ref_collection=args.ref_collection
        )
        app = create_app(executor=executor)
        client = TestClient(app)

        # Test: POST /api/jobs (sync mode)
        output_dir = Path(f".live_e2e_data/{args.ts}/rest_output")
        output_dir.mkdir(parents=True, exist_ok=True)

        job_payload = {
            "workflow_id": "default_blog",
            "topic": "Advanced Python Features",
            "output_dir": str(output_dir),
            "blog_collection": args.blog_collection,
            "ref_collection": args.ref_collection,
            "inputs": {}
        }

        logger.info("Testing POST /api/jobs...")
        resp = client.post("/api/jobs", json=job_payload)

        results["tests"]["post_jobs"] = {
            "status_code": resp.status_code,
            "ok": resp.status_code in [200, 201]
        }

        if resp.status_code not in [200, 201]:
            logger.error(f"REST API failed: {resp.status_code} - {resp.text}")
            results["status"] = "FAIL"
            results["error"] = f"HTTP {resp.status_code}"
        else:
            # Validate output
            resp_data = resp.json()
            output_path = resp_data.get("output_path")

            if not output_path:
                logger.error("REST API did not return output_path")
                results["status"] = "FAIL"
                results["error"] = "No output_path in response"
            else:
                valid, size, msg = check_output_size(output_path)
                logger.info(msg)

                if not valid:
                    logger.error(f"FAIL: {msg}")
                    results["status"] = "FAIL"
                    results["error"] = msg
                else:
                    results["tests"]["post_jobs"]["output_size"] = size
                    results["tests"]["post_jobs"]["output_path"] = output_path
                    results["status"] = "PASS"

    except Exception as e:
        logger.error(f"REST API exception: {e}", exc_info=True)
        results["status"] = "FAIL"
        results["error"] = str(e)

    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    return 0 if results["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
