#!/usr/bin/env python3
"""Unit tests for LLM Response Validator.

Tests fast validation (<15ms) for common LLM generation errors:
- Unbalanced code blocks
- Frontmatter contamination
- Truncation detection
- JSON validity (outline type)
- Structural sanity checks
- Content type handling

Performance requirement: <15ms for 2KB content, <25ms for 10KB content.
"""

import unittest
import sys
import time
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.llm_response_validator import (
    validate_llm_response as _raw_validate_llm_response,
    check_code_block_balance,
    check_frontmatter_contamination,
    check_minimum_content,
    check_prose_content,
    check_truncation_indicators,
    check_json_validity,
)


def validate_llm_response(**kwargs):
    """Wrapper that returns (is_valid, errors, warnings) tuple for test compat."""
    result = _raw_validate_llm_response(**kwargs)
    return result.is_valid, result.errors, result.warnings


class TestCodeBlockBalance(unittest.TestCase):
    """Test code block balance detection."""

    def test_balanced_code_blocks_pass(self):
        """Balanced code blocks pass validation."""
        content = """# Introduction

Here's a code example:

```python
def hello():
    print("world")
```

More text here."""
        is_valid, errors = check_code_block_balance(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_odd_code_blocks_fail(self):
        """Odd number of code fence markers fail."""
        content = """# Introduction

```python
def hello():
    pass
# Missing closing fence"""
        is_valid, errors = check_code_block_balance(content)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("unbalanced", errors[0].lower())

    def test_no_code_blocks_pass(self):
        """Content without code blocks passes."""
        content = """# Introduction

This is regular text without any code blocks.

## Section 2

More regular text."""
        is_valid, errors = check_code_block_balance(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_multiple_balanced_blocks_pass(self):
        """Multiple properly balanced code blocks pass."""
        content = """# Examples

```python
code1()
```

```javascript
code2();
```

```bash
echo "test"
```"""
        is_valid, errors = check_code_block_balance(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_empty_content_pass(self):
        """Empty content passes (no code blocks to check)."""
        content = ""
        is_valid, errors = check_code_block_balance(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class TestFrontmatterContamination(unittest.TestCase):
    """Test frontmatter contamination detection."""

    def test_clean_frontmatter_pass(self):
        """Valid frontmatter at start only passes."""
        content = """---
title: Test
tags: [test]
---

# Introduction

Content here."""
        is_valid, errors = check_frontmatter_contamination(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_duplicate_frontmatter_fail(self):
        """Duplicate frontmatter blocks fail."""
        content = """---
title: Original
---

# Content

---
title: Duplicate
---"""
        is_valid, errors = check_frontmatter_contamination(content)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("duplicate", errors[0].lower())

    def test_no_frontmatter_pass(self):
        """Content without frontmatter passes."""
        content = """# Introduction

Regular content without frontmatter."""
        is_valid, errors = check_frontmatter_contamination(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_horizontal_rules_not_flagged(self):
        """Horizontal rules (---) without YAML are not flagged."""
        content = """---
title: Test
---

# Section 1

---

# Section 2"""
        is_valid, errors = check_frontmatter_contamination(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class TestMinimumContent(unittest.TestCase):
    """Test minimum content length checks."""

    def test_sufficient_content_pass(self):
        """Content meeting minimum length passes."""
        content = "# Introduction\n\n" + "This is substantial content. " * 20
        is_valid, errors = check_minimum_content(content, min_length=100)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_insufficient_content_fail(self):
        """Content below minimum length fails."""
        content = "# Test\n\nShort."
        is_valid, errors = check_minimum_content(content, min_length=100)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("minimum", errors[0].lower())

    def test_empty_content_fail(self):
        """Empty content fails."""
        content = ""
        is_valid, errors = check_minimum_content(content, min_length=50)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_whitespace_only_fail(self):
        """Whitespace-only content fails."""
        content = "   \n\n   \n"
        is_valid, errors = check_minimum_content(content, min_length=50)
        self.assertFalse(is_valid)


class TestProseContent(unittest.TestCase):
    """Test prose content detection."""

    def test_substantial_prose_pass(self):
        """Content with substantial prose passes."""
        content = """---
title: Test
---

# Introduction

This document contains substantial prose content that explains the topic
in detail. There are complete sentences and paragraphs throughout.

## Details

More explanatory text here with proper sentence structure."""
        is_valid, errors = check_prose_content(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_code_only_fail(self):
        """Content that is mostly code fails."""
        content = """---
title: Test
---

```python
def func1():
    pass

def func2():
    pass

def func3():
    pass
```"""
        is_valid, errors = check_prose_content(content)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_minimal_prose_fail(self):
        """Content with minimal prose fails."""
        content = """---
title: Test
---

# Title

Test."""
        is_valid, errors = check_prose_content(content)
        self.assertFalse(is_valid)

    def test_balanced_content_pass(self):
        """Content with both code and prose passes."""
        content = """---
title: Test
---

# Introduction

This is a balanced document with both explanatory prose and code examples.
The prose provides context and explanation for the technical concepts.

```python
def example():
    return "code"
```

The code above demonstrates the concept we discussed."""
        is_valid, errors = check_prose_content(content)
        self.assertTrue(is_valid)


class TestTruncationDetection(unittest.TestCase):
    """Test truncation indicator detection."""

    def test_complete_content_pass(self):
        """Complete content without truncation indicators passes."""
        content = """---
title: Complete Document
---

# Introduction

This is a complete document with proper ending.

## Conclusion

Document ends properly."""
        is_valid, errors = check_truncation_indicators(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_ellipsis_at_end_fail(self):
        """Content ending with ... fails."""
        content = """# Introduction

This document appears to be truncated..."""
        is_valid, errors = check_truncation_indicators(content)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("truncat", errors[0].lower())

    def test_unfinished_sentence_fail(self):
        """Content with obviously unfinished sentence fails."""
        content = """# Introduction

This document contains substantial content but appears to be cut off mid-sent"""
        is_valid, errors = check_truncation_indicators(content)
        self.assertFalse(is_valid)

    def test_incomplete_code_block_fail(self):
        """Content ending with incomplete code block fails."""
        content = """# Example

```python
def incomplete_func():
    # Function appears to be cut off"""
        is_valid, errors = check_truncation_indicators(content)
        self.assertFalse(is_valid)

    def test_ellipsis_mid_content_pass(self):
        """Ellipsis in middle of content (not at end) passes."""
        content = """# Introduction

Here are some features... and more text follows.

## Conclusion

Document ends properly."""
        is_valid, errors = check_truncation_indicators(content)
        self.assertTrue(is_valid)


class TestJSONValidity(unittest.TestCase):
    """Test JSON validity checking for outline content."""

    def test_valid_json_pass(self):
        """Valid JSON outline passes."""
        outline = {
            "sections": [
                {"title": "Introduction", "content": "Overview"},
                {"title": "Details", "content": "More info"}
            ]
        }
        content = json.dumps(outline, indent=2)
        is_valid, errors = check_json_validity(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_invalid_json_fail(self):
        """Invalid JSON fails."""
        content = """{"sections": [{"title": "Test", "content": "Missing closing brace"}"""
        is_valid, errors = check_json_validity(content)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("json", errors[0].lower())

    def test_non_json_text_fail(self):
        """Non-JSON text fails."""
        content = "This is just regular text, not JSON"
        is_valid, errors = check_json_validity(content)
        self.assertFalse(is_valid)

    def test_empty_content_fail(self):
        """Empty content fails JSON validation."""
        content = ""
        is_valid, errors = check_json_validity(content)
        self.assertFalse(is_valid)

    def test_json_with_trailing_comma_fail(self):
        """JSON with syntax errors (trailing comma) fails."""
        content = """{"sections": [{"title": "Test",}]}"""
        is_valid, errors = check_json_validity(content)
        self.assertFalse(is_valid)


class TestValidateLLMResponse(unittest.TestCase):
    """Test comprehensive LLM response validation."""

    def test_valid_section_content_pass(self):
        """Valid section content passes all checks."""
        content = """---
title: Test Section
---

# Introduction

This is a well-formed section with substantial prose content that provides
detailed explanation of the topic at hand. It contains multiple sentences
and paragraphs that demonstrate proper technical writing structure and
format for generated content documents.

The section continues with additional context about the subject matter,
ensuring there is enough prose content to pass the minimum length and
structural sanity checks required by the validation pipeline.

```python
def example():
    return "code example"
```

The code above demonstrates the concept clearly and shows how Python
functions can be used effectively in documentation examples."""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_valid_outline_pass(self):
        """Valid JSON outline passes."""
        outline = {
            "sections": [
                {"title": "Introduction", "content": "Overview of the topic"},
                {"title": "Core Concepts", "content": "Key ideas"},
                {"title": "Examples", "content": "Practical demonstrations"}
            ]
        }
        content = json.dumps(outline, indent=2)
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="outline"
        )
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_unbalanced_code_blocks_fail(self):
        """Unbalanced code blocks fail validation."""
        content = """# Test

```python
def broken():
    pass
# Missing closing fence"""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_duplicate_frontmatter_fail(self):
        """Duplicate frontmatter fails validation."""
        content = """---
title: Original
---

# Content

---
title: Duplicate
---"""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_insufficient_content_fail(self):
        """Content below minimum length fails."""
        content = "# Test\n\nTiny."
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_truncated_content_fail(self):
        """Truncated content fails validation."""
        content = """# Introduction

This content appears to be cut off mid-sentence and never finishes prop..."""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_multiple_errors_detected(self):
        """Multiple validation failures detected together."""
        content = """---
title: Broken
---

# Test

Short.

```python
unclosed_code_block

---
title: Duplicate
---"""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 2)  # Multiple errors detected

    def test_full_document_type(self):
        """Full document type applies all checks."""
        content = """---
title: Complete Document
---

# Introduction

This is a substantial introduction with detailed explanatory content
that provides context and background for the entire document. The purpose
of this document is to demonstrate proper content structure and validation
for the content generation pipeline.

## Core Concepts

More detailed prose explaining the key concepts in depth. This section
covers the fundamental principles that underpin the quality assurance
framework used to validate generated content. Understanding these concepts
is essential for producing high-quality technical documentation.

```python
def example():
    return "demonstration"
```

## Conclusion

Wrapping up with final thoughts and a comprehensive summary of the key
points discussed throughout this document."""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="full_document"
        )
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_unknown_content_type_uses_defaults(self):
        """Unknown content type uses default validation."""
        content = """# Test

Valid content with reasonable length and structure."""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="unknown_type"
        )
        # Should still validate basic structure
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)
        self.assertIsInstance(warnings, list)


class TestContentTypeHandling(unittest.TestCase):
    """Test content type specific validation."""

    def test_outline_requires_json(self):
        """Outline type requires valid JSON."""
        content = "This is markdown, not JSON"
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="outline"
        )
        self.assertFalse(is_valid)
        # Should have JSON validation error
        self.assertTrue(any("json" in e.lower() for e in errors))

    def test_section_requires_prose(self):
        """Section type requires prose content."""
        content = """---
title: Test
---

```python
# Just code, no prose
def func():
    pass
```"""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertFalse(is_valid)

    def test_full_document_strictest_checks(self):
        """Full document type has strictest validation."""
        content = """---
title: Test
---

# Short

Brief content."""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="full_document"
        )
        self.assertFalse(is_valid)
        # Should fail on insufficient content


class TestPerformanceBenchmarks(unittest.TestCase):
    """Test performance requirements (<15ms for 2KB, <25ms for 10KB)."""

    def test_performance_2kb_content(self):
        """Validation completes in <15ms for 2KB content."""
        # Generate realistic 2KB content
        content = """---
title: Performance Test
tags: [test]
---

# Introduction

""" + ("This is test content with reasonable prose. " * 40) + """

```python
def example():
    return "code"
```

## Conclusion

""" + ("More test content here. " * 20)

        # Verify size is approximately 2KB
        size_kb = len(content.encode('utf-8')) / 1024
        self.assertLess(size_kb, 3.0)  # Roughly 2KB

        # Benchmark validation
        start_time = time.perf_counter()
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert performance requirement
        self.assertLess(
            elapsed_ms, 15.0,
            f"2KB validation took {elapsed_ms:.2f}ms (target: <15ms)"
        )

    def test_performance_10kb_content(self):
        """Validation completes in <25ms for 10KB content."""
        # Generate realistic 10KB content
        content = """---
title: Large Performance Test
tags: [test, performance]
---

# Introduction

""" + ("This is substantial test content with detailed prose. " * 150) + """

## Section 1

""" + ("More detailed content here. " * 100) + """

```python
def complex_example():
    data = [i for i in range(100)]
    return sum(data)
```

## Section 2

""" + ("Additional prose content. " * 100) + """

## Conclusion

""" + ("Final thoughts and summary. " * 50)

        # Verify size is approximately 10KB
        size_kb = len(content.encode('utf-8')) / 1024
        self.assertGreater(size_kb, 8.0)
        self.assertLess(size_kb, 16.0)

        # Benchmark validation
        start_time = time.perf_counter()
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert performance requirement
        self.assertLess(
            elapsed_ms, 25.0,
            f"10KB validation took {elapsed_ms:.2f}ms (target: <25ms)"
        )

    def test_performance_large_content_50kb(self):
        """Validation handles large content (50KB+) gracefully."""
        # Generate large 50KB content
        content = """---
title: Very Large Document
---

# Introduction

""" + ("Substantial prose content repeated many times. " * 1000)

        # Verify size is approximately 50KB
        size_kb = len(content.encode('utf-8')) / 1024
        self.assertGreater(size_kb, 45.0)

        # Benchmark validation (should still be reasonable)
        start_time = time.perf_counter()
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="full_document"
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should complete in reasonable time (relaxed for large content)
        self.assertLess(
            elapsed_ms, 100.0,
            f"50KB validation took {elapsed_ms:.2f}ms (should be <100ms)"
        )


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_content(self):
        """Empty content is handled gracefully."""
        content = ""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_whitespace_only_content(self):
        """Whitespace-only content is rejected."""
        content = "   \n\n   \n   "
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertFalse(is_valid)

    def test_very_large_content(self):
        """Very large content (100KB+) is handled."""
        content = "# Test\n\n" + ("Content. " * 15000)

        # Should not crash or timeout
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        self.assertIsInstance(is_valid, bool)

    def test_unicode_content(self):
        """Unicode content is handled correctly."""
        content = """---
title: Unicode Test
---

# 介绍

这是中文内容。This is a mix of Unicode and ASCII content that demonstrates
proper handling of international characters and multilingual text throughout
the validation pipeline. The system should handle all Unicode code points
correctly without errors or encoding issues.

## Emoji Section

Content with emoji 🚀 and special characters: é, ñ, ü. This section
contains additional prose to ensure the content meets minimum length
requirements for structural validation checks. International content
should be treated equally to ASCII-only content in all quality metrics.

## Technical Details

The validation system processes content byte-by-byte and character-by-character
to ensure structural integrity regardless of character encoding or language.

```python
def test():
    return "✓ success"
```"""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        # Should handle unicode without errors
        self.assertTrue(is_valid)

    def test_malformed_frontmatter(self):
        """Malformed frontmatter is detected."""
        content = """---
title: Test
this is not valid yaml syntax {}[]
---

# Content

Valid content below."""
        is_valid, errors, warnings = validate_llm_response(
            content=content,
            content_type="section"
        )
        # May have warnings about frontmatter
        # but content structure should still validate
        self.assertIsInstance(is_valid, bool)


if __name__ == "__main__":
    unittest.main()
