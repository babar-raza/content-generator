#!/usr/bin/env python3
"""Quality gate v2.0 - robust multi-dimensional quality evaluation.

Replaces brittle byte-only threshold with comprehensive rubric:
- A) Frontmatter validity
- B) Structural headings (≥3)
- C) Completeness (≥2 sections)
- D) Grounding (≥2 references)
- E) Size (soft: 1800 hard min, 2200+ target)
- F) Safety (no fenced frontmatter)
"""

import re
from pathlib import Path
from typing import Dict, List


def check_frontmatter(content: str) -> tuple[bool, bool]:
    """Check frontmatter validity and detect fenced blocks.

    Returns:
        (has_valid_frontmatter, has_fenced_frontmatter)
    """
    # Check for valid frontmatter
    valid_pattern = r'^---\s*\n.*?\n---\s*\n'
    has_valid = re.match(valid_pattern, content, re.DOTALL) is not None

    # Check for dangerous fenced frontmatter (```yaml at top)
    fenced_pattern = r'^```ya?ml\s*\n'
    has_fenced = re.match(fenced_pattern, content, re.IGNORECASE) is not None

    return has_valid, has_fenced


def count_headings(content: str) -> int:
    """Count markdown headings."""
    lines = content.split('\n')
    count = 0
    for line in lines:
        stripped = line.strip()
        # Count # or ## or ### style headings (but not #### and deeper for main structure)
        if stripped and re.match(r'^#{1,3}\s+\w', stripped):
            count += 1
    return count


def count_sections(content: str) -> int:
    """Count distinct content sections (text between headings)."""
    # Split by headings
    sections = re.split(r'\n#{1,4}\s+', content)

    # Count sections with substantial content (>100 chars after stripping)
    substantial_sections = 0
    for section in sections:
        # Remove frontmatter from first section
        if section.startswith('---'):
            section = re.sub(r'^---\s*\n.*?\n---\s*\n', '', section, flags=re.DOTALL)

        cleaned = section.strip()
        if len(cleaned) > 100:
            substantial_sections += 1

    return substantial_sections


def count_references(content: str) -> int:
    """Count references/citations/grounding evidence.

    Detects:
    - Quoted terms: "something"
    - Named references: UCOP, Aspose, etc.
    - Citation markers: [1], (Source: X)
    """
    reference_count = 0

    # Pattern 1: Quoted terms (multi-word phrases in quotes)
    quoted_pattern = r'"[A-Za-z][A-Za-z\s]{2,}"'
    quoted_matches = re.findall(quoted_pattern, content)
    reference_count += len(quoted_matches)

    # Pattern 2: Explicit citations/sources
    citation_pattern = r'\(Source:|\[[\d]+\]|References:|Citations:'
    citation_matches = re.findall(citation_pattern, content, re.IGNORECASE)
    reference_count += len(citation_matches)

    # Pattern 3: Named entities that suggest grounding (proper nouns, organizations)
    # Look for capitalized multi-word phrases that aren't headings
    lines = [l for l in content.split('\n') if not l.strip().startswith('#')]
    content_no_headings = '\n'.join(lines)

    entity_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
    entities = re.findall(entity_pattern, content_no_headings)
    # Count unique entities (avoid double counting)
    unique_entities = set(entities)
    # Only count substantial entities (not common words)
    substantial_entities = [e for e in unique_entities if len(e) > 5]
    reference_count += min(len(substantial_entities), 3)  # Cap contribution

    return reference_count


def evaluate_output(output_path: str) -> Dict:
    """Evaluate a single output file against quality rubric v2.0.

    Args:
        output_path: Path to markdown output file

    Returns:
        dict with structure:
        {
            "pass": bool,
            "reasons": [list of passing criteria],
            "failures": [list of failing criteria],
            "metrics": {detailed measurements}
        }
    """
    path = Path(output_path)

    result = {
        "pass": False,
        "reasons": [],
        "failures": [],
        "metrics": {
            "exists": False,
            "size_bytes": 0,
            "has_frontmatter": False,
            "has_fenced_frontmatter": False,
            "heading_count": 0,
            "section_count": 0,
            "reference_count": 0
        }
    }

    # Check existence
    if not path.exists():
        result["failures"].append("file_not_found")
        return result

    result["metrics"]["exists"] = True
    result["reasons"].append("file_exists")

    # Check size
    size = path.stat().st_size
    result["metrics"]["size_bytes"] = size

    # Read content
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        result["failures"].append(f"read_error_{str(e)}")
        return result

    # A) Frontmatter check (REQUIRED)
    has_frontmatter, has_fenced = check_frontmatter(content)
    result["metrics"]["has_frontmatter"] = has_frontmatter
    result["metrics"]["has_fenced_frontmatter"] = has_fenced

    if has_frontmatter:
        result["reasons"].append("criterion_a_frontmatter_valid")
    else:
        result["failures"].append("criterion_a_frontmatter_missing")

    # F) Safety check - no fenced frontmatter (REQUIRED)
    if has_fenced:
        result["failures"].append("criterion_f_safety_fenced_frontmatter")
    else:
        result["reasons"].append("criterion_f_safety_no_fenced_frontmatter")

    # B) Structure check - headings (REQUIRED)
    heading_count = count_headings(content)
    result["metrics"]["heading_count"] = heading_count

    if heading_count >= 3:
        result["reasons"].append("criterion_b_structure_sufficient_headings")
    else:
        result["failures"].append(f"criterion_b_structure_insufficient_headings_{heading_count}")

    # C) Completeness check - sections (REQUIRED)
    section_count = count_sections(content)
    result["metrics"]["section_count"] = section_count

    if section_count >= 2:
        result["reasons"].append("criterion_c_completeness_sufficient_sections")
    else:
        result["failures"].append(f"criterion_c_completeness_insufficient_sections_{section_count}")

    # D) Grounding check - references (REQUIRED)
    reference_count = count_references(content)
    result["metrics"]["reference_count"] = reference_count

    if reference_count >= 2:
        result["reasons"].append("criterion_d_grounding_sufficient_references")
    else:
        result["failures"].append(f"criterion_d_grounding_insufficient_references_{reference_count}")

    # E) Size check (SOFT REQUIREMENT)
    HARD_MIN = 1800
    TARGET = 2200

    if size < HARD_MIN:
        result["failures"].append(f"criterion_e_size_below_hard_minimum_{size}")
    elif size < TARGET:
        result["reasons"].append(f"criterion_e_size_acceptable_{size}")
    else:
        result["reasons"].append(f"criterion_e_size_ideal_{size}")

    # Overall pass: all REQUIRED criteria met
    required_pass = (
        has_frontmatter and
        not has_fenced and
        heading_count >= 3 and
        section_count >= 2 and
        reference_count >= 2 and
        size >= HARD_MIN
    )

    result["pass"] = required_pass

    return result


def main():
    """CLI entry point for testing."""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: quality_gate.py <output_path>")
        print("Evaluates a single output file against quality rubric v2.0")
        sys.exit(1)

    output_path = sys.argv[1]
    result = evaluate_output(output_path)

    print(json.dumps(result, indent=2))

    # Exit code: 0 if pass, 1 if fail
    sys.exit(0 if result["pass"] else 1)


if __name__ == '__main__':
    main()
