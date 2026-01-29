"""MCP Phase Test - Isolated Process

Tests MCP workflow.execute (single + batch) with output validation.
"""
import os
import sys
import json
import logging
from pathlib import Path

os.environ["TEST_MODE"] = "live"
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from tools.live_e2e.executor_factory import create_live_executor
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

        # Test 1: Single workflow.execute
        output_dir_single = Path(f".live_e2e_data/{args.ts}/mcp_single_output")
        output_dir_single.mkdir(parents=True, exist_ok=True)

        mcp_req_single = {
            "jsonrpc": "2.0",
            "method": "workflow.execute",
            "params": {
                "workflow_id": "default_blog",
                "topic": "Machine Learning Best Practices",
                "output_dir": str(output_dir_single),
                "blog_collection": args.blog_collection,
                "ref_collection": args.ref_collection
            },
            "id": 1
        }

        logger.info("Testing MCP workflow.execute (single)...")
        resp = client.post("/mcp/request", json=mcp_req_single)

        results["tests"]["mcp_single"] = {
            "status_code": resp.status_code,
            "ok": resp.status_code == 200
        }

        if resp.status_code != 200:
            logger.error(f"MCP single failed: {resp.status_code} - {resp.text}")
            results["status"] = "FAIL"
            results["error"] = f"MCP single HTTP {resp.status_code}"
        else:
            resp_data = resp.json()
            # MCP JSON-RPC response format: {"jsonrpc": "2.0", "result": {...}, "id": 1}
            # or direct response: {"job_id": ..., "output_path": ...}
            if "error" in resp_data and resp_data["error"] is not None:
                logger.error(f"MCP single returned error: {resp_data['error']}")
                results["status"] = "FAIL"
                results["error"] = resp_data["error"]
            else:
                # Try both formats: JSON-RPC wrapped or direct
                if "result" in resp_data:
                    output_path = resp_data["result"].get("output_path")
                else:
                    output_path = resp_data.get("output_path")
                if not output_path:
                    logger.error("MCP single did not return output_path")
                    results["status"] = "FAIL"
                    results["error"] = "No output_path in MCP single response"
                else:
                    valid, size, msg = check_output_size(output_path)
                    logger.info(f"MCP single: {msg}")

                    if not valid:
                        logger.error(f"FAIL: {msg}")
                        results["status"] = "FAIL"
                        results["error"] = msg
                    else:
                        results["tests"]["mcp_single"]["output_size"] = size
                        results["tests"]["mcp_single"]["output_path"] = output_path

                        # Test 2: Batch workflow.execute
                        output_dir_batch_1 = Path(f".live_e2e_data/{args.ts}/mcp_batch_output_1")
                        output_dir_batch_2 = Path(f".live_e2e_data/{args.ts}/mcp_batch_output_2")
                        output_dir_batch_1.mkdir(parents=True, exist_ok=True)
                        output_dir_batch_2.mkdir(parents=True, exist_ok=True)

                        mcp_batch = [
                            {
                                "jsonrpc": "2.0",
                                "method": "workflow.execute",
                                "params": {
                                    "workflow_id": "default_blog",
                                    "topic": "Web Development Patterns",
                                    "output_dir": str(output_dir_batch_1),
                                    "blog_collection": args.blog_collection,
                                    "ref_collection": args.ref_collection
                                },
                                "id": 2
                            },
                            {
                                "jsonrpc": "2.0",
                                "method": "workflow.execute",
                                "params": {
                                    "workflow_id": "default_blog",
                                    "topic": "Database Design Principles",
                                    "output_dir": str(output_dir_batch_2),
                                    "blog_collection": args.blog_collection,
                                    "ref_collection": args.ref_collection
                                },
                                "id": 3
                            }
                        ]

                        logger.info("Testing MCP workflow.execute (batch)...")
                        resp = client.post("/mcp/request", json=mcp_batch)

                        results["tests"]["mcp_batch"] = {
                            "status_code": resp.status_code,
                            "ok": resp.status_code == 200
                        }

                        if resp.status_code != 200:
                            logger.error(f"MCP batch failed: {resp.status_code} - {resp.text}")
                            results["status"] = "FAIL"
                            results["error"] = f"MCP batch HTTP {resp.status_code}"
                        else:
                            batch_responses = resp.json()
                            if not isinstance(batch_responses, list) or len(batch_responses) != 2:
                                logger.error(f"MCP batch did not return 2 responses: {batch_responses}")
                                results["status"] = "FAIL"
                                results["error"] = "Invalid batch response format"
                            else:
                                # Validate both batch outputs
                                batch_outputs = []
                                batch_ok = True
                                for i, batch_resp in enumerate(batch_responses):
                                    if "error" in batch_resp and batch_resp["error"] is not None:
                                        logger.error(f"MCP batch[{i}] returned error: {batch_resp['error']}")
                                        results["status"] = "FAIL"
                                        results["error"] = f"Batch[{i}] error: {batch_resp['error']}"
                                        batch_ok = False
                                        break

                                    # Try both formats: JSON-RPC wrapped or direct
                                    if "result" in batch_resp:
                                        output_path = batch_resp["result"].get("output_path")
                                    else:
                                        output_path = batch_resp.get("output_path")
                                    if not output_path:
                                        logger.error(f"MCP batch[{i}] did not return output_path")
                                        results["status"] = "FAIL"
                                        results["error"] = f"No output_path in batch[{i}]"
                                        batch_ok = False
                                        break

                                    valid, size, msg = check_output_size(output_path)
                                    logger.info(f"MCP batch[{i}]: {msg}")

                                    if not valid:
                                        logger.error(f"FAIL: {msg}")
                                        results["status"] = "FAIL"
                                        results["error"] = msg
                                        batch_ok = False
                                        break

                                    batch_outputs.append({"output_path": output_path, "output_size": size})

                                if batch_ok:
                                    results["tests"]["mcp_batch"]["outputs"] = batch_outputs
                                    results["status"] = "PASS"

    except Exception as e:
        logger.error(f"MCP exception: {e}", exc_info=True)
        results["status"] = "FAIL"
        results["error"] = str(e)

    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    return 0 if results["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
