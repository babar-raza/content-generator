#!/usr/bin/env python3
"""Live E2E Ingestion Runner V2 - With per-run collection names.

This script ingests real data into Chroma with custom collection names
to ensure per-run isolation and delta verification.
"""

import os
import sys
import json
import time
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Must set environment variables BEFORE importing anything
os.environ['TEST_MODE'] = 'live'
os.environ['ALLOW_NETWORK'] = '1'
os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434'
os.environ['LLM_PROVIDER'] = 'OLLAMA'
os.environ['OLLAMA_TOPIC_MODEL'] = 'phi4-mini'
os.environ['OLLAMA_CONTENT_MODEL'] = 'phi4-mini'
os.environ['OLLAMA_CODE_MODEL'] = 'phi4-mini'
os.environ['ENABLE_CACHING'] = 'false'
os.environ['LOG_LEVEL'] = 'INFO'

from src.core.config import load_config
from src.services.services import DatabaseService, EmbeddingService


@dataclass
class IngestionStats:
    """Statistics for ingestion run."""
    docs_total: int
    docs_success: int
    docs_failed: int
    chunks_created: int
    vectors_written: int
    collection_name: str
    duration_seconds: float
    errors: List[str]


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - chunk_overlap

    return chunks


def convert_text_to_markdown(text_path: Path, slug: str, description: str) -> str:
    """Load text file and add frontmatter."""
    with open(text_path, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter = f"""---
title: {slug.replace('_', ' ').title()}
description: {description}
source: live_e2e_test
slug: {slug}
---

"""
    return frontmatter + content


def ingest_sources(
    sources: List[Dict[str, Any]],
    collection_name: str,
    database_service: DatabaseService,
    embedding_service: EmbeddingService,
    config,
    repo_root: Path
) -> IngestionStats:
    """Ingest sources into specified collection."""

    start_time = time.time()
    errors = []
    docs_success = 0
    docs_failed = 0
    chunks_created = 0

    print(f"\n{'=' * 80}")
    print(f"INGESTING {len(sources)} SOURCES INTO: {collection_name}")
    print(f"{'=' * 80}")

    all_chunks = []
    all_metadatas = []
    all_ids = []

    for source in sources:
        try:
            slug = source['slug']
            print(f"  Processing: {slug}")

            # Load text and convert to markdown
            text_path = repo_root / source['text_path']
            if not text_path.exists():
                raise FileNotFoundError(f"Text file not found: {text_path}")

            markdown_content = convert_text_to_markdown(text_path, slug, source['description'])

            # Chunk the content
            chunks = chunk_text(
                markdown_content,
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap
            )

            print(f"    Created {len(chunks)} chunks")

            # Create metadata and IDs for each chunk
            for i, chunk in enumerate(chunks):
                chunk_id = f"{slug}_chunk_{i}_{hashlib.md5(chunk.encode()).hexdigest()[:8]}"
                metadata = {
                    "source": slug,
                    "description": source['description'],
                    "url": source['url'],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "ingested_at": datetime.now(timezone.utc).isoformat()
                }

                all_chunks.append(chunk)
                all_metadatas.append(metadata)
                all_ids.append(chunk_id)

            chunks_created += len(chunks)
            docs_success += 1

        except Exception as e:
            error_msg = f"Failed to process {source.get('slug', 'unknown')}: {str(e)}"
            print(f"    ERROR: {error_msg}")
            errors.append(error_msg)
            docs_failed += 1

    # Add all documents to vector store in one batch
    if all_chunks:
        print(f"\nAdding {len(all_chunks)} chunks to collection: {collection_name}")
        try:
            database_service.add_documents(
                documents=all_chunks,
                metadatas=all_metadatas,
                ids=all_ids,
                collection_name=collection_name
            )
            vectors_written = len(all_chunks)
            print(f"  [OK] {vectors_written} vectors written")
        except Exception as e:
            error_msg = f"Failed to write vectors: {str(e)}"
            print(f"  [ERROR] {error_msg}")
            errors.append(error_msg)
            vectors_written = 0
    else:
        vectors_written = 0

    duration = time.time() - start_time

    print(f"\n  Summary:")
    print(f"    Docs processed: {docs_success + docs_failed}")
    print(f"    Success: {docs_success}")
    print(f"    Failed: {docs_failed}")
    print(f"    Chunks created: {chunks_created}")
    print(f"    Vectors written: {vectors_written}")
    print(f"    Duration: {duration:.2f}s")

    return IngestionStats(
        docs_total=len(sources),
        docs_success=docs_success,
        docs_failed=docs_failed,
        chunks_created=chunks_created,
        vectors_written=vectors_written,
        collection_name=collection_name,
        duration_seconds=duration,
        errors=errors
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Live E2E Ingestion with custom collections")
    parser.add_argument("--manifest", required=True, help="Path to dataset_manifest.json")
    parser.add_argument("--blog-collection", required=True, help="Blog collection name")
    parser.add_argument("--ref-collection", required=True, help="Reference collection name")
    parser.add_argument("--output", help="Output JSON file for results")
    parser.add_argument("--log", help="Output log file")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    manifest_path = Path(args.manifest)

    print(f"\nLive E2E Ingestion Runner V2")
    print(f"{'=' * 80}")
    print(f"Manifest: {manifest_path}")
    print(f"Blog collection: {args.blog_collection}")
    print(f"Reference collection: {args.ref_collection}")

    # Load manifest
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"Dataset: {manifest['summary']['kb_count']} KB docs, {manifest['summary']['reference_count']} ref docs")

    # Initialize services
    print("\nInitializing services...")
    try:
        config = load_config()
        database_service = DatabaseService(config)
        embedding_service = EmbeddingService(config)
        print("  [OK] Services initialized")
    except Exception as e:
        print(f"  [ERROR] Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Separate sources by type
    kb_sources = [s for s in manifest['sources'] if s['source_type'] == 'kb' and s['fetch_success']]
    ref_sources = [s for s in manifest['sources'] if s['source_type'] == 'reference' and s['fetch_success']]

    # Ingest KB sources
    kb_stats = ingest_sources(
        kb_sources,
        args.blog_collection,
        database_service,
        embedding_service,
        config,
        repo_root
    )

    # Ingest reference sources
    ref_stats = ingest_sources(
        ref_sources,
        args.ref_collection,
        database_service,
        embedding_service,
        config,
        repo_root
    )

    # Create results
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "kb_ingestion": asdict(kb_stats),
        "ref_ingestion": asdict(ref_stats),
        "total_docs": kb_stats.docs_total + ref_stats.docs_total,
        "total_success": kb_stats.docs_success + ref_stats.docs_success,
        "total_failed": kb_stats.docs_failed + ref_stats.docs_failed,
        "total_chunks": kb_stats.chunks_created + ref_stats.chunks_created,
        "total_vectors": kb_stats.vectors_written + ref_stats.vectors_written,
        "status": "PASS" if (kb_stats.docs_failed == 0 and ref_stats.docs_failed == 0) else "FAIL"
    }

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n[OK] Results written to: {output_path}")

    # Final summary
    print(f"\n{'=' * 80}")
    print(f"FINAL SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total docs: {results['total_docs']}")
    print(f"Success: {results['total_success']}")
    print(f"Failed: {results['total_failed']}")
    print(f"Total chunks: {results['total_chunks']}")
    print(f"Total vectors: {results['total_vectors']}")
    print(f"Status: {results['status']}")

    sys.exit(0 if results['status'] == 'PASS' else 1)


if __name__ == "__main__":
    main()
