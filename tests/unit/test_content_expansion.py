"""Unit tests for content expansion utility.

Tests the ensure_minimum_size and expand_content functions to verify
they correctly expand short content to meet size requirements.
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.utils.content_expansion import needs_expansion, expand_content, ensure_minimum_size, TARGET_BYTES


def test_needs_expansion_short_content():
    """Short content should need expansion."""
    short_content = "---\ntitle: Test\n---\n\n# Heading\n\nShort content here."
    assert needs_expansion(short_content, min_bytes=1800)


def test_needs_expansion_long_content():
    """Long content should not need expansion."""
    # Create content > 2200 bytes
    long_content = "---\ntitle: Test\n---\n\n# Heading\n\n" + ("Lorem ipsum dolor sit amet. " * 100)
    assert not needs_expansion(long_content, min_bytes=TARGET_BYTES)


def test_expand_content_success():
    """Expansion should successfully increase content size."""
    short_content = """---
title: "Test Topic"
date: 2024-01-01
---

# Introduction

This is a short article about testing."""

    # Mock LLM service
    mock_llm = Mock()
    # Return expanded content that's larger
    expanded_body = short_content + "\n\n## Frequently Asked Questions\n\n" + ("Q: Question here? A: Answer here. " * 30)
    mock_llm.generate.return_value = expanded_body

    result = expand_content(
        content=short_content,
        llm_service=mock_llm,
        topic="Test Topic",
        target_bytes=TARGET_BYTES,
        max_attempts=2
    )

    # Verify expansion occurred
    assert len(result.encode('utf-8')) > len(short_content.encode('utf-8'))
    assert len(result.encode('utf-8')) >= TARGET_BYTES
    mock_llm.generate.assert_called_once()


def test_expand_content_preserves_frontmatter():
    """Expansion should preserve original frontmatter."""
    short_content = """---
title: "Important Title"
author: "Test Author"
tags: [test, important]
---

# Content

Short content."""

    # Mock LLM service
    mock_llm = Mock()
    expanded_body = short_content + "\n\n## Additional Section\n\n" + ("More content here. " * 50)
    mock_llm.generate.return_value = expanded_body

    result = expand_content(
        content=short_content,
        llm_service=mock_llm,
        topic="Important Title",
        target_bytes=TARGET_BYTES,
        max_attempts=2
    )

    # Verify frontmatter is preserved
    assert 'title: "Important Title"' in result or "title: 'Important Title'" in result
    assert "author: " in result or "author:" in result
    assert len(result.encode('utf-8')) >= TARGET_BYTES


def test_expand_content_multiple_attempts():
    """Expansion should retry if first attempt is insufficient."""
    short_content = """---
title: "Test"
---

# Short"""

    # Mock LLM service - first attempt returns still-short content, second succeeds
    mock_llm = Mock()
    first_response = short_content + "\n\n## Section\n\nSome text."
    second_response = first_response + "\n\n## Another Section\n\n" + ("More content here. " * 50)
    mock_llm.generate.side_effect = [first_response, second_response]

    result = expand_content(
        content=short_content,
        llm_service=mock_llm,
        topic="Test",
        target_bytes=TARGET_BYTES,
        max_attempts=2
    )

    # Verify multiple attempts were made
    assert mock_llm.generate.call_count == 2
    assert len(result.encode('utf-8')) >= TARGET_BYTES


def test_expand_content_failure_after_max_attempts():
    """Expansion should raise ValueError if max attempts exceeded."""
    short_content = """---
title: "Test"
---

# Short"""

    # Mock LLM service - always returns short content
    mock_llm = Mock()
    mock_llm.generate.return_value = short_content + "\n\n## Short section"

    with pytest.raises(ValueError) as exc_info:
        expand_content(
            content=short_content,
            llm_service=mock_llm,
            topic="Test",
            target_bytes=TARGET_BYTES,
            max_attempts=2
        )

    assert "Failed to expand content after" in str(exc_info.value)
    assert mock_llm.generate.call_count == 2


def test_ensure_minimum_size_no_expansion_needed():
    """Content meeting size requirement should not be expanded."""
    # Create content > 2200 bytes
    long_content = "---\ntitle: Test\n---\n\n# Heading\n\n" + ("Lorem ipsum dolor sit amet. " * 100)

    mock_llm = Mock()

    result = ensure_minimum_size(
        content=long_content,
        llm_service=mock_llm,
        topic="Test",
        min_bytes=TARGET_BYTES
    )

    # No expansion should occur
    assert result == long_content
    mock_llm.generate.assert_not_called()


def test_ensure_minimum_size_with_expansion():
    """Short content should be expanded to meet minimum."""
    short_content = """---
title: "Test"
---

# Short content"""

    mock_llm = Mock()
    expanded = short_content + "\n\n## FAQ\n\n" + ("Q: Question? A: Answer. " * 50)
    mock_llm.generate.return_value = expanded

    result = ensure_minimum_size(
        content=short_content,
        llm_service=mock_llm,
        topic="Test",
        min_bytes=TARGET_BYTES
    )

    assert len(result.encode('utf-8')) >= TARGET_BYTES
    mock_llm.generate.assert_called_once()
