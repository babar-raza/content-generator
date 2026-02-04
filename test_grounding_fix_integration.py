"""Integration test for grounding enforcer fix.

Tests the complete flow: content generation -> frontmatter -> expansion -> grounding.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.frontmatter_normalize import enforce_frontmatter
from src.utils.content_expansion import ensure_minimum_size, TARGET_BYTES
from src.utils.grounding_enforcer import enforce_minimum_references
from tools.quality_gate import evaluate_output

def test_art_content_flow():
    """Test the complete content generation flow for ART File Format."""

    # Simulate generated content (what LLM produces)
    topic = "ART File Format"
    initial_content = f"""---
title: {topic}
tags:
- auto-generated
date: auto
---

## Overview

{topic} is an important technical concept that requires understanding of its core principles and practical applications.

## Technical Details

This format provides structured data storage with specific encoding requirements.
"""

    print(f"Testing content generation flow for: {topic}")
    print("=" * 80)

    # Step 1: Enforce frontmatter
    print("\n[Step 1] Enforcing frontmatter...")
    content = enforce_frontmatter(initial_content, fallback_metadata={
        'title': topic,
        'tags': ['auto-generated'],
        'date': 'auto'
    })
    print(f"  Frontmatter OK: {len(content)} chars")

    # Step 2: Expand to minimum size (simulated - without LLM for this test)
    print("\n[Step 2] Ensuring minimum size...")
    # For testing, we'll use the deterministic fallback directly
    from src.utils.content_expansion import deterministic_fallback_expansion
    content = deterministic_fallback_expansion(content, topic)
    print(f"  Size OK: {len(content.encode('utf-8'))} bytes (target: {TARGET_BYTES})")

    # Step 3: Enforce minimum references (THE FIX)
    print("\n[Step 3] Enforcing minimum references...")
    content = enforce_minimum_references(
        content=content,
        topic=topic,
        min_refs=3
    )
    print(f"  References enforced: {len(content)} chars")

    # Step 4: Save to temp file and run quality gate
    print("\n[Step 4] Running quality gate...")
    temp_output = Path("test_grounding_output.md")
    with open(temp_output, "w", encoding="utf-8") as f:
        f.write(content)

    result = evaluate_output(str(temp_output))

    print("\nQuality Gate Result:")
    print(f"  Pass: {result['pass']}")
    print(f"  Reference count: {result['metrics']['reference_count']}")
    print(f"  Size: {result['metrics']['size_bytes']} bytes")
    print(f"  Headings: {result['metrics']['heading_count']}")
    print(f"  Sections: {result['metrics']['section_count']}")

    if result['pass']:
        print("\n[OK] Quality gate PASSED!")
        print(f"  All criteria met, including grounding (>= 3 references)")
        return True
    else:
        print("\n[FAIL] Quality gate FAILED!")
        print(f"  Failures: {result['failures']}")
        return False

if __name__ == '__main__':
    success = test_art_content_flow()
    sys.exit(0 if success else 1)
