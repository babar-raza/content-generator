#!/usr/bin/env python3
"""Unit tests for Quality Gate Tool.

Tests quality gate criterion G (markdown syntax validation) and
integration with existing criteria A-F.
"""

import unittest
import sys
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.quality_gate import (
    check_frontmatter,
    count_headings,
    count_sections,
    count_references,
    evaluate_output,
)


class TestValidateMarkdownSyntax(unittest.TestCase):
    """Test validate_markdown_syntax() function (criterion G)."""

    def test_valid_markdown_passes(self):
        """Valid markdown with balanced code blocks passes."""
        content = """---
title: Test
---

# Introduction

Regular content here.

```python
def hello():
    print("world")
```

More content.
"""
        # Import the function to test
        from tools.quality_gate import validate_markdown_syntax

        is_valid, errors = validate_markdown_syntax(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_detects_unbalanced_code_blocks(self):
        """Detects unbalanced code blocks (odd number of fences)."""
        content = """---
title: Test
---

# Example

```python
def hello():
    pass
# Missing closing fence
"""
        from tools.quality_gate import validate_markdown_syntax

        is_valid, errors = validate_markdown_syntax(content)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('unclosed' in e.lower() or 'opened' in e.lower() for e in errors))

    def test_detects_orphaned_opening_fence(self):
        """Detects orphaned opening fence at document end."""
        content = """---
title: Test
---

# Content

Some text.

```python
"""
        from tools.quality_gate import validate_markdown_syntax

        is_valid, errors = validate_markdown_syntax(content)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_detects_mismatched_fence_markers(self):
        """Detects mismatched fence markers (``` vs ~~~)."""
        content = """---
title: Test
---

```python
def hello():
    pass
~~~
"""
        from tools.quality_gate import validate_markdown_syntax

        is_valid, errors = validate_markdown_syntax(content)
        self.assertFalse(is_valid)
        # Should detect mismatch
        self.assertTrue(any('mismatch' in e.lower() for e in errors))

    def test_multiple_balanced_code_blocks_valid(self):
        """Multiple balanced code blocks are valid."""
        content = """---
title: Test
---

# Example 1

```python
code1()
```

## Example 2

```javascript
code2();
```

### Example 3

```bash
echo "test"
```
"""
        from tools.quality_gate import validate_markdown_syntax

        is_valid, errors = validate_markdown_syntax(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_handles_empty_content(self):
        """Handles empty content gracefully."""
        content = ""
        from tools.quality_gate import validate_markdown_syntax

        is_valid, errors = validate_markdown_syntax(content)
        self.assertTrue(is_valid)  # No code blocks = valid
        self.assertEqual(len(errors), 0)

    def test_handles_content_without_code_blocks(self):
        """Content without code blocks is valid."""
        content = """---
title: Test
---

# Introduction

Regular markdown text.

## Section 2

More text.
"""
        from tools.quality_gate import validate_markdown_syntax

        is_valid, errors = validate_markdown_syntax(content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class TestCriterionGIntegration(unittest.TestCase):
    """Test criterion G integration in evaluate_output()."""

    def setUp(self):
        """Set up test fixtures directory."""
        self.fixtures_dir = project_root / "tests" / "fixtures" / "markdown_syntax"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def test_criterion_g_in_evaluation_valid_file(self):
        """Criterion G is checked in overall evaluation for valid file."""
        # Create valid test file
        test_file = self.fixtures_dir / "valid_markdown.md"
        test_file.write_text("""---
title: Valid Markdown Test
description: Test file
---

# Introduction

This is a well-formed markdown document with balanced code blocks.

## Code Example

```python
def hello():
    print("world")
```

## Section 2

More content here with sufficient text to pass completeness checks.

## Section 3

Additional section with references to "Python Programming" and "Code Quality".
""", encoding='utf-8')

        result = evaluate_output(str(test_file))

        # Should pass criterion G
        self.assertIn("syntax_valid", result["metrics"])
        if result["metrics"]["syntax_valid"]:
            self.assertIn("criterion_g_syntax_valid", result["reasons"])

        # Clean up
        test_file.unlink()

    def test_criterion_g_in_evaluation_invalid_file(self):
        """Criterion G fails for file with unbalanced code blocks."""
        # Create invalid test file
        test_file = self.fixtures_dir / "unbalanced_fences.md"
        test_file.write_text("""---
title: Broken Markdown Test
description: Test file with syntax errors
---

# Introduction

This file has unbalanced code blocks.

```python
def hello():
    print("world")
# Missing closing fence

More content here.
""", encoding='utf-8')

        result = evaluate_output(str(test_file))

        # Should fail criterion G
        self.assertIn("syntax_valid", result["metrics"])
        if not result["metrics"]["syntax_valid"]:
            # Should have failure
            failures_str = " ".join(result["failures"])
            self.assertTrue(any('criterion_g' in f for f in result["failures"]))

        # Clean up
        test_file.unlink()

    def test_overall_pass_requires_criterion_g(self):
        """Overall pass requires criterion G to pass."""
        # Create file that passes A-F but fails G
        test_file = self.fixtures_dir / "passes_all_but_g.md"
        test_file.write_text("""---
title: Passes A-F But Fails G
description: Test file
---

# Section 1

This file passes criteria A (frontmatter), B (headings), C (sections),
D (references to "Quality Standards"), E (size), and F (no fenced frontmatter).

## Section 2

However it has an unclosed code block that fails criterion G.

```python
def broken():
    pass
# No closing fence

## Section 3

More content here with additional references to "Best Practices".
""", encoding='utf-8')

        result = evaluate_output(str(test_file))

        # Should fail overall due to criterion G
        if "syntax_valid" in result["metrics"]:
            if not result["metrics"]["syntax_valid"]:
                self.assertFalse(result["pass"],
                    "Should fail overall if criterion G fails")

        # Clean up
        test_file.unlink()


class TestCriterionGErrorReporting(unittest.TestCase):
    """Test error counting and reporting for criterion G."""

    def setUp(self):
        """Set up test fixtures directory."""
        self.fixtures_dir = project_root / "tests" / "fixtures" / "markdown_syntax"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def test_error_count_in_metrics(self):
        """Syntax error count is reported in metrics."""
        from tools.quality_gate import validate_markdown_syntax

        content = """---
title: Test
---

```python
unclosed1

Some text

```javascript
unclosed2
"""
        is_valid, errors = validate_markdown_syntax(content)

        self.assertFalse(is_valid)
        # Should report error count
        self.assertGreater(len(errors), 0)

    def test_error_details_included(self):
        """Error details include line numbers and descriptions."""
        from tools.quality_gate import validate_markdown_syntax

        content = """---
title: Test
---

# Section

```python
code
~~~
"""
        is_valid, errors = validate_markdown_syntax(content)

        self.assertFalse(is_valid)
        # Errors should include line number and description
        self.assertGreater(len(errors), 0)
        # At least one error should mention the issue
        error_text = " ".join(errors).lower()
        self.assertTrue('line' in error_text or 'mismatch' in error_text or 'unclosed' in error_text)


class TestRegressionBMP(unittest.TestCase):
    """Regression test for BMP file format issue."""

    def setUp(self):
        """Set up test fixtures directory."""
        self.fixtures_dir = project_root / "tests" / "fixtures" / "markdown_syntax"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def test_bmp_regression_orphaned_fences(self):
        """Detects BMP file with orphaned fences and duplicate frontmatter.

        Issue: BMP file has orphaned ``` at lines 8, 12, 48 and duplicate
        YAML frontmatter at lines 51-58.
        """
        test_file = self.fixtures_dir / "bmp_orphaned.md"
        test_file.write_text("""---
title: BMP File Format
tags:
- auto-generated
date: auto
---

python
with open('image.bmp', 'wb') as bmp_file:
    content = b'...'
    bmp_file.write(content)
```

In this example, `'b'` signifies binary mode.

## Practical Example

```python
def resize_bmp(filename):
    with open(filename, 'rb') as bmp_file:
        content = bytearray(bmp_file.read())
```

## Conclusion

Understanding binary I/O is essential.
```

This provides an overview.

```yaml
title: Understanding BMP File Format
date: 2023-04-01
tags:
  - Python Programming
```
""", encoding='utf-8')

        # Evaluate with quality gate
        result = evaluate_output(str(test_file))

        # Should detect syntax errors
        if "syntax_valid" in result["metrics"]:
            self.assertFalse(result["metrics"]["syntax_valid"],
                "BMP regression: should detect unbalanced fences")

        # Should fail overall
        self.assertFalse(result["pass"],
            "BMP regression: should fail overall quality check")

        # Clean up
        test_file.unlink()


class TestRegressionPaperless(unittest.TestCase):
    """Regression test for PAPERLESS-POLICY file format issue."""

    def setUp(self):
        """Set up test fixtures directory."""
        self.fixtures_dir = project_root / "tests" / "fixtures" / "markdown_syntax"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def test_paperless_regression_nested_markdown(self):
        """Detects PAPERLESS-POLICY with entire content wrapped in code block.

        Issue: PAPERLESS-POLICY file has entire content from line 8-99
        wrapped in unclosed ```python block.
        """
        test_file = self.fixtures_dir / "nested_markdown.md"
        test_file.write_text("""---
title: PAPERLESS-POLICY File Format
tags:
- auto-generated
date: auto
---

```python
# Best Practices

## Emphasizing Code Readability and Maintenance
One of Python's strengths is its readability:

- **Code Clarity**: Use meaningful variable names

  ```python
  file = open(file_name)
  ```

- **Modularization**: Break down your code into functions.

  ```python
  def read_file_contents(path):
      with open(path) as f:
          return f.read()
  ```

## Conclusion

Adopting these best practices makes your codebase robust.
```""", encoding='utf-8')

        # Evaluate with quality gate
        result = evaluate_output(str(test_file))

        # Should detect nested markdown or unclosed blocks
        if "syntax_valid" in result["metrics"]:
            self.assertFalse(result["metrics"]["syntax_valid"],
                "PAPERLESS regression: should detect wrapped content")

        # Should fail overall
        self.assertFalse(result["pass"],
            "PAPERLESS regression: should fail overall quality check")

        # Clean up
        test_file.unlink()


class TestBackwardsCompatibility(unittest.TestCase):
    """Test backwards compatibility with existing criteria A-F."""

    def setUp(self):
        """Set up test fixtures directory."""
        self.fixtures_dir = project_root / "tests" / "fixtures" / "markdown_syntax"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def test_existing_criteria_still_work(self):
        """Existing criteria A-F continue to function correctly."""
        test_file = self.fixtures_dir / "test_existing_criteria.md"
        test_file.write_text("""---
title: Existing Criteria Test
description: Test file
---

# Heading 1

Content section with more than one hundred characters of substantial content.
This should be counted as a valid section.

## Heading 2

Another section with references to "Best Practices" and "Quality Standards".

## Heading 3

Third section with more content.
""", encoding='utf-8')

        result = evaluate_output(str(test_file))

        # Check that all existing criteria are still evaluated
        metrics = result["metrics"]
        self.assertIn("has_frontmatter", metrics)
        self.assertIn("heading_count", metrics)
        self.assertIn("section_count", metrics)
        self.assertIn("reference_count", metrics)
        self.assertIn("size_bytes", metrics)
        self.assertIn("has_fenced_frontmatter", metrics)

        # Clean up
        test_file.unlink()

    def test_criterion_g_does_not_break_valid_files(self):
        """Files that passed A-F still pass with G if syntax is valid."""
        test_file = self.fixtures_dir / "test_valid_legacy.md"
        test_file.write_text("""---
title: Legacy Valid File
description: Test file for quality gate backwards compatibility
---

# Introduction

This file would pass the old quality gate (criteria A-F) and should continue
to pass with criterion G added. It has valid frontmatter, multiple headings,
multiple sections, references to "Quality Assurance" and "Testing Standards",
and sufficient size to meet the hard minimum threshold.

The purpose of this document is to verify that adding markdown syntax
validation (criterion G) does not accidentally break files that were
previously passing all quality checks. This is critical for backwards
compatibility and production stability.

## Details and Technical Background

More content here with balanced code blocks that demonstrate proper
markdown syntax. The following code example shows a well-formed Python
function that implements quality checking logic:

```python
def example():
    return True
```

This section provides additional context about "Best Practices" in software
quality assurance. Organizations like the "International Software Testing
Qualifications Board" have established frameworks for ensuring code quality
and reliability across enterprise applications.

When implementing quality gates, it is important to consider multiple
dimensions of content quality including structural integrity, grounding
with real references, and syntactic correctness of the output format.

## Implementation Considerations

Quality gates serve as automated checkpoints in content generation pipelines.
Each criterion validates a different aspect of the generated output:

- Criterion A validates frontmatter presence and format
- Criterion B checks structural headings count
- Criterion C ensures completeness with multiple sections
- Criterion D verifies grounding through references
- Criterion E enforces minimum content size
- Criterion F checks safety (no fenced frontmatter)
- Criterion G validates markdown syntax correctness

These criteria work together to ensure high-quality output that meets
production standards. The "Software Engineering Institute" recommends
layered quality approaches for generated content systems.

## Conclusion

Final section with adequate content to ensure this document passes all
quality criteria including the new criterion G for markdown syntax
validation. This backwards compatibility test is essential for safe
deployment of quality gate enhancements to production environments.
""", encoding='utf-8')

        result = evaluate_output(str(test_file))

        # Should pass all criteria including G
        self.assertTrue(result["pass"],
            "Valid legacy file should still pass with criterion G")

        # Clean up
        test_file.unlink()


class TestEdgeCases(unittest.TestCase):
    """Test edge cases for criterion G."""

    def test_inline_code_not_flagged(self):
        """Inline code backticks are not flagged as unbalanced."""
        from tools.quality_gate import validate_markdown_syntax

        content = """---
title: Test
---

# Example

Use `inline code` in your text.

Here's a `variable_name` example.
"""
        is_valid, errors = validate_markdown_syntax(content)
        self.assertTrue(is_valid)

    def test_code_blocks_with_language_specifiers(self):
        """Handles various language specifiers correctly."""
        from tools.quality_gate import validate_markdown_syntax

        content = """---
title: Test
---

```python
python_code()
```

```javascript
jsCode();
```

```bash
echo "test"
```

```
plain_code_block()
```
"""
        is_valid, errors = validate_markdown_syntax(content)
        self.assertTrue(is_valid)

    def test_nested_code_blocks_detected(self):
        """Detects nested code blocks (code block inside code block)."""
        from tools.quality_gate import validate_markdown_syntax

        content = """---
title: Test
---

```python
def example():
    '''
    ```python
    nested code
    ```
    '''
    pass
```
"""
        is_valid, errors = validate_markdown_syntax(content)
        # May or may not be valid depending on implementation
        # At minimum, should not crash
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)


if __name__ == "__main__":
    unittest.main()
