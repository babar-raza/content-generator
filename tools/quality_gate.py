#!/usr/bin/env python3
"""Quality gate v2.0 - robust multi-dimensional quality evaluation.

Replaces brittle byte-only threshold with comprehensive rubric:
- A) Frontmatter validity
- B) Structural headings (≥3)
- C) Completeness (≥2 sections)
- D) Grounding (≥2 references)
- E) Size (soft: 1800 hard min, 2200+ target)
- F) Safety (no fenced frontmatter)
- G) Markdown syntax (REQUIRED: no unclosed code blocks, orphaned markers)
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


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


def validate_markdown_syntax(content: str) -> Tuple[bool, List[str]]:
    """Validate markdown syntax for common errors.

    Detects:
    - Unclosed code blocks
    - Orphaned backtick markers
    - Mismatched code fence pairs
    - Orphaned language specifiers (missing opening fence)

    Args:
        content: Markdown content to validate

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Track code fence state
    in_code_block = False
    code_fence_stack = []

    lines = content.split('\n')

    # Common language specifiers that shouldn't appear standalone
    lang_specifiers = {
        'python', 'javascript', 'java', 'bash', 'sh', 'yaml', 'json',
        'xml', 'sql', 'typescript', 'cpp', 'c', 'ruby', 'go', 'rust',
        'html', 'css', 'php', 'perl', 'swift', 'kotlin', 'scala'
    }

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Detect code fence markers (``` or ~~~)
        if stripped.startswith('```') or stripped.startswith('~~~'):
            fence_marker = stripped[:3]
            # Check if this is an opening fence (has language specifier) or closing fence (bare)
            has_language = len(stripped) > 3 and stripped[3:].strip()

            if not in_code_block:
                # We're outside a code block, so this must be an opening fence
                in_code_block = True
                code_fence_stack.append((i, fence_marker, stripped))
            else:
                # We're inside a code block
                # If this fence has a language specifier, it's likely a nested/orphaned opening
                if has_language:
                    # This is a fence with language specifier inside a code block - error!
                    errors.append(f"Nested code block at line {i}: found {stripped} inside block opened at line {code_fence_stack[-1][0] if code_fence_stack else '?'}")
                else:
                    # This is a bare fence - should be closing
                    if code_fence_stack:
                        open_line, open_marker, _ = code_fence_stack.pop()
                        if fence_marker != open_marker:
                            errors.append(f"Mismatched code fence: {open_marker} at line {open_line}, {fence_marker} at line {i}")
                    else:
                        # Closing fence without opening - shouldn't happen if logic is correct
                        errors.append(f"Orphaned closing fence at line {i} without matching opening")
                    in_code_block = False

        # Check for standalone language specifiers (orphaned)
        elif stripped.lower() in lang_specifiers and not in_code_block:
            # Check if previous line was a fence opening
            if i > 1:
                prev_line = lines[i-2].strip()  # i is 1-indexed, lines is 0-indexed
                if not (prev_line.startswith('```') or prev_line.startswith('~~~')):
                    errors.append(f"Orphaned language specifier '{stripped}' at line {i} without opening fence")
            else:
                # Language specifier at start of file without fence
                errors.append(f"Orphaned language specifier '{stripped}' at line {i} without opening fence")

    # Check for unclosed blocks
    if in_code_block and code_fence_stack:
        for open_line, marker, _ in code_fence_stack:
            errors.append(f"Unclosed code block: {marker} opened at line {open_line} never closed")

    return len(errors) == 0, errors


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

    # G) Markdown syntax check (REQUIRED)
    syntax_valid, syntax_errors = validate_markdown_syntax(content)
    result["metrics"]["syntax_valid"] = syntax_valid
    result["metrics"]["syntax_error_count"] = len(syntax_errors)

    if syntax_valid:
        result["reasons"].append("criterion_g_syntax_valid")
    else:
        error_summary = "; ".join(syntax_errors[:3])
        if len(syntax_errors) > 3:
            error_summary += f" (and {len(syntax_errors) - 3} more)"
        result["failures"].append(f"criterion_g_syntax_errors_{len(syntax_errors)}")
        result["metrics"]["syntax_errors"] = syntax_errors

    # Overall pass: all REQUIRED criteria met
    required_pass = (
        has_frontmatter and
        not has_fenced and
        heading_count >= 3 and
        section_count >= 2 and
        reference_count >= 2 and
        size >= HARD_MIN and
        syntax_valid
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
