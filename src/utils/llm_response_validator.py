"""LLM Response Validator - Layer 1 validation to catch errors at the source.

This module provides fast (<15ms) validation of LLM responses to catch structural
issues before they propagate through the pipeline. It enables retry logic with
enhanced prompts when validation fails.

Key Features:
- Detects unbalanced code blocks (``` markers must be even)
- Identifies frontmatter contamination (agents shouldn't generate ---)
- Validates structural sanity (minimum length, prose content)
- Detects truncation (ends properly, not mid-sentence)
- Validates JSON responses (outline creation)
- Fast validation (<15ms) using compiled regex patterns
- Content-type aware (outline/section/full_document/unknown)
- Returns structured ValidationResult for retry logic

Integration Point: src/services/services.py LLMService.generate() (line ~407)
"""

import re
import json
import logging
import time
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Compiled regex patterns (module-level for performance)
CODE_FENCE_PATTERN = re.compile(r'^\s*```', re.MULTILINE)
FRONTMATTER_PATTERN = re.compile(r'^---\s*$', re.MULTILINE)
TRUNCATION_PATTERN = re.compile(r'[.!?]\s*$|```\s*$')
HEADING_PATTERN = re.compile(r'^#{1,6}\s+.+$', re.MULTILINE)
PROSE_PATTERN = re.compile(r'[a-zA-Z]{4,}.*[a-zA-Z]{4,}')  # Multi-word sentences


@dataclass
class ValidationResult:
    """Result of LLM response validation.

    Attributes:
        is_valid: True if all validation checks passed
        errors: List of error messages (empty if valid)
        warnings: List of warning messages (non-blocking issues)
        content_type: Content type that was validated
        validation_duration_ms: Time taken for validation in milliseconds
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    content_type: str
    validation_duration_ms: int


def validate_code_block_balance(content: str) -> tuple[bool, List[str]]:
    """Validate that code fence markers (```) are balanced.

    Args:
        content: LLM response content

    Returns:
        Tuple of (is_valid, errors)
        - is_valid: True if code fences are balanced
        - errors: List of error messages (empty if valid)
    """
    fence_matches = CODE_FENCE_PATTERN.findall(content)
    fence_count = len(fence_matches)

    if fence_count % 2 != 0:
        error_msg = (
            f"Unbalanced code fences: found {fence_count} ``` markers (must be even). "
            f"LLM likely wrapped entire response in a code block or left one unclosed."
        )
        return False, [error_msg]

    return True, []


def validate_no_frontmatter(content: str) -> tuple[bool, List[str]]:
    """Validate no duplicate or contaminated frontmatter in content.

    A single frontmatter block at document start is allowed (may have been
    added by the enforcement layer). Flags:
    - Multiple frontmatter blocks (duplicate contamination)
    - Frontmatter deep in the body (not at document start)

    Args:
        content: LLM response content

    Returns:
        Tuple of (is_valid, errors)
        - is_valid: True if no contaminated frontmatter found
        - errors: List of error messages (empty if valid)
    """
    lines = content.split('\n')
    fm_blocks = []
    i = 0

    while i < len(lines):
        if lines[i].strip() == '---':
            block_start = i
            i += 1
            has_yaml = False
            while i < len(lines) and lines[i].strip() != '---':
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*:', lines[i].strip()):
                    has_yaml = True
                i += 1
            if i < len(lines) and has_yaml:
                fm_blocks.append(block_start)
                i += 1
            else:
                if i < len(lines):
                    i += 1
        else:
            i += 1

    if len(fm_blocks) > 1:
        return False, [
            f"Duplicate frontmatter contamination: Found {len(fm_blocks)} frontmatter blocks "
            f"at lines {[b + 1 for b in fm_blocks]} (only 1 at document start is allowed)"
        ]

    if len(fm_blocks) == 1 and fm_blocks[0] > 5:
        return False, [
            f"Frontmatter contamination: Found frontmatter block at line {fm_blocks[0] + 1} "
            f"(should only appear at document start)"
        ]

    return True, []


def validate_structural_sanity(content: str, content_type: str, allow_partial: bool) -> tuple[bool, List[str], List[str]]:
    """Validate basic structural requirements of LLM response.

    Checks:
    1. Minimum length (>500 chars for full content, >200 for partials)
    2. Contains prose content (not just code)
    3. Has headings (for section/full_document types)

    Args:
        content: LLM response content
        content_type: Type of content (outline/section/full_document/unknown)
        allow_partial: If True, relax length requirements

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    # Check 1: Minimum length
    min_length = 200 if allow_partial else 500
    if len(content) < min_length:
        errors.append(
            f"Content too short: {len(content)} chars (minimum: {min_length}). "
            f"LLM response appears truncated or incomplete."
        )

    # Check 2: Contains prose (not all code)
    prose_matches = PROSE_PATTERN.findall(content)
    if len(prose_matches) < 3:
        errors.append(
            f"Insufficient prose content: found {len(prose_matches)} multi-word sentences. "
            f"Response appears to be mostly code or malformed."
        )

    # Check 3: Has headings (for non-outline content)
    if content_type in ['section', 'full_document']:
        heading_matches = HEADING_PATTERN.findall(content)
        if len(heading_matches) < 1:
            warnings.append(
                f"No headings found for content_type '{content_type}'. "
                f"Expected at least one markdown heading (# or ##)."
            )

    # Check 4: Not entirely wrapped in code block
    stripped = content.strip()
    if stripped.startswith('```') and stripped.endswith('```'):
        # Entire content is in one code block
        # Count newlines to see if it's substantial
        if content.count('\n') > 10:
            errors.append(
                "Entire response wrapped in code block. "
                "LLM should generate markdown prose, not wrap everything in ```."
            )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def validate_no_truncation(content: str) -> tuple[bool, List[str]]:
    """Validate that response ends properly (not mid-sentence).

    Args:
        content: LLM response content

    Returns:
        Tuple of (is_valid, errors)
    """
    # Check if content ends with proper punctuation or code fence
    stripped = content.rstrip()

    if not stripped:
        return False, ["Response is empty or only whitespace"]

    # Get last 100 chars to check ending
    ending = stripped[-100:] if len(stripped) > 100 else stripped

    # Valid endings: sentence punctuation, code fence, list item
    valid_ending = (
        TRUNCATION_PATTERN.search(ending) or
        ending.endswith('\n') or
        re.search(r'[0-9]\.$', ending)  # Numbered list item
    )

    if not valid_ending:
        # Check if it looks like mid-sentence truncation
        last_line = stripped.split('\n')[-1]
        if len(last_line) > 20 and not last_line[-1] in '.!?`:' and not last_line.endswith('```'):
            return False, [
                f"Response appears truncated (ends mid-sentence): '...{last_line[-50:]}'"
            ]

    return True, []


def validate_json_response(content: str) -> tuple[bool, List[str]]:
    """Validate JSON syntax for json_mode responses.

    Used for outline creation where LLM returns JSON structure.

    Args:
        content: LLM response (should be JSON)

    Returns:
        Tuple of (is_valid, errors)
    """
    try:
        parsed = json.loads(content)

        # Additional check: must be dict or list, not just a string/number
        if not isinstance(parsed, (dict, list)):
            return False, [
                f"JSON response is not a dict or list (got {type(parsed).__name__})"
            ]

        return True, []

    except json.JSONDecodeError as e:
        return False, [
            f"Invalid JSON syntax: {str(e)}"
        ]


def validate_llm_response(
    content: str,
    content_type: str = 'unknown',
    allow_partial: bool = False
) -> ValidationResult:
    """Validate LLM response for structural issues before processing.

    This is the main entry point for Layer 1 validation. It runs fast (<15ms)
    checks to catch common LLM errors before they propagate through the pipeline.

    Validation checks depend on content_type:
    - outline: JSON validity, structural sanity
    - section: Code block balance, no frontmatter, structural sanity, no truncation
    - full_document: All checks (code blocks, frontmatter, structure, truncation)
    - unknown: All checks (default for safety)

    Args:
        content: LLM response text to validate
        content_type: Type of content being validated
            - 'outline': Expect JSON structure
            - 'section': Expect markdown prose section
            - 'full_document': Expect complete markdown document
            - 'unknown': Apply all checks (default)
        allow_partial: If True, relax length requirements for partial content

    Returns:
        ValidationResult with is_valid, errors, warnings, content_type, duration

    Example:
        >>> result = validate_llm_response(llm_output, content_type='section')
        >>> if not result.is_valid:
        ...     logger.warning(f"Validation failed: {result.errors}")
        ...     # Retry with enhanced prompt
    """
    start_time = time.perf_counter()

    all_errors = []
    all_warnings = []

    logger.debug(f"Validating LLM response: content_type={content_type}, length={len(content)}")

    # Content type specific validation
    if content_type == 'outline':
        # Outline: Expect JSON
        is_valid_json, json_errors = validate_json_response(content)
        all_errors.extend(json_errors)

        # Also check basic structure (but allow shorter content)
        is_valid_struct, struct_errors, struct_warnings = validate_structural_sanity(
            content, content_type, allow_partial=True
        )
        # For JSON, structural errors are less critical
        all_warnings.extend(struct_errors)
        all_warnings.extend(struct_warnings)

    elif content_type in ['section', 'full_document', 'unknown']:
        # Markdown content: Run all checks

        # Check 1: Code block balance
        is_balanced, balance_errors = validate_code_block_balance(content)
        all_errors.extend(balance_errors)

        # Check 2: No frontmatter contamination
        is_clean_fm, fm_errors = validate_no_frontmatter(content)
        all_errors.extend(fm_errors)

        # Check 3: Structural sanity
        is_valid_struct, struct_errors, struct_warnings = validate_structural_sanity(
            content, content_type, allow_partial
        )
        all_errors.extend(struct_errors)
        all_warnings.extend(struct_warnings)

        # Check 4: No truncation (only for full_document and unknown)
        if content_type in ['full_document', 'unknown']:
            is_complete, truncation_errors = validate_no_truncation(content)
            all_errors.extend(truncation_errors)

    else:
        # Unknown content type - log warning and apply all checks
        logger.warning(f"Unknown content_type '{content_type}', applying all checks")
        all_warnings.append(f"Unknown content_type '{content_type}'")

        # Run all checks
        is_balanced, balance_errors = validate_code_block_balance(content)
        all_errors.extend(balance_errors)

        is_clean_fm, fm_errors = validate_no_frontmatter(content)
        all_errors.extend(fm_errors)

        is_valid_struct, struct_errors, struct_warnings = validate_structural_sanity(
            content, content_type, allow_partial
        )
        all_errors.extend(struct_errors)
        all_warnings.extend(struct_warnings)

        is_complete, truncation_errors = validate_no_truncation(content)
        all_errors.extend(truncation_errors)

    # Calculate duration
    end_time = time.perf_counter()
    duration_ms = int((end_time - start_time) * 1000)

    # Determine overall validity
    is_valid = len(all_errors) == 0

    # Log results
    if is_valid:
        logger.debug(f"  ✓ LLM response validation passed ({duration_ms}ms)")
        if all_warnings:
            logger.debug(f"  ⚠ {len(all_warnings)} warning(s): {all_warnings}")
    else:
        logger.warning(f"  ✗ LLM response validation failed ({duration_ms}ms)")
        logger.warning(f"  Errors: {all_errors}")
        if all_warnings:
            logger.warning(f"  Warnings: {all_warnings}")

    return ValidationResult(
        is_valid=is_valid,
        errors=all_errors,
        warnings=all_warnings,
        content_type=content_type,
        validation_duration_ms=duration_ms
    )


def enhance_prompt_for_retry(original_prompt: str, validation_errors: List[str]) -> str:
    """Enhance prompt with specific instructions based on validation errors.

    This is used in retry logic to guide the LLM to avoid previous mistakes.

    Args:
        original_prompt: Original prompt that led to invalid response
        validation_errors: List of validation errors from previous attempt

    Returns:
        Enhanced prompt with added instructions
    """
    enhancements = []

    # Detect error types and add specific instructions
    error_text = ' '.join(validation_errors).lower()

    if 'code fence' in error_text or 'code block' in error_text:
        enhancements.append(
            "CRITICAL: Do NOT wrap your entire response in a code block (```). "
            "Use code blocks ONLY for code examples, not for the entire markdown content."
        )

    if 'frontmatter' in error_text:
        enhancements.append(
            "CRITICAL: Do NOT include YAML frontmatter (--- markers). "
            "Frontmatter will be added automatically by the system."
        )

    if 'truncat' in error_text or 'too short' in error_text:
        enhancements.append(
            "IMPORTANT: Provide a COMPLETE response. Do not truncate or cut off mid-sentence. "
            "Ensure the response ends with proper punctuation."
        )

    if 'prose' in error_text or 'heading' in error_text:
        enhancements.append(
            "IMPORTANT: Generate proper markdown prose with headings (##) and paragraphs. "
            "Do not generate only code or lists."
        )

    # Build enhanced prompt
    if enhancements:
        enhancement_block = '\n'.join(enhancements)
        return f"{enhancement_block}\n\n---\n\n{original_prompt}"
    else:
        # Generic enhancement if no specific pattern detected
        return (
            "IMPORTANT: Generate clean markdown content without wrapping in code blocks. "
            "Do not include YAML frontmatter. Provide complete, well-structured content.\n\n"
            f"---\n\n{original_prompt}"
        )


def check_code_block_balance(content: str) -> tuple[bool, list]:
    """Check code block balance (convenience wrapper)."""
    return validate_code_block_balance(content)


def check_frontmatter_contamination(content: str) -> tuple[bool, list]:
    """Check for duplicate/contaminated frontmatter (convenience wrapper)."""
    return validate_no_frontmatter(content)


def check_minimum_content(content: str, min_length: int = 500) -> tuple[bool, list]:
    """Check content meets minimum length requirement."""
    stripped = content.strip()
    if len(stripped) < min_length:
        return False, [
            f"Content below minimum length: {len(stripped)} chars < {min_length} required"
        ]
    return True, []


def check_prose_content(content: str) -> tuple[bool, list]:
    """Check content has sufficient prose (multi-word sentences)."""
    prose_matches = PROSE_PATTERN.findall(content)
    if len(prose_matches) < 3:
        return False, [
            f"Insufficient prose: {len(prose_matches)} multi-word phrases (need ≥3)"
        ]
    return True, []


def check_truncation_indicators(content: str) -> tuple[bool, list]:
    """Check for truncation indicators in content."""
    stripped = content.rstrip()
    if not stripped:
        return False, ["Response is empty or only whitespace"]

    # Check for explicit truncation markers (... at end)
    if stripped.endswith('...'):
        return False, [
            f"Truncation indicator: content ends with '...'"
        ]

    # Check for incomplete code block
    in_code_block = False
    for line in stripped.split('\n'):
        if re.match(r'^\s*```', line):
            in_code_block = not in_code_block
    if in_code_block:
        return False, [
            "Truncation indicator: content ends inside unclosed code block"
        ]

    # Check for mid-sentence ending
    last_line = stripped.split('\n')[-1].strip()
    if last_line and len(last_line) > 20:
        if last_line[-1] not in '.!?`:;\'")\u201d' and not last_line.endswith('```'):
            return False, [
                f"Truncation indicator: content appears cut off mid-sentence"
            ]

    return True, []


def check_json_validity(content: str) -> tuple[bool, list]:
    """Check JSON validity (convenience wrapper)."""
    return validate_json_response(content)


def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: llm_response_validator.py <input_file> [content_type]")
        print("Validates LLM response content for structural issues")
        print("content_type: outline|section|full_document|unknown (default: unknown)")
        sys.exit(1)

    input_file = sys.argv[1]
    content_type = sys.argv[2] if len(sys.argv) > 2 else 'unknown'

    # Configure logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Read input
    print(f"Validating: {input_file}")
    print(f"Content type: {content_type}")
    print("-" * 80)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"[FAIL] Cannot read file: {e}")
        sys.exit(1)

    # Validate
    result = validate_llm_response(content, content_type=content_type)

    # Display results
    print(f"\nValidation Result:")
    print(f"  Valid: {result.is_valid}")
    print(f"  Duration: {result.validation_duration_ms}ms")
    print(f"  Content Type: {result.content_type}")

    if result.errors:
        print(f"\n  Errors ({len(result.errors)}):")
        for i, error in enumerate(result.errors, 1):
            print(f"    {i}. {error}")

    if result.warnings:
        print(f"\n  Warnings ({len(result.warnings)}):")
        for i, warning in enumerate(result.warnings, 1):
            print(f"    {i}. {warning}")

    # Exit code
    if result.is_valid:
        print("\n[OK] Validation passed")
        sys.exit(0)
    else:
        print("\n[FAIL] Validation failed")

        # Show enhanced prompt for retry
        if result.errors:
            print("\n" + "=" * 80)
            print("Enhanced prompt for retry:")
            print("=" * 80)
            enhanced = enhance_prompt_for_retry("Original prompt here", result.errors)
            print(enhanced)

        sys.exit(1)


if __name__ == '__main__':
    main()
