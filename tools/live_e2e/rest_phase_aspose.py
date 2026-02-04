#!/usr/bin/env python3
"""REST API Phase for Aspose - Single collection."""
import os
import sys
import json
import logging
from pathlib import Path

os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["ALLOW_NETWORK"] = "0"

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from tools.live_e2e.executor_factory import create_live_executor
from src.web.app import create_app
from src.utils.frontmatter_normalize import enforce_frontmatter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--result-file", required=True)
    args = parser.parse_args()

    result = {
        "status": "UNKNOWN",
        "output_path": "",
        "output_size": 0,
        "retrieval_count": 0,
        "error": None
    }

    try:
        executor = create_live_executor(
            blog_collection=args.collection,
            ref_collection=args.collection
        )

        app = create_app(executor=executor)
        client = TestClient(app)

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        job_payload = {
            "workflow_id": "default_blog",
            "topic": args.topic,
            "output_dir": str(output_dir),
            "inputs": {}
        }

        logger.info(f"POST /api/jobs for: {args.topic}")
        resp = client.post("/api/jobs", json=job_payload)

        if resp.status_code not in [200, 201]:
            result["status"] = "FAIL"
            result["error"] = f"HTTP {resp.status_code}"
        else:
            resp_data = resp.json()
            output_path = resp_data.get("output_path")

            if not output_path:
                result["status"] = "FAIL"
                result["error"] = "No output_path"
            else:
                result["output_path"] = output_path
                output_file = Path(output_path)

                if output_file.exists():
                    content = output_file.read_text(encoding='utf-8')
                    enforced = enforce_frontmatter(content)
                    if enforced != content:
                        output_file.write_text(enforced, encoding='utf-8')
                        logger.info("Enforced valid frontmatter")
                    result["output_size"] = len(enforced)

                try:
                    coll = executor.database_service.get_or_create_collection(args.collection)
                    results = coll.query(query_texts=[args.topic], n_results=5)
                    result["retrieval_count"] = len(results.get("documents", [[]])[0])
                except Exception as e:
                    logger.warning(f"Retrieval capture failed: {e}")
                    result["retrieval_count"] = 0

                result["status"] = "PASS"

    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)
        logger.error(f"Exception: {e}", exc_info=True)

    with open(args.result_file, 'w') as f:
        json.dump(result, f, indent=2)

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
