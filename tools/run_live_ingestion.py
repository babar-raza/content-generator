#!/usr/bin/env python3
"""Live E2E Ingestion Runner - Ingest real data into Chroma using real agents.

This script:
1. Loads dataset_manifest.json
2. Converts extracted text files to markdown
3. Ingests KB sources using KBIngestionAgent
4. Ingests reference sources using APIIngestionAgent/DocsIngestionAgent
5. Records statistics and results
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Must set environment variables BEFORE importing anything
os.environ['TEST_MODE'] = 'live'
os.environ['ALLOW_NETWORK'] = '1'
os.environ['CHROMA_HOST'] = 'localhost'
os.environ['CHROMA_PORT'] = '9100'
os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434'
os.environ['LLM_PROVIDER'] = 'ollama'

# Override Ollama models to use fast ones
os.environ['OLLAMA_TOPIC_MODEL'] = 'phi4-mini'
os.environ['OLLAMA_CONTENT_MODEL'] = 'phi4-mini'
os.environ['OLLAMA_CODE_MODEL'] = 'phi4-mini'

from src.core.config import load_config
from src.core.event_bus import EventBus
from src.services.services import (
    LLMService, DatabaseService, EmbeddingService, GistService, LinkChecker, TrendsService
)
from src.agents.ingestion.kb_ingestion import KBIngestionAgent
from src.agents.ingestion.api_ingestion import APIIngestionAgent


@dataclass
class IngestionResult:
    """Result of ingesting sources."""
    source_type: str  # 'kb' or 'reference'
    docs_processed: int
    docs_success: int
    docs_failed: int
    chunks_created: int
    vectors_written: int
    collection_name: str
    errors: List[str]
    duration_seconds: float


def setup_environment():
    """Set up environment variables for live mode."""
    env_vars = {
        'TEST_MODE': 'live',
        'ALLOW_NETWORK': '1',
        'CHROMA_HOST': 'localhost',
        'CHROMA_PORT': '9100',
        'OLLAMA_BASE_URL': 'http://localhost:11434',
        'LLM_PROVIDER': 'ollama',
        'OLLAMA_TOPIC_MODEL': 'phi4-mini',
        'OLLAMA_CONTENT_MODEL': 'phi4-mini',
        'OLLAMA_CODE_MODEL': 'phi4-mini',
        'ENABLE_CACHING': 'false',  # Disable caching for true live testing
        'LOG_LEVEL': 'INFO'
    }

    for key, value in env_vars.items():
        os.environ[key] = value

    print("Environment configured for live mode:")
    for key, value in env_vars.items():
        if 'KEY' not in key and 'TOKEN' not in key:
            print(f"  {key}={value}")


def convert_text_to_markdown(text_path: Path, md_path: Path, slug: str, description: str):
    """Convert extracted text to markdown with metadata."""
    with open(text_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add frontmatter
    frontmatter = f"""---
title: {slug.replace('_', ' ').title()}
description: {description}
source: live_e2e_test
slug: {slug}
---

"""

    md_content = frontmatter + content

    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)


def ingest_kb_sources(
    manifest: Dict[str, Any],
    timestamp: str,
    repo_root: Path,
    config,
    event_bus: EventBus,
    database_service: DatabaseService,
    embedding_service: EmbeddingService
) -> IngestionResult:
    """Ingest KB sources."""
    print("\n" + "=" * 80)
    print("INGESTING KB SOURCES")
    print("=" * 80)

    start_time = time.time()
    errors = []

    # Prepare markdown files from extracted text
    kb_md_dir = repo_root / ".live_e2e_data" / timestamp / "kb_markdown"
    kb_md_dir.mkdir(parents=True, exist_ok=True)

    kb_sources = [s for s in manifest['sources'] if s['source_type'] == 'kb' and s['fetch_success']]
    print(f"Converting {len(kb_sources)} KB sources to markdown...")

    for source in kb_sources:
        text_path = repo_root / source['text_path']
        md_path = kb_md_dir / f"{source['slug']}.md"
        convert_text_to_markdown(text_path, md_path, source['slug'], source['description'])
        print(f"  Converted: {source['slug']}")

    # Create and execute KB ingestion agent
    print(f"\nIngesting KB articles from: {kb_md_dir}")
    agent = KBIngestionAgent(config, event_bus, database_service, embedding_service)

    from src.core.event_bus import AgentEvent

    try:
        event = AgentEvent(
            event_type="execute_ingest_kb",
            data={"kb_path": str(kb_md_dir)},
            source_agent="live_e2e_runner",
            correlation_id="live_e2e_kb_ingest"
        )
        result_event = agent.execute(event)

        if result_event:
            docs_processed = len(kb_sources)
            # Try to get stats from database
            try:
                collection = database_service.get_collection("blog_knowledge")
                vectors_count = collection.count() if collection else 0
            except Exception as e:
                print(f"  Warning: Could not get vector count: {e}")
                vectors_count = 0

            duration = time.time() - start_time

            print(f"\n  [OK] KB Ingestion Complete")
            print(f"    Documents processed: {docs_processed}")
            print(f"    Vectors written: {vectors_count}")
            print(f"    Duration: {duration:.2f}s")

            return IngestionResult(
                source_type='kb',
                docs_processed=docs_processed,
                docs_success=docs_processed,
                docs_failed=0,
                chunks_created=vectors_count,
                vectors_written=vectors_count,
                collection_name='blog_knowledge',
                errors=[],
                duration_seconds=duration
            )
        else:
            raise ValueError("Agent returned None")

    except Exception as e:
        error_msg = f"KB ingestion failed: {str(e)}"
        print(f"  [ERROR] {error_msg}")
        errors.append(error_msg)

        duration = time.time() - start_time
        return IngestionResult(
            source_type='kb',
            docs_processed=len(kb_sources),
            docs_success=0,
            docs_failed=len(kb_sources),
            chunks_created=0,
            vectors_written=0,
            collection_name='blog_knowledge',
            errors=errors,
            duration_seconds=duration
        )


def ingest_reference_sources(
    manifest: Dict[str, Any],
    timestamp: str,
    repo_root: Path,
    config,
    event_bus: EventBus,
    database_service: DatabaseService,
    embedding_service: EmbeddingService
) -> IngestionResult:
    """Ingest reference sources."""
    print("\n" + "=" * 80)
    print("INGESTING REFERENCE SOURCES")
    print("=" * 80)

    start_time = time.time()
    errors = []

    # Prepare markdown files from extracted text
    ref_md_dir = repo_root / ".live_e2e_data" / timestamp / "reference_markdown"
    ref_md_dir.mkdir(parents=True, exist_ok=True)

    ref_sources = [s for s in manifest['sources'] if s['source_type'] == 'reference' and s['fetch_success']]
    print(f"Converting {len(ref_sources)} reference sources to markdown...")

    for source in ref_sources:
        text_path = repo_root / source['text_path']
        md_path = ref_md_dir / f"{source['slug']}.md"
        convert_text_to_markdown(text_path, md_path, source['slug'], source['description'])
        print(f"  Converted: {source['slug']}")

    # Update config to point to reference markdown directory
    config.api_dir = ref_md_dir

    # Create and execute API ingestion agent
    print(f"\nIngesting API reference from: {ref_md_dir}")
    agent = APIIngestionAgent(config, event_bus, database_service)

    from src.core.event_bus import AgentEvent

    try:
        event = AgentEvent(
            event_type="execute_ingest_api",
            data={"api_path": str(ref_md_dir)},
            source_agent="live_e2e_runner",
            correlation_id="live_e2e_ref_ingest"
        )
        result_event = agent.execute(event)

        if result_event:
            docs_processed = len(ref_sources)
            # Try to get stats from database
            try:
                collection = database_service.get_collection("api_reference")
                vectors_count = collection.count() if collection else 0
            except Exception as e:
                print(f"  Warning: Could not get vector count: {e}")
                vectors_count = 0

            duration = time.time() - start_time

            print(f"\n  [OK] Reference Ingestion Complete")
            print(f"    Documents processed: {docs_processed}")
            print(f"    Vectors written: {vectors_count}")
            print(f"    Duration: {duration:.2f}s")

            return IngestionResult(
                source_type='reference',
                docs_processed=docs_processed,
                docs_success=docs_processed,
                docs_failed=0,
                chunks_created=vectors_count,
                vectors_written=vectors_count,
                collection_name='api_reference',
                errors=[],
                duration_seconds=duration
            )
        else:
            raise ValueError("Agent returned None")

    except Exception as e:
        error_msg = f"Reference ingestion failed: {str(e)}"
        print(f"  [ERROR] {error_msg}")
        errors.append(error_msg)

        duration = time.time() - start_time
        return IngestionResult(
            source_type='reference',
            docs_processed=len(ref_sources),
            docs_success=0,
            docs_failed=len(ref_sources),
            chunks_created=0,
            vectors_written=0,
            collection_name='api_reference',
            errors=errors,
            duration_seconds=duration
        )


def main():
    """Main entry point."""
    setup_environment()

    timestamp = os.environ.get('LIVE_E2E_TIMESTAMP', '20260127-1926')
    repo_root = Path(__file__).parent.parent
    report_base = os.environ.get('LIVE_E2E_REPORT_DIR', 'live_e2e_ollama_fix')
    manifest_path = repo_root / "reports" / report_base / timestamp / "dataset_manifest.json"
    output_dir = repo_root / "reports" / report_base / timestamp

    print(f"\nLive E2E Ingestion Runner")
    print(f"=" * 80)
    print(f"Timestamp: {timestamp}")
    print(f"Manifest: {manifest_path}")
    print()

    # Load manifest
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        print("Please run tools/fetch_live_e2e_data.py first")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"Dataset: {manifest['summary']['kb_count']} KB docs, {manifest['summary']['reference_count']} ref docs")

    # Initialize services
    print("\nInitializing services...")
    try:
        config = load_config()
        event_bus = EventBus()
        llm_service = LLMService(config)
        database_service = DatabaseService(config)
        embedding_service = EmbeddingService(config)
        gist_service = GistService(config)
        link_checker = LinkChecker(config)
        trends_service = TrendsService(config)
        print("  [OK] Services initialized")
    except Exception as e:
        print(f"  [ERROR] Service initialization failed: {e}")
        sys.exit(1)

    # Ingest KB sources
    kb_result = ingest_kb_sources(
        manifest, timestamp, repo_root, config, event_bus, database_service, embedding_service
    )

    # Ingest reference sources
    ref_result = ingest_reference_sources(
        manifest, timestamp, repo_root, config, event_bus, database_service, embedding_service
    )

    # Save results
    results = {
        'timestamp': timestamp,
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'kb_ingestion': asdict(kb_result),
        'reference_ingestion': asdict(ref_result),
        'summary': {
            'total_docs_processed': kb_result.docs_processed + ref_result.docs_processed,
            'total_vectors_written': kb_result.vectors_written + ref_result.vectors_written,
            'total_duration_seconds': kb_result.duration_seconds + ref_result.duration_seconds,
            'kb_success': kb_result.docs_failed == 0,
            'reference_success': ref_result.docs_failed == 0,
            'overall_success': kb_result.docs_failed == 0 and ref_result.docs_failed == 0
        }
    }

    results_path = output_dir / "ingestion_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Save log
    log_path = output_dir / "ingestion_log.txt"
    with open(log_path, 'w') as f:
        f.write(f"Live E2E Ingestion Log\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Completed: {results['completed_at_utc']}\n\n")
        f.write(f"KB Ingestion:\n")
        f.write(f"  Docs: {kb_result.docs_processed}\n")
        f.write(f"  Success: {kb_result.docs_success}\n")
        f.write(f"  Failed: {kb_result.docs_failed}\n")
        f.write(f"  Vectors: {kb_result.vectors_written}\n")
        f.write(f"  Duration: {kb_result.duration_seconds:.2f}s\n")
        if kb_result.errors:
            f.write(f"  Errors: {', '.join(kb_result.errors)}\n")
        f.write(f"\nReference Ingestion:\n")
        f.write(f"  Docs: {ref_result.docs_processed}\n")
        f.write(f"  Success: {ref_result.docs_success}\n")
        f.write(f"  Failed: {ref_result.docs_failed}\n")
        f.write(f"  Vectors: {ref_result.vectors_written}\n")
        f.write(f"  Duration: {ref_result.duration_seconds:.2f}s\n")
        if ref_result.errors:
            f.write(f"  Errors: {', '.join(ref_result.errors)}\n")

    print("\n" + "=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)
    print(f"Total docs processed: {results['summary']['total_docs_processed']}")
    print(f"Total vectors written: {results['summary']['total_vectors_written']}")
    print(f"Total duration: {results['summary']['total_duration_seconds']:.2f}s")
    print(f"Overall success: {results['summary']['overall_success']}")
    print(f"\nResults: {results_path}")
    print(f"Log: {log_path}")

    sys.exit(0 if results['summary']['overall_success'] else 1)


if __name__ == '__main__':
    main()
