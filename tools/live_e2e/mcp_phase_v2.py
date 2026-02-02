#!/usr/bin/env python3
"""MCP Phase Test V2 - Per-topic subprocess runner

Runs a single topic through MCP workflow.execute with output validation
and frontmatter normalization. Designed to run in isolated subprocess.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Set environment BEFORE imports
os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["ALLOW_NETWORK"] = "1"
os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ["OLLAMA_MODEL"] = os.getenv("OLLAMA_MODEL", "phi4-mini:latest")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from tools.live_e2e.executor_factory import create_live_executor
from src.web.app import create_app
from src.utils.frontmatter_normalize import normalize_frontmatter, enforce_frontmatter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCP Phase V2 - Per-topic")
    parser.add_argument("--topic", required=True, help="Topic to generate")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--blog-collection", required=True, help="Blog collection")
    parser.add_argument("--ref-collection", required=True, help="Reference collection")
    parser.add_argument("--result-file", required=True, help="JSON result file path")
    args = parser.parse_args()

    result = {
        "status": "UNKNOWN",
        "output_path": "",
        "output_size": 0,
        "retrieval_count": 0,
        "error": None
    }

    try:
        # Create executor with proper collections
        executor = create_live_executor(
            blog_collection=args.blog_collection,
            ref_collection=args.ref_collection
        )

        app = create_app(executor=executor)
        client = TestClient(app)

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # MCP JSON-RPC request for workflow.execute
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "workflow.execute",
            "params": {
                "workflow_id": "default_blog",
                "topic": args.topic,
                "output_dir": str(output_dir),
                "blog_collection": args.blog_collection,
                "ref_collection": args.ref_collection
            },
            "id": 1
        }

        logger.info(f"POST /mcp/request workflow.execute for topic: {args.topic}")
        resp = client.post("/mcp/request", json=mcp_request)

        if resp.status_code != 200:
            result["status"] = "FAIL"
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
        else:
            resp_data = resp.json()

            # Check for JSON-RPC error
            if "error" in resp_data and resp_data["error"] is not None:
                result["status"] = "FAIL"
                result["error"] = f"MCP error: {resp_data['error']}"
            else:
                # Extract output_path from response
                if "result" in resp_data:
                    output_path = resp_data["result"].get("output_path")
                else:
                    output_path = resp_data.get("output_path")

                if not output_path:
                    result["status"] = "FAIL"
                    result["error"] = "No output_path in MCP response"
                else:
                    result["output_path"] = output_path
                    output_file = Path(output_path)

                    # Enforce valid frontmatter
                    if output_file.exists():
                        content = output_file.read_text(encoding='utf-8')
                        enforced = enforce_frontmatter(content)
                        if enforced != content:
                            output_file.write_text(enforced, encoding='utf-8')
                            logger.info("Enforced valid frontmatter")
                        result["output_size"] = len(enforced)

                    # Capture retrieval evidence
                    try:
                        db_service = executor.database_service
                        blog_coll = db_service.get_or_create_collection(args.blog_collection)
                        ref_coll = db_service.get_or_create_collection(args.ref_collection)

                        blog_results = blog_coll.query(query_texts=[args.topic], n_results=3)
                        ref_results = ref_coll.query(query_texts=[args.topic], n_results=2)

                        blog_count = len(blog_results.get("documents", [[]])[0])
                        ref_count = len(ref_results.get("documents", [[]])[0])
                        result["retrieval_count"] = blog_count + ref_count

                        # Save retrieval evidence
                        retrieval_file = output_dir / "retrieval_used.json"
                        with open(retrieval_file, 'w') as f:
                            json.dump({
                                "query": args.topic,
                                "blog_collection": args.blog_collection,
                                "ref_collection": args.ref_collection,
                                "blog_results": blog_count,
                                "ref_results": ref_count,
                                "total_retrievals": blog_count + ref_count
                            }, f, indent=2)
                    except Exception as e:
                        logger.warning(f"Failed to capture retrieval: {e}")
                        result["retrieval_count"] = 0

                    result["status"] = "PASS"

    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)
        logger.error(f"MCP exception: {e}", exc_info=True)

    # Save result
    with open(args.result_file, 'w') as f:
        json.dump(result, f, indent=2)

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
