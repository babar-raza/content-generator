"""Simple Live Workflow E2E Test"""
import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"

from tools.live_executor_factory import create_live_executor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(workflow, topic, output_dir, report_dir):
    output_dir = Path(output_dir)
    report_dir = Path(report_dir)
    
    logger.info(f"Running workflow: {workflow}")
    logger.info(f"Topic: {topic}")
    
    executor = create_live_executor()
    llm_service = executor.llm_service
    db_service = executor.database_service
    
    # Query vector store
    logger.info("Querying vector store...")
    collection = db_service.get_or_create_collection("blog_knowledge")
    results = collection.query(query_texts=[topic], n_results=3)
    
    docs = results.get("documents", [[]])[0]
    context = " ".join(docs[:2])[:500] if docs else ""
    
    # Save retrieval evidence
    with open(report_dir / "retrieval_used.json", "w") as f:
        json.dump({"query": topic, "docs": len(docs)}, f, indent=2)
    
    # Generate content
    logger.info("Generating content...")
    prompt = f"Write a 300-word technical blog about: {topic}\n\nContext: {context}\n\nUse markdown with YAML frontmatter and 3 headings."
    
    content = llm_service.generate(prompt, model="phi4-mini:latest", temperature=0.7)
    
    # Save output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "generated_content.md"
    output_file.write_text(content, encoding="utf-8")
    
    logger.info(f"Saved to {output_file}")
    
    # Save trace
    trace = {"workflow": workflow, "topic": topic, "status": "PASS"}
    with open(report_dir / "workflow_trace.json", "w") as f:
        json.dump(trace, f, indent=2)
    
    print(f"[PASS] Output: {output_file}")
    return 0

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--workflow", required=True)
    p.add_argument("--topic", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--report-dir", required=True)
    args = p.parse_args()
    
    try:
        sys.exit(main(args.workflow, args.topic, args.output_dir, args.report_dir))
    except Exception as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
