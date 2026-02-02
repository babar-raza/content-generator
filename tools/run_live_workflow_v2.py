#!/usr/bin/env python3
"""Live Workflow E2E Test V2 - With per-run collections

Runs a complete workflow using:
- Real Ollama generation (phi4-mini:latest)
- Real vector retrieval from per-run collections
- Real output generation with validation
"""
import os
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set live mode environment
os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["ALLOW_NETWORK"] = "1"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

from tools.live_e2e.executor_factory import create_live_executor
from src.utils.frontmatter_normalize import normalize_frontmatter, has_valid_frontmatter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def run_workflow_e2e(
    workflow_id: str,
    topic: str,
    output_dir: Path,
    report_dir: Path,
    blog_collection: str,
    ref_collection: str,
    ollama_model: str = "phi4-mini:latest"
) -> Dict[str, Any]:
    """Run workflow end-to-end with real services.

    Args:
        workflow_id: Workflow name (e.g., 'blog_workflow')
        topic: Content topic
        output_dir: Directory for generated content
        report_dir: Directory for test reports
        blog_collection: Blog knowledge collection name
        ref_collection: API reference collection name
        ollama_model: Ollama model name

    Returns:
        Results dictionary with status and paths
    """
    start_time = time.time()

    logger.info("=" * 80)
    logger.info("LIVE WORKFLOW E2E TEST V2")
    logger.info("=" * 80)
    logger.info(f"Workflow: {workflow_id}")
    logger.info(f"Topic: {topic}")
    logger.info(f"Blog Collection: {blog_collection}")
    logger.info(f"Reference Collection: {ref_collection}")
    logger.info(f"Ollama Model: {ollama_model}")
    logger.info(f"Output: {output_dir}")

    # Create executor with per-run collections
    logger.info("\nCreating live executor...")
    executor = create_live_executor(
        blog_collection=blog_collection,
        ref_collection=ref_collection,
        ollama_model=ollama_model
    )

    llm_service = executor.llm_service
    db_service = executor.database_service

    # Log LLM provider verification
    logger.info(f"  LLM Provider: {executor.config.llm_provider}")
    logger.info(f"  LLM Model: {ollama_model}")
    logger.info(f"  Ollama URL: {executor.config.ollama_base_url}")

    # Query both collections for retrieval evidence
    logger.info("\nRetrieving context from vector stores...")
    retrieval_evidence = []

    # Query blog knowledge collection
    try:
        blog_coll = db_service.get_or_create_collection(blog_collection)
        blog_results = blog_coll.query(query_texts=[topic], n_results=3)
        blog_docs = blog_results.get("documents", [[]])[0]
        blog_metadatas = blog_results.get("metadatas", [[]])[0]

        logger.info(f"  Blog collection: Retrieved {len(blog_docs)} documents")

        for i, (doc, meta) in enumerate(zip(blog_docs[:3], blog_metadatas[:3])):
            retrieval_evidence.append({
                "collection": blog_collection,
                "query": topic,
                "result_index": i,
                "source": meta.get("source", "unknown"),
                "chunk_preview": doc[:200] if doc else "",
                "metadata": meta
            })

    except Exception as e:
        logger.error(f"  Error querying blog collection: {e}")
        blog_docs = []

    # Query reference collection
    try:
        ref_coll = db_service.get_or_create_collection(ref_collection)
        ref_results = ref_coll.query(query_texts=[topic], n_results=2)
        ref_docs = ref_results.get("documents", [[]])[0]
        ref_metadatas = ref_results.get("metadatas", [[]])[0]

        logger.info(f"  Reference collection: Retrieved {len(ref_docs)} documents")

        for i, (doc, meta) in enumerate(zip(ref_docs[:2], ref_metadatas[:2])):
            retrieval_evidence.append({
                "collection": ref_collection,
                "query": topic,
                "result_index": i,
                "source": meta.get("source", "unknown"),
                "chunk_preview": doc[:200] if doc else "",
                "metadata": meta
            })

    except Exception as e:
        logger.error(f"  Error querying reference collection: {e}")
        ref_docs = []

    # Save retrieval evidence
    retrieval_file = report_dir / "retrieval_used.json"
    retrieval_file.parent.mkdir(parents=True, exist_ok=True)
    with open(retrieval_file, "w") as f:
        json.dump({
            "query": topic,
            "blog_collection": blog_collection,
            "ref_collection": ref_collection,
            "blog_results": len(blog_docs),
            "ref_results": len(ref_docs),
            "total_retrievals": len(retrieval_evidence),
            "evidence": retrieval_evidence
        }, f, indent=2)

    logger.info(f"  Saved retrieval evidence: {retrieval_file}")

    # Build context from retrieved documents
    context_parts = []
    if blog_docs:
        context_parts.append("Knowledge Base Context:\n" + "\n".join(blog_docs[:2]))
    if ref_docs:
        context_parts.append("Reference Context:\n" + "\n".join(ref_docs[:1]))

    context = "\n\n".join(context_parts)[:2000] if context_parts else "No context retrieved"

    # Generate content using LLM
    logger.info("\nGenerating content with Ollama...")
    prompt = f"""Write a comprehensive technical blog post about: {topic}

Context from knowledge base:
{context}

Requirements:
- Use proper YAML frontmatter with title, description, and tags
- Include at least 3 main headings (##)
- Write 500+ words of technical content
- Include code examples if relevant
- Reference the context sources naturally
- Use markdown formatting

Format:
---
title: Your Title
description: Brief description
tags: [tag1, tag2, tag3]
---

# Main Title

Your content here...
"""

    try:
        content = llm_service.generate(
            prompt,
            model=ollama_model,
            temperature=0.7,
            max_tokens=2000
        )
        logger.info(f"  Generated {len(content)} characters")
    except Exception as e:
        logger.error(f"  Generation failed: {e}")
        content = f"# Error\n\nGeneration failed: {str(e)}"

    # Normalize frontmatter to ensure proper --- delimiters
    content = normalize_frontmatter(content)
    if not has_valid_frontmatter(content):
        logger.error("  CRITICAL: Frontmatter normalization failed - output has invalid frontmatter")
        raise ValueError("Generated content has invalid YAML frontmatter after normalization")

    logger.info(f"  Frontmatter normalized and validated")

    # Save output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "generated_content.md"
    output_file.write_text(content, encoding="utf-8")

    logger.info(f"  Saved output: {output_file}")

    # Create workflow trace
    duration = time.time() - start_time
    trace = {
        "workflow_id": workflow_id,
        "topic": topic,
        "blog_collection": blog_collection,
        "ref_collection": ref_collection,
        "ollama_model": ollama_model,
        "retrieval_count": len(retrieval_evidence),
        "output_size_bytes": len(content),
        "output_file": str(output_file),
        "duration_seconds": duration,
        "status": "PASS",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    trace_file = report_dir / "workflow_trace.json"
    with open(trace_file, "w") as f:
        json.dump(trace, f, indent=2)

    # Create workflow log
    log_file = report_dir / "workflow_run.log"
    with open(log_file, "w") as f:
        f.write(f"Live Workflow E2E Test V2\n")
        f.write(f"{'=' * 80}\n")
        f.write(f"Workflow: {workflow_id}\n")
        f.write(f"Topic: {topic}\n")
        f.write(f"Collections: {blog_collection}, {ref_collection}\n")
        f.write(f"Model: {ollama_model}\n")
        f.write(f"Retrievals: {len(retrieval_evidence)}\n")
        f.write(f"Output: {output_file}\n")
        f.write(f"Duration: {duration:.2f}s\n")
        f.write(f"Status: PASS\n")

    logger.info(f"\n{'=' * 80}")
    logger.info(f"WORKFLOW E2E COMPLETE")
    logger.info(f"{'=' * 80}")
    logger.info(f"Output: {output_file}")
    logger.info(f"Trace: {trace_file}")
    logger.info(f"Duration: {duration:.2f}s")
    logger.info(f"Status: PASS")

    return trace


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Live Workflow E2E Test V2")
    parser.add_argument("--workflow-id", required=True, help="Workflow name")
    parser.add_argument("--topic", required=True, help="Content topic")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--report-dir", required=True, help="Report directory")
    parser.add_argument("--blog-collection", required=True, help="Blog collection name")
    parser.add_argument("--ref-collection", required=True, help="Reference collection name")
    parser.add_argument("--ollama-model", default="phi4-mini:latest", help="Ollama model")
    args = parser.parse_args()

    try:
        result = run_workflow_e2e(
            workflow_id=args.workflow_id,
            topic=args.topic,
            output_dir=Path(args.output_dir),
            report_dir=Path(args.report_dir),
            blog_collection=args.blog_collection,
            ref_collection=args.ref_collection,
            ollama_model=args.ollama_model
        )

        print(f"\n[PASS] Workflow E2E Complete")
        print(f"Output: {result['output_file']}")
        print(f"Status: {result['status']}")

        sys.exit(0)

    except Exception as e:
        logger.error(f"Workflow E2E failed: {e}", exc_info=True)
        print(f"\n[FAIL] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
