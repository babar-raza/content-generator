"""Markdown Validator - Ensures valid markdown syntax in generated content.

This module provides Layer 2 validation for markdown syntax errors that break
rendering, including unbalanced code blocks, nested markdown, and duplicate
frontmatter. It follows the enforcer pattern for integration into the quality
gate pipeline.

Key Features:
- Detects unbalanced code fences (``` markers must be even)
- Identifies nested markdown (headings inside code blocks)
- Finds duplicate frontmatter (YAML frontmatter only at document start)
- Auto-fixes safe cases (orphaned fences, entire-document wrapping)
- Fails fast on ambiguous cases with clear error messages
- Idempotent: can run multiple times safely
- Non-destructive: preserves valid content structure
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def count_code_fences(content: str) -> Tuple[int, List[int]]:
    """Count code fence markers (```) and return their line numbers.

    Args:
        content: Markdown content to analyze

    Returns:
        Tuple of (total_count, line_numbers)
        - total_count: Number of ``` markers found
        - line_numbers: List of 1-indexed line numbers where ``` appears
    """
    lines = content.split('\n')
    fence_lines = []

    for i, line in enumerate(lines, start=1):
        # Match ``` at start of line (allowing leading whitespace)
        if re.match(r'^\s*```', line):
            fence_lines.append(i)

    return len(fence_lines), fence_lines


def validate_balanced_code_blocks(content: str) -> Tuple[bool, List[str]]:
    """Validate that code fence markers are balanced and properly paired.

    Args:
        content: Markdown content to validate

    Returns:
        Tuple of (is_valid, errors)
        - is_valid: True if code fences are balanced
        - errors: List of error messages (empty if valid)
    """
    fence_count, fence_lines = count_code_fences(content)

    if fence_count % 2 != 0:
        error_msg = (
            f"Unbalanced code fences: found {fence_count} ``` markers "
            f"(odd number of fences, must be even). "
            f"Fence locations: lines {fence_lines}"
        )
        logger.warning(f"  ⚠ {error_msg}")
        return False, [error_msg]

    # Additional check: look for language specifiers without opening fence
    lines = content.split('\n')
    errors = []

    for i, line in enumerate(lines, start=1):
        line_stripped = line.strip()
        # Check for standalone language specifier
        if line_stripped in ['python', 'javascript', 'java', 'bash', 'sh', 'yaml', 'json', 'xml', 'sql', 'typescript', 'cpp', 'c', 'ruby', 'go', 'rust']:
            # Previous line should be a fence opening (```)
            # Check if previous line is a fence
            if i > 1:
                prev_line = lines[i-2].strip()  # i is 1-indexed, lines is 0-indexed
                # If previous line is NOT a fence opening, this is an error
                if not re.match(r'^```', prev_line):
                    error_msg = f"Language specifier '{line_stripped}' at line {i} is missing opening ``` fence"
                    errors.append(error_msg)
                    logger.warning(f"  ⚠ {error_msg}")
            else:
                # Language specifier at start of file without fence
                error_msg = f"Language specifier '{line_stripped}' at line {i} is missing opening ``` fence"
                errors.append(error_msg)
                logger.warning(f"  ⚠ {error_msg}")

    if errors:
        return False, errors

    logger.debug(f"  ✓ Code fences balanced: {fence_count} markers at lines {fence_lines}")
    return True, []


def detect_nested_code_blocks(content: str) -> List[Tuple[int, str]]:
    """Detect markdown headings inside code blocks (invalid nesting).

    Note: Single # followed by text can be a valid Python/shell comment,
    so we only flag it if it appears to be a markdown heading (multiple #
    or unusual capitalization pattern).

    Args:
        content: Markdown content to analyze

    Returns:
        List of (line_number, heading_text) tuples for invalid headings
    """
    lines = content.split('\n')
    nested_headings = []
    inside_code_block = False
    code_block_language = None

    for i, line in enumerate(lines, start=1):
        # Toggle code block state and track language
        fence_match = re.match(r'^\s*```(\w*)', line)
        if fence_match:
            if inside_code_block:
                # Closing fence
                inside_code_block = False
                code_block_language = None
            else:
                # Opening fence
                inside_code_block = True
                code_block_language = fence_match.group(1) if fence_match.group(1) else None
            continue

        # Check for headings inside code blocks
        if inside_code_block:
            heading_match = re.match(r'^(\s*)(#{1,6})\s+(.+)$', line)
            if heading_match:
                indent = heading_match.group(1)
                hashes = heading_match.group(2)
                text = heading_match.group(3)

                # If it's a single # in a python/shell/bash block with indent, likely a comment
                if len(hashes) == 1 and code_block_language in ['python', 'py', 'bash', 'sh', 'shell', 'ruby', 'perl', 'yaml']:
                    # This is likely a valid comment, not a markdown heading
                    continue

                # If it's ## or more, always flag it
                if len(hashes) >= 2:
                    nested_headings.append((i, line.strip()))

    return nested_headings


def validate_no_nested_markdown(content: str) -> Tuple[bool, List[str]]:
    """Validate that markdown headings are not nested inside code blocks.

    Args:
        content: Markdown content to validate

    Returns:
        Tuple of (is_valid, errors)
        - is_valid: True if no nested markdown found
        - errors: List of error messages (empty if valid)
    """
    nested = detect_nested_code_blocks(content)

    if nested:
        errors = []
        for line_num, heading in nested:
            error_msg = f"Nested markdown heading inside code block at line {line_num}: '{heading}'"
            errors.append(error_msg)
            logger.warning(f"  ⚠ {error_msg}")
        return False, errors

    logger.debug("  ✓ No nested markdown headings found")
    return True, []


def detect_duplicate_frontmatter(content: str) -> List[int]:
    """Detect duplicate YAML frontmatter blocks in content.

    Valid frontmatter must be at document start (after optional whitespace).
    Any subsequent --- ... --- blocks are duplicates.

    Args:
        content: Markdown content to analyze

    Returns:
        List of line numbers where duplicate frontmatter starts
    """
    lines = content.split('\n')
    frontmatter_starts = []
    seen_first = False
    i = 0

    # Skip leading whitespace/empty lines
    while i < len(lines) and not lines[i].strip():
        i += 1

    # Check if first non-empty line starts valid frontmatter
    if i < len(lines) and lines[i].strip() == '---':
        seen_first = True
        i += 1
        # Skip to end of first frontmatter
        while i < len(lines) and lines[i].strip() != '---':
            i += 1
        if i < len(lines):
            i += 1  # Skip closing ---

    # Look for duplicate frontmatter blocks after the first
    while i < len(lines):
        line = lines[i].strip()
        if line == '---':
            # Check if this starts a YAML-like block (next line has key:value)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Simple heuristic: looks like YAML if has "key:" pattern
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*:', next_line):
                    frontmatter_starts.append(i + 1)  # 1-indexed
                    logger.debug(f"  Found duplicate frontmatter at line {i + 1}")
        i += 1

    return frontmatter_starts


def validate_no_duplicate_frontmatter(content: str) -> Tuple[bool, List[str]]:
    """Validate that frontmatter only appears at document start.

    Args:
        content: Markdown content to validate

    Returns:
        Tuple of (is_valid, errors)
        - is_valid: True if no duplicate frontmatter found
        - errors: List of error messages (empty if valid)
    """
    duplicates = detect_duplicate_frontmatter(content)

    if duplicates:
        errors = []
        for line_num in duplicates:
            error_msg = f"Duplicate frontmatter block found at line {line_num}"
            errors.append(error_msg)
            logger.warning(f"  ⚠ {error_msg}")
        return False, errors

    logger.debug("  ✓ No duplicate frontmatter found")
    return True, []


def validate_markdown_syntax(content: str, skip_nested_check: bool = False) -> Tuple[bool, List[str]]:
    """Validate all markdown syntax requirements.

    Runs all validation checks and aggregates results.

    Args:
        content: Markdown content to validate
        skip_nested_check: If True, skip nested markdown check (used during fix attempts)

    Returns:
        Tuple of (is_valid, errors)
        - is_valid: True if all checks pass
        - errors: List of all error messages from failed checks
    """
    logger.info("Running markdown syntax validation")

    all_errors = []

    # Check 1: Balanced code blocks
    is_balanced, balance_errors = validate_balanced_code_blocks(content)
    all_errors.extend(balance_errors)

    # Check 2: No nested markdown (only if balanced, else might give false positives)
    if not skip_nested_check and is_balanced:
        is_not_nested, nested_errors = validate_no_nested_markdown(content)
        all_errors.extend(nested_errors)
    elif not is_balanced:
        logger.debug("  Skipping nested markdown check due to unbalanced fences")

    # Check 3: No duplicate frontmatter
    is_unique_fm, fm_errors = validate_no_duplicate_frontmatter(content)
    all_errors.extend(fm_errors)

    is_valid = len(all_errors) == 0

    if is_valid:
        logger.info("  ✓ All markdown syntax checks passed")
    else:
        logger.warning(f"  ✗ Markdown syntax validation failed with {len(all_errors)} error(s)")

    return is_valid, all_errors


def auto_fix_markdown_syntax(content: str, errors: List[str]) -> Tuple[str, bool]:
    """Attempt to auto-fix markdown syntax errors.

    Only applies safe, deterministic fixes:
    1. Single orphaned ``` at end → Add closing ```
    2. Entire document wrapped in code block → Unwrap
    3. Duplicate frontmatter → Remove duplicates
    4. Missing opening ``` before language specifier → Add opening ```

    Note: Fixes code fence issues FIRST since they can cause false positives
    in other checks (e.g., nested markdown detection).

    Args:
        content: Markdown content with errors
        errors: List of error messages from validation

    Returns:
        Tuple of (fixed_content, was_fixed)
        - fixed_content: Content after fixes applied
        - was_fixed: True if any fixes were applied

    Raises:
        ValueError: If errors cannot be safely fixed
    """
    logger.info("Attempting auto-fix for markdown syntax errors")
    fixed = content
    applied_fixes = []

    # Fix 1: Check for entire-document code block wrapping
    # Pattern: Frontmatter, then ```, then content, then ``` at very end
    lines = fixed.split('\n')

    # Find frontmatter end
    frontmatter_end_idx = -1
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                frontmatter_end_idx = i
                break

    # Check if code block wraps entire content after frontmatter
    if frontmatter_end_idx >= 0 and frontmatter_end_idx + 1 < len(lines):
        next_line_idx = frontmatter_end_idx + 1
        # Skip empty lines
        while next_line_idx < len(lines) and not lines[next_line_idx].strip():
            next_line_idx += 1

        if next_line_idx < len(lines) and re.match(r'^\s*```', lines[next_line_idx]):
            # Find closing fence at or near end
            last_fence_idx = -1
            for i in range(len(lines) - 1, next_line_idx, -1):
                if re.match(r'^\s*```\s*$', lines[i]):
                    last_fence_idx = i
                    break

            # If found opening and closing that wrap everything
            if last_fence_idx > next_line_idx:
                # Check if there's only whitespace after closing fence
                after_closing = '\n'.join(lines[last_fence_idx + 1:]).strip()
                if not after_closing or len(after_closing) < 50:  # Allow short trailing content
                    logger.info(f"  Detected entire-document code block wrap (lines {next_line_idx + 1} to {last_fence_idx + 1})")
                    # Remove the wrapping fences
                    lines.pop(last_fence_idx)
                    lines.pop(next_line_idx)
                    fixed = '\n'.join(lines)
                    applied_fixes.append("Unwrapped entire-document code block")

    # Fix 2: Missing opening fences before language specifiers
    # This can happen even when total count is even (compensating errors)
    lines = fixed.split('\n')
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # Check if line looks like language specifier (common: python, javascript, etc.)
        if line_stripped in ['python', 'javascript', 'java', 'bash', 'sh', 'yaml', 'json', 'xml', 'sql', 'typescript', 'cpp', 'c', 'ruby', 'go', 'rust']:
            # Check if previous line is NOT a fence
            if i == 0 or not re.match(r'^\s*```', lines[i-1]):
                # This is likely a missing opening fence
                logger.info(f"  Detected missing opening fence before language specifier at line {i + 1}")
                lines[i] = f'```{line_stripped}'
                fixed = '\n'.join(lines)
                applied_fixes.append(f"Added opening ``` before language specifier at line {i + 1}")
                break  # Only fix one at a time, then re-validate

    # Fix 3: Unbalanced code fences (after fixing missing openings)
    fence_count, fence_lines = count_code_fences(fixed)
    if fence_count % 2 != 0:
        # After fixing missing opening fences, re-check balance
        if fence_count % 2 != 0:
            # Check if last fence is orphaned (no closing)
            last_fence_line = fence_lines[-1] - 1  # Convert to 0-indexed

            # Count fences before the last one
            fences_before_last = fence_count - 1

            if fences_before_last % 2 == 0:
                # All fences before last are balanced, so last is orphaned opening
                logger.info(f"  Detected orphaned opening fence at line {fence_lines[-1]}")
                # Add closing fence at end
                fixed = fixed.rstrip() + '\n```\n'
                applied_fixes.append(f"Added closing ``` for orphaned fence at line {fence_lines[-1]}")
            else:
                # More complex case - could be orphaned closing or middle fence
                # Check if first fence is orphaned (missing opening)
                if fence_lines[0] > 1:
                    # Content exists before first fence
                    # Assume first fence is an orphaned closing
                    logger.info(f"  Detected orphaned closing fence at line {fence_lines[0]}")
                    lines = fixed.split('\n')
                    # Find the line and remove the fence
                    for i, line in enumerate(lines):
                        if i + 1 == fence_lines[0] and re.match(r'^\s*```', line):
                            # Remove this line
                            lines[i] = ''
                            fixed = '\n'.join(lines)
                            # Clean up multiple consecutive empty lines
                            fixed = re.sub(r'\n\n\n+', '\n\n', fixed)
                            applied_fixes.append(f"Removed orphaned closing fence at line {fence_lines[0]}")
                            break
                else:
                    # Ambiguous case - cannot safely fix
                    raise ValueError(
                        f"Cannot safely fix unbalanced code fences: {fence_count} fences found. "
                        f"Ambiguous orphaned fence - manual review required. Fence locations: {fence_lines}"
                    )

    # Re-check fence count after potential fixes
    fence_count, fence_lines = count_code_fences(fixed)

    # Fix 4: Remove duplicate frontmatter
    duplicate_fm_lines = detect_duplicate_frontmatter(fixed)
    if duplicate_fm_lines:
        logger.info(f"  Removing {len(duplicate_fm_lines)} duplicate frontmatter block(s)")
        lines = fixed.split('\n')

        for dup_line in sorted(duplicate_fm_lines, reverse=True):  # Remove from end first
            # Find the block: --- at dup_line-1, content, then closing ---
            start_idx = dup_line - 1  # Convert 1-indexed to 0-indexed (--- line)
            if start_idx >= 0 and start_idx < len(lines):
                end_idx = start_idx + 1
                # Find closing ---
                while end_idx < len(lines) and lines[end_idx].strip() != '---':
                    end_idx += 1

                if end_idx < len(lines):
                    # Remove the entire block
                    logger.info(f"    Removing duplicate frontmatter block: lines {start_idx + 1} to {end_idx + 1}")
                    del lines[start_idx:end_idx + 1]
                    applied_fixes.append(f"Removed duplicate frontmatter at line {dup_line}")

        fixed = '\n'.join(lines)
        # Clean up multiple consecutive empty lines
        fixed = re.sub(r'\n\n\n+', '\n\n', fixed)

    # Verify fixes worked
    if applied_fixes:
        logger.info(f"  Applied {len(applied_fixes)} fix(es): {applied_fixes}")
        # Re-validate to confirm
        is_valid, remaining_errors = validate_markdown_syntax(fixed)
        if not is_valid:
            logger.error(f"  ✗ Auto-fix did not resolve all errors: {remaining_errors}")
            raise ValueError(
                f"Auto-fix attempted but errors remain: {remaining_errors}. "
                f"Applied fixes: {applied_fixes}"
            )
        logger.info("  ✓ Auto-fix successful - all errors resolved")
        return fixed, True
    else:
        logger.warning("  No fixes could be safely applied")
        # If there are errors but no fixes applied, fail
        if errors:
            raise ValueError(
                f"Cannot safely fix markdown syntax errors: {errors}. "
                f"Manual review required."
            )
        return fixed, False


def enforce_valid_markdown(
    content: str,
    strict: bool = False,
    auto_fix: bool = True
) -> str:
    """Ensure content has valid markdown syntax.

    This is the main entry point for markdown validation enforcement.
    It validates syntax and optionally auto-fixes safe errors.

    Args:
        content: Markdown content to validate/fix
        strict: If True, fail on any errors (no auto-fix)
        auto_fix: If True, attempt to auto-fix errors (default: True)

    Returns:
        Content with valid markdown syntax

    Raises:
        ValueError: If validation fails and cannot be fixed
    """
    logger.info("Enforcing valid markdown syntax")

    # Validate current state
    is_valid, errors = validate_markdown_syntax(content)

    # If already valid, return as-is
    if is_valid:
        logger.info("  ✓ Content already has valid markdown syntax")
        return content

    # If strict mode, fail immediately
    if strict:
        error_msg = f"Markdown syntax validation failed (strict mode): {errors}"
        logger.error(f"  ✗ {error_msg}")
        raise ValueError(error_msg)

    # Attempt auto-fix if enabled
    if auto_fix:
        logger.info("  Attempting auto-fix for markdown syntax errors")
        fixed_content, was_fixed = auto_fix_markdown_syntax(content, errors)

        if was_fixed:
            logger.info("  ✓ Markdown syntax enforcement successful")
            return fixed_content
        else:
            # No fixes applied but errors exist - this shouldn't happen
            # as auto_fix_markdown_syntax raises ValueError in this case
            error_msg = f"Auto-fix enabled but no fixes applied: {errors}"
            logger.error(f"  ✗ {error_msg}")
            raise ValueError(error_msg)
    else:
        # Auto-fix disabled but errors exist
        error_msg = f"Markdown syntax validation failed (auto-fix disabled): {errors}"
        logger.error(f"  ✗ {error_msg}")
        raise ValueError(error_msg)


def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: markdown_validator.py <input_file> [output_file]")
        print("Validates and fixes markdown syntax in content")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Configure logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Read input
    print(f"Processing: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Enforce valid markdown
    try:
        enforced_content = enforce_valid_markdown(content, strict=False, auto_fix=True)

        # Write output
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(enforced_content)
            print(f"[OK] Wrote fixed content to: {output_file}")
        else:
            print("\n" + "="*80)
            print(enforced_content)
            print("="*80)

        # Show validation results
        is_valid, errors = validate_markdown_syntax(enforced_content)
        if is_valid:
            print(f"\n[OK] Markdown syntax is valid")
        else:
            print(f"\n[WARN] Validation errors remain: {errors}")

    except ValueError as e:
        print(f"[FAIL] Enforcement failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
