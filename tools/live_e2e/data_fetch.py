#!/usr/bin/env python3
"""Fetch and process real data sources for Live E2E testing.

This script:
1. Reads config/live_e2e_sources.yaml
2. Fetches HTML from each URL
3. Extracts readable text content
4. Computes SHA256 hashes
5. Creates a manifest JSON for reproducibility
"""

import os
import sys
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error
from html.parser import HTMLParser
import yaml


@dataclass
class SourceFetch:
    """Result of fetching a single source."""
    url: str
    slug: str
    description: str
    source_type: str  # 'kb' or 'reference'
    fetched_at_utc: str
    fetch_success: bool
    error_message: Optional[str]
    html_path: Optional[str]
    html_size_bytes: int
    html_sha256: Optional[str]
    text_path: Optional[str]
    text_size_bytes: int
    text_sha256: Optional[str]
    truncated: bool


class HTMLTextExtractor(HTMLParser):
    """Extract readable text from HTML, filtering out scripts and styles."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'head', 'noscript'}
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag

    def handle_endtag(self, tag):
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self) -> str:
        return '\n'.join(self.text_parts)


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def fetch_url(url: str, timeout: int = 30) -> tuple[bool, Optional[bytes], Optional[str]]:
    """Fetch URL with timeout.

    Returns:
        (success, content_bytes, error_message)
    """
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Live E2E Testing)'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read()
            return True, content, None
    except urllib.error.HTTPError as e:
        return False, None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, None, f"URL Error: {e.reason}"
    except Exception as e:
        return False, None, f"Error: {str(e)}"


def extract_text_from_html(html_bytes: bytes) -> str:
    """Extract readable text from HTML."""
    try:
        html_str = html_bytes.decode('utf-8', errors='ignore')
        parser = HTMLTextExtractor()
        parser.feed(html_str)
        return parser.get_text()
    except Exception as e:
        return f"[Text extraction failed: {e}]"


def truncate_if_needed(content: bytes, max_size: int) -> tuple[bytes, bool]:
    """Truncate content if it exceeds max_size.

    Returns:
        (content, was_truncated)
    """
    if len(content) <= max_size:
        return content, False
    return content[:max_size], True


def fetch_source(
    source: Dict[str, str],
    source_type: str,
    output_dir: Path,
    max_html_size: int,
    max_text_size: int
) -> SourceFetch:
    """Fetch and process a single source."""
    url = source['url']
    slug = source['slug']
    description = source.get('description', '')

    print(f"  Fetching: {slug} ({url})")

    # Fetch HTML
    success, html_bytes, error = fetch_url(url)
    fetched_at = datetime.now(timezone.utc).isoformat()

    if not success:
        print(f"    ERROR: {error}")
        return SourceFetch(
            url=url,
            slug=slug,
            description=description,
            source_type=source_type,
            fetched_at_utc=fetched_at,
            fetch_success=False,
            error_message=error,
            html_path=None,
            html_size_bytes=0,
            html_sha256=None,
            text_path=None,
            text_size_bytes=0,
            text_sha256=None,
            truncated=False
        )

    # Truncate HTML if needed
    html_bytes, html_truncated = truncate_if_needed(html_bytes, max_html_size)

    # Save HTML
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    html_path = raw_dir / f"{slug}.html"
    html_path.write_bytes(html_bytes)
    html_sha256 = compute_sha256(html_bytes)

    # Extract text
    text = extract_text_from_html(html_bytes)
    text_bytes = text.encode('utf-8')

    # Truncate text if needed
    text_bytes, text_truncated = truncate_if_needed(text_bytes, max_text_size)
    truncated = html_truncated or text_truncated

    # Save text
    extracted_dir = output_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    text_path = extracted_dir / f"{slug}.txt"
    text_path.write_bytes(text_bytes)
    text_sha256 = compute_sha256(text_bytes)

    print(f"    OK: HTML={len(html_bytes)} bytes, Text={len(text_bytes)} bytes"
          + (" [TRUNCATED]" if truncated else ""))

    return SourceFetch(
        url=url,
        slug=slug,
        description=description,
        source_type=source_type,
        fetched_at_utc=fetched_at,
        fetch_success=True,
        error_message=None,
        html_path=str(html_path.relative_to(output_dir.parent.parent)),
        html_size_bytes=len(html_bytes),
        html_sha256=html_sha256,
        text_path=str(text_path.relative_to(output_dir.parent.parent)),
        text_size_bytes=len(text_bytes),
        text_sha256=text_sha256,
        truncated=truncated
    )


def main():
    """Main entry point."""
    # Determine timestamp (from env or use Asia/Karachi time)
    timestamp = os.environ.get('LIVE_E2E_TIMESTAMP', '20260127-1831')

    # Paths
    repo_root = Path(__file__).parent.parent
    config_file = repo_root / "config" / "live_e2e_sources.yaml"
    output_dir = repo_root / ".live_e2e_data" / timestamp
    reports_dir = repo_root / "reports" / "live_e2e_ollama" / timestamp

    print(f"Live E2E Data Fetcher")
    print(f"=" * 80)
    print(f"Timestamp: {timestamp}")
    print(f"Config: {config_file}")
    print(f"Output: {output_dir}")
    print()

    # Load config
    if not config_file.exists():
        print(f"ERROR: Config file not found: {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        config = yaml.safe_load(f)

    kb_sources = config.get('kb_sources', [])
    ref_sources = config.get('reference_sources', [])
    max_html_size = config.get('max_html_size_bytes', 512000)
    max_text_size = config.get('max_text_size_bytes', 204800)

    print(f"KB sources: {len(kb_sources)}")
    print(f"Reference sources: {len(ref_sources)}")
    print(f"Max HTML size: {max_html_size} bytes")
    print(f"Max text size: {max_text_size} bytes")
    print()

    # Fetch KB sources
    print("Fetching KB sources...")
    kb_results = []
    for source in kb_sources:
        result = fetch_source(source, 'kb', output_dir, max_html_size, max_text_size)
        kb_results.append(result)
        time.sleep(0.5)  # Be nice to servers

    print()
    print("Fetching reference sources...")
    ref_results = []
    for source in ref_sources:
        result = fetch_source(source, 'reference', output_dir, max_html_size, max_text_size)
        ref_results.append(result)
        time.sleep(0.5)

    # Generate manifest
    all_results = kb_results + ref_results
    successful = [r for r in all_results if r.fetch_success]
    failed = [r for r in all_results if not r.fetch_success]

    total_html_bytes = sum(r.html_size_bytes for r in successful)
    total_text_bytes = sum(r.text_size_bytes for r in successful)

    manifest = {
        'timestamp': timestamp,
        'fetched_at_utc': datetime.now(timezone.utc).isoformat(),
        'config_file': str(config_file.relative_to(repo_root)),
        'summary': {
            'total_sources': len(all_results),
            'successful': len(successful),
            'failed': len(failed),
            'kb_count': len([r for r in successful if r.source_type == 'kb']),
            'reference_count': len([r for r in successful if r.source_type == 'reference']),
            'total_html_bytes': total_html_bytes,
            'total_text_bytes': total_text_bytes,
            'truncated_count': len([r for r in successful if r.truncated])
        },
        'sources': [asdict(r) for r in all_results]
    }

    # Save manifest
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = reports_dir / "dataset_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total sources: {manifest['summary']['total_sources']}")
    print(f"Successful: {manifest['summary']['successful']}")
    print(f"Failed: {manifest['summary']['failed']}")
    print(f"KB docs: {manifest['summary']['kb_count']}")
    print(f"Reference docs: {manifest['summary']['reference_count']}")
    print(f"Total HTML: {total_html_bytes:,} bytes ({total_html_bytes/1024:.1f} KB)")
    print(f"Total text: {total_text_bytes:,} bytes ({total_text_bytes/1024:.1f} KB)")
    print(f"Truncated: {manifest['summary']['truncated_count']}")
    print()
    print(f"Manifest saved: {manifest_path}")
    print()

    if failed:
        print("FAILED SOURCES:")
        for r in failed:
            print(f"  - {r.slug}: {r.error_message}")
        print()

    # Generate summary markdown
    summary_md = f"""# Live E2E Dataset Summary

## Overview
- **Timestamp**: {timestamp}
- **Fetched**: {manifest['fetched_at_utc']}
- **Total Sources**: {manifest['summary']['total_sources']}
- **Successful**: {manifest['summary']['successful']}
- **Failed**: {manifest['summary']['failed']}

## Breakdown
- **KB Documents**: {manifest['summary']['kb_count']}
- **Reference Documents**: {manifest['summary']['reference_count']}
- **Total HTML**: {total_html_bytes:,} bytes ({total_html_bytes/1024:.1f} KB)
- **Total Extracted Text**: {total_text_bytes:,} bytes ({total_text_bytes/1024:.1f} KB)
- **Truncated**: {manifest['summary']['truncated_count']}

## KB Sources
"""

    for r in kb_results:
        if r.fetch_success:
            summary_md += f"- **{r.slug}**: {r.description} ({r.text_size_bytes:,} bytes)\n"
        else:
            summary_md += f"- **{r.slug}**: FAILED - {r.error_message}\n"

    summary_md += "\n## Reference Sources\n"

    for r in ref_results:
        if r.fetch_success:
            summary_md += f"- **{r.slug}**: {r.description} ({r.text_size_bytes:,} bytes)\n"
        else:
            summary_md += f"- **{r.slug}**: FAILED - {r.error_message}\n"

    if failed:
        summary_md += "\n## Failed Fetches\n"
        for r in failed:
            summary_md += f"- **{r.slug}** ({r.url}): {r.error_message}\n"

    summary_md += f"\n## Files\n"
    summary_md += f"- Manifest: `{manifest_path.relative_to(repo_root)}`\n"
    summary_md += f"- Raw HTML: `.live_e2e_data/{timestamp}/raw/`\n"
    summary_md += f"- Extracted text: `.live_e2e_data/{timestamp}/extracted/`\n"

    summary_path = reports_dir / "dataset_summary.md"
    summary_path.write_text(summary_md)
    print(f"Summary saved: {summary_path}")

    # Exit with error if any fetches failed
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
