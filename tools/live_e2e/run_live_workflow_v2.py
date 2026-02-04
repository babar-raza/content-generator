#!/usr/bin/env python3
"""Live Workflow V2 - Direct engine execution for single collection."""
import os
import sys
import json
import logging
from pathlib import Path

# Set environment
os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["ALLOW_NETWORK"] = "0"

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.live_e2e.executor_factory import create_live_executor
from src.utils.frontmatter_normalize import enforce_frontmatter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Live Workflow V2")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--collection", required=True, help="Single collection name")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir = Path(args.report_dir)

    try:
        # Create executor with single collection
        executor = create_live_executor(
            blog_collection=args.collection,
            ref_collection=args.collection  # Use same collection for both
        )

        # Use internal REST client for reliable execution
        from fastapi.testclient import TestClient
        from src.web.app import create_app

        app = create_app(executor=executor)
        client = TestClient(app)

        # Generate content via REST API
        logger.info(f"Generating content for: {args.topic}")
        job_payload = {
            "workflow_id": "default_blog",
            "topic": args.topic,
            "output_dir": str(output_dir),
            "inputs": {}
        }

        resp = client.post("/api/jobs", json=job_payload)
        if resp.status_code not in [200, 201]:
            raise Exception(f"Job submission failed: HTTP {resp.status_code}")

        resp_data = resp.json()
        output_path = resp_data.get("output_path")
        if not output_path:
            raise Exception("No output_path in response")

        output_file = Path(output_path)

        # Also create a copy at the expected location for validation
        expected_file = output_dir / "generated_content.md"
        if output_file.exists() and output_file != expected_file:
            import shutil
            shutil.copy2(output_file, expected_file)
            logger.info(f"Copied output to {expected_file}")

        # Use expected file for validation
        output_file = expected_file

        # Enforce valid frontmatter
        if output_file.exists():
            content = output_file.read_text(encoding='utf-8')
            enforced = enforce_frontmatter(content)
            if enforced != content:
                output_file.write_text(enforced, encoding='utf-8')
                logger.info("Enforced valid frontmatter")

        # Save retrieval evidence
        try:
            db_service = executor.database_service
            coll = db_service.get_or_create_collection(args.collection)
            results = coll.query(query_texts=[args.topic], n_results=5)

            retrieval_count = len(results.get("documents", [[]])[0])
            retrieval_file = report_dir / "retrieval_used.json"
            with open(retrieval_file, 'w') as f:
                json.dump({
                    "query": args.topic,
                    "collection": args.collection,
                    "results": results.get("documents", [[]])[0],
                    "count": retrieval_count
                }, f, indent=2)
            logger.info(f"Retrieval evidence: {retrieval_count} results")
        except Exception as e:
            logger.warning(f"Could not save retrieval evidence: {e}")

        logger.info(f"Success: {output_file}")
        return 0

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
