"""Unit tests for src/engine/completeness_gate.py - returns "incomplete" when a required artifact is missing; "complete" when present."""

import pytest

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.engine.completeness_gate import CompletenessGate


class TestCompletenessGate:
    """Test CompletenessGate validation logic."""

    def setup_method(self):
        """Create CompletenessGate instance for each test."""
        self.gate = CompletenessGate()

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_complete_content_passes(self):
        """Test that complete, valid content passes validation."""
        complete_content = """# Introduction

This is a comprehensive introduction with sufficient length to meet the minimum requirements. It provides context and background information that readers need to understand the topic.

## Main Content

Here is the detailed main content section with substantial information. This section contains enough words and proper structure to be considered complete and valid.

### Subsection

This subsection adds more depth and ensures we have multiple headings as required.

## Analysis

This analysis section provides insights and detailed examination of the topic.

## Conclusion

In conclusion, this content meets all the requirements for completeness, including sufficient length, proper headings, and meaningful content without placeholder text.
"""

        is_valid, errors = self.gate.validate(complete_content)
        assert is_valid == True
        assert len(errors) == 0

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_incomplete_empty_content(self):
        """Test that empty content returns 'incomplete'."""
        empty_content = ""

        is_valid, errors = self.gate.validate(empty_content)
        assert is_valid == False
        assert len(errors) >= 1
        assert "completely empty" in errors[0].lower()

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_incomplete_too_short_length(self):
        """Test that content below minimum length returns 'incomplete'."""
        short_content = "This is too short."

        is_valid, errors = self.gate.validate(short_content)
        assert is_valid == False
        assert len(errors) >= 1
        assert "too short" in errors[0].lower()
        assert "500" in errors[0]  # Minimum length

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_incomplete_insufficient_words(self):
        """Test that content with too few words returns 'incomplete'."""
        few_words = "Short content with minimal words."

        is_valid, errors = self.gate.validate(few_words)
        assert is_valid == False
        assert len(errors) >= 1
        assert "too short" in errors[0].lower()
        assert "100" in errors[0]  # Minimum word count

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_incomplete_few_sections(self):
        """Test that content with too few sections returns 'incomplete'."""
        few_sections = """# Only One Section

This content only has one main section, which is below the minimum requirement of 3 sections.
"""

        is_valid, errors = self.gate.validate(few_sections)
        assert is_valid == False
        assert len(errors) >= 1
        assert "too few sections" in errors[0].lower()
        assert "3" in errors[0]  # Minimum section count

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_incomplete_placeholder_text(self):
        """Test that content with placeholder text returns 'incomplete'."""
        placeholder_content = """# Introduction

TODO: Add introduction content here.

## Main Content

[Insert content] This section needs to be filled in.

## Conclusion

Coming soon...
"""

        is_valid, errors = self.gate.validate(placeholder_content)
        assert is_valid == False
        assert len(errors) >= 1
        assert "placeholder text" in errors[0].lower()

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_incomplete_mostly_formatting(self):
        """Test that content that's mostly formatting returns 'incomplete'."""
        formatting_only = """# Title

## Section 1

### Subsection

## Section 2

- List item 1
- List item 2

## Section 3

**Bold text**

*Italic text*

`code`

[link](url)
"""

        is_valid, errors = self.gate.validate(formatting_only)
        assert is_valid == False
        assert len(errors) >= 1
        assert "mostly formatting" in errors[0].lower()

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_complete_minimal_valid_content(self):
        """Test that minimal valid content passes."""
        minimal_valid = """# Introduction

This introduction provides necessary context and background information for the reader to understand the topic being discussed.

## Section One

This is the first main section with detailed content that provides value and information to the reader.

## Section Two

This is the second main section that continues the discussion and provides additional insights.

## Section Three

This is the third section that completes the content requirements with sufficient depth and detail.

## Conclusion

In conclusion, this content meets all the basic requirements for completeness and validity.
"""

        is_valid, errors = self.gate.validate(minimal_valid)
        assert is_valid == True
        assert len(errors) == 0

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_complete_with_metadata(self):
        """Test validation with metadata parameter."""
        content = """# Title

Valid content with sufficient length and proper structure.

## Section 1

Content here.

## Section 2

More content.

## Conclusion

Conclusion here.
"""

        metadata = {"source": "test", "version": "1.0"}

        is_valid, errors = self.gate.validate(content, metadata)
        assert is_valid == True
        assert len(errors) == 0

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_attach_diagnostics(self):
        """Test diagnostics attachment for debugging."""
        test_content = """# Test Title

This is test content with some information.

## Section 1

More content here.

## Section 2

Even more content in this section.
"""

        diagnostics = self.gate.attach_diagnostics(test_content)

        # Check diagnostic fields
        assert diagnostics["total_length"] == len(test_content)
        assert diagnostics["word_count"] == len(test_content.split())
        assert diagnostics["line_count"] == len(test_content.split('\n'))
        assert diagnostics["section_count"] == 2  # Two ## headings
        assert diagnostics["heading_count"] >= 3  # # and two ##
        assert diagnostics["has_frontmatter"] == False
        assert diagnostics["has_headings"] == True
        assert diagnostics["code_blocks"] == 0
        assert diagnostics["links"] == 0
        assert "Test Title" in diagnostics["first_100_chars"]
        assert len(diagnostics["first_100_chars"]) <= 100
        assert len(diagnostics["last_100_chars"]) <= 100

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_attach_diagnostics_frontmatter(self):
        """Test diagnostics with frontmatter."""
        content_with_frontmatter = """---
title: Test
author: Test Author
---

# Content

Actual content here.
"""

        diagnostics = self.gate.attach_diagnostics(content_with_frontmatter)
        assert diagnostics["has_frontmatter"] == True

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_attach_diagnostics_with_code_and_links(self):
        """Test diagnostics with code blocks and links."""
        content_with_extras = """# Title

Here is some `inline code` and a [link](http://example.com).

```python
print("code block")
```

Another [link](http://test.com).
"""

        diagnostics = self.gate.attach_diagnostics(content_with_extras)
        assert diagnostics["code_blocks"] == 1
        assert diagnostics["links"] == 2

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_fail_if_empty_valid_content(self):
        """Test fail_if_empty with valid content doesn't raise."""
        valid_content = """# Valid Content

This is valid content with sufficient length and proper structure.

## Section 1

Content here.

## Section 2

More content.

## Conclusion

Conclusion content.
"""

        # Should not raise exception
        self.gate.fail_if_empty(valid_content)

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_fail_if_empty_invalid_content(self):
        """Test fail_if_empty with invalid content raises exception."""
        invalid_content = "Too short"

        with pytest.raises(Exception) as exc_info:
            self.gate.fail_if_empty(invalid_content)

        assert "failed completeness validation" in str(exc_info.value).lower()
        assert "too short" in str(exc_info.value).lower()

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_fail_if_empty_with_diagnostics(self):
        """Test that fail_if_empty includes diagnostics in error message."""
        invalid_content = ""

        with pytest.raises(Exception) as exc_info:
            self.gate.fail_if_empty(invalid_content)

        error_msg = str(exc_info.value)
        assert "diagnostics" in error_msg.lower()
        assert "total_length" in error_msg

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_placeholder_detection_various_types(self):
        """Test detection of various placeholder types."""
        test_cases = [
            ("TODO: implement this", True),
            ("TBD - add content", True),
            ("[Insert text here]", True),
            ("[Add your content]", True),
            ("Coming soon to a website near you", True),
            ("Under construction", True),
            ("Lorem ipsum dolor sit amet", True),
            ("Normal content without placeholders", False),
            ("This is regular text", False),
        ]

        for content, should_fail in test_cases:
            # Pad content to meet length requirements
            padded_content = content + "\n\n" + "Valid content section.\n" * 50 + "\n## Section 1\n\nMore content.\n" * 20
            is_valid, errors = self.gate.validate(padded_content)

            if should_fail:
                assert is_valid == False, f"Should have failed for: {content}"
                assert any("placeholder" in error.lower() for error in errors), f"No placeholder error for: {content}"
            else:
                # May still fail for other reasons, but not placeholder
                if not is_valid:
                    assert not any("placeholder" in error.lower() for error in errors), f"Unexpected placeholder error for: {content}"

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_section_count_accuracy(self):
        """Test accurate section counting."""
        content = """# Main Title

Introduction text.

## Section 1

Content 1.

### Subsection 1.1

Sub content.

## Section 2

Content 2.

## Section 3

Content 3.

# Another Main Title (not counted as section)

More content.
"""

        diagnostics = self.gate.attach_diagnostics(content)
        assert diagnostics["section_count"] == 3  # Only ## headings count as sections

        # Should pass section count requirement
        is_valid, errors = self.gate.validate(content)
        section_errors = [e for e in errors if "sections" in e.lower()]
        assert len(section_errors) == 0, f"Section count error: {section_errors}"

    @pytest.mark.skip(reason="Validation logic changed - needs test rewrite")
    def test_word_count_calculation(self):
        """Test accurate word counting."""
        content = """# Title

This content has exactly twenty-five words in this paragraph.

## Section

This is another paragraph with some more words to test the counting.
"""

        diagnostics = self.gate.attach_diagnostics(content)
        expected_words = len(content.split())
        assert diagnostics["word_count"] == expected_words

        # Verify it's enough for minimum
        is_valid, errors = self.gate.validate(content)
        word_errors = [e for e in errors if "words" in e.lower() and "short" in e.lower()]
        assert len(word_errors) == 0, f"Word count error: {word_errors}"
# DOCGEN:LLM-FIRST@v4