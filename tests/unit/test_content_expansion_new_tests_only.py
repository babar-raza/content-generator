"""Additional tests for deterministic fallback expansion."""
import pytest
from unittest.mock import Mock


def test_deterministic_fallback_expansion():
    """Test that deterministic fallback always succeeds and meets target."""
    from src.utils.content_expansion import deterministic_fallback_expansion

    # Very short content
    short_content = """---
title: "Test"
---

Short body."""

    result = deterministic_fallback_expansion(
        content=short_content,
        topic="Test Topic",
        target_bytes=2200
    )

    # Verify size
    result_bytes = len(result.encode('utf-8'))
    assert result_bytes >= 2200, f"Expected >= 2200 bytes, got {result_bytes}"

    # Verify frontmatter preserved
    assert result.startswith('---')
    assert 'title: "Test"' in result

    # Verify original body preserved
    assert 'Short body' in result


def test_deterministic_fallback_without_llm():
    """Test ensure_minimum_size with llm_service=None uses fallback."""
    from src.utils.content_expansion import ensure_minimum_size

    short_content = """---
title: "Test"
---

Minimal content here."""

    # Call with llm_service=None to force deterministic fallback
    result = ensure_minimum_size(
        content=short_content,
        llm_service=None,  # Force fallback
        topic="Test Topic",
        min_bytes=2200
    )

    result_bytes = len(result.encode('utf-8'))
    assert result_bytes >= 2200, f"Expected >= 2200 bytes, got {result_bytes}"
    assert 'title: "Test"' in result
    assert 'Minimal content here' in result


def test_ensure_minimum_size_llm_fails_uses_fallback():
    """Test that LLM failure triggers deterministic fallback."""
    from src.utils.content_expansion import ensure_minimum_size

    # Create a mock LLM that always fails
    mock_llm = Mock()
    mock_llm.generate.side_effect = Exception("LLM service unavailable")

    short_content = """---
title: "Test"
---

Short."""

    # Should NOT raise - fallback handles it
    result = ensure_minimum_size(
        content=short_content,
        llm_service=mock_llm,
        topic="Test Topic",
        min_bytes=2200
    )

    result_bytes = len(result.encode('utf-8'))
    assert result_bytes >= 2200, f"Fallback should guarantee size, got {result_bytes}"
    assert 'Short' in result


def test_deterministic_fallback_idempotent():
    """Test that running fallback twice doesn't bloat endlessly."""
    from src.utils.content_expansion import deterministic_fallback_expansion

    content = """---
title: "Test"
---

Content."""

    # First expansion
    result1 = deterministic_fallback_expansion(content, "Topic", 2200)
    size1 = len(result1.encode('utf-8'))

    # Second expansion should be idempotent (return same content if already expanded)
    result2 = deterministic_fallback_expansion(result1, "Topic", 2200)
    size2 = len(result2.encode('utf-8'))

    # Should be exactly the same (idempotent)
    assert size2 == size1, f"Expansion not idempotent: {size1} → {size2}"
