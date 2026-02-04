"""Unit tests for frontmatter enforcement.

Tests the enforce_frontmatter function to ensure it can handle various
malformed frontmatter cases and always produces valid YAML.
"""
import pytest
import yaml
from src.utils.frontmatter_normalize import enforce_frontmatter, has_valid_frontmatter


def test_enforce_with_valid_frontmatter():
    """Valid frontmatter should pass through unchanged."""
    content = """---
title: Test Post
date: 2024-01-01
tags: [python, testing]
---

# Content Here"""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)
    assert result == content


def test_enforce_with_yaml_fence():
    """```yaml fences should be converted to --- delimiters."""
    content = """```yaml
title: Test Post
date: 2024-01-01
tags: [python]
```

# Content Here"""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)
    assert result.startswith('---')
    assert '```yaml' not in result


def test_enforce_with_invalid_yaml_missing_colon():
    """Invalid YAML (missing colon) should be repaired with minimal frontmatter."""
    content = """---
title Test Post
date: 2024-01-01
---

# Content Here"""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)

    # Verify YAML is parseable
    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    yaml_content = '\n'.join(lines[1:yaml_end])
    parsed = yaml.safe_load(yaml_content)
    assert parsed is not None
    assert isinstance(parsed, dict)
    assert 'title' in parsed


def test_enforce_with_invalid_yaml_bad_syntax():
    """YAML with syntax errors should be repaired."""
    content = """---
title: Test Post
invalid_array: [missing, close, bracket
date: 2024-01-01
---

# Content Here"""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)

    # Verify YAML is parseable
    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    yaml_content = '\n'.join(lines[1:yaml_end])
    parsed = yaml.safe_load(yaml_content)
    assert parsed is not None
    assert isinstance(parsed, dict)


def test_enforce_with_no_frontmatter():
    """Content with no frontmatter should get minimal frontmatter added."""
    content = "# My Article\n\nSome content here"

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)
    assert result.startswith('---')

    # Should extract title from heading
    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    yaml_content = '\n'.join(lines[1:yaml_end])
    parsed = yaml.safe_load(yaml_content)
    assert 'title' in parsed
    assert 'My Article' in parsed['title']


def test_enforce_with_markdown_fence_wrapper():
    """Content wrapped in ```markdown fence should be unwrapped and fixed."""
    content = """```markdown
---
title: Test
---
# Content
```"""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)
    assert '```markdown' not in result


def test_enforce_with_empty_content():
    """Empty content should get minimal frontmatter."""
    content = ""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)

    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    yaml_content = '\n'.join(lines[1:yaml_end])
    parsed = yaml.safe_load(yaml_content)
    assert parsed is not None
    assert 'title' in parsed


def test_enforce_with_fallback_metadata():
    """Fallback metadata should be used when provided."""
    content = "# Content without frontmatter"
    fallback = {
        'title': 'Fallback Title',
        'author': 'Test Author',
        'tags': ['test']
    }

    result = enforce_frontmatter(content, fallback_metadata=fallback)
    assert has_valid_frontmatter(result)

    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    yaml_content = '\n'.join(lines[1:yaml_end])
    parsed = yaml.safe_load(yaml_content)
    assert parsed['title'] == 'Fallback Title'


def test_enforce_preserves_body_content():
    """Body content should be preserved during repair."""
    content = """---
invalid yaml here
---

# Important Heading

This is important content that must be preserved.

## Another Section

More content here."""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)
    assert '# Important Heading' in result
    assert 'important content that must be preserved' in result
    assert '## Another Section' in result


def test_enforce_yaml_parseable():
    """All results must have parseable YAML."""
    test_cases = [
        "# Just content",
        "```yaml\ntitle: Test\n```\nContent",
        "---\nbad: yaml: syntax\n---\nContent",
        "---\ntitle\n---\nContent",  # Missing colon
        "",
        "Plain text with no structure at all",
    ]

    for content in test_cases:
        result = enforce_frontmatter(content)
        assert has_valid_frontmatter(result), f"Failed for: {content[:50]}"

        # Parse and validate YAML
        lines = result.split('\n')
        yaml_end = lines.index('---', 1)
        yaml_content = '\n'.join(lines[1:yaml_end])

        # This should not raise an exception
        parsed = yaml.safe_load(yaml_content)
        assert parsed is not None
        assert isinstance(parsed, dict)
        assert len(parsed) > 0


def test_enforce_with_trailing_backtick_on_delimiter():
    """Closing delimiter with trailing backtick (---`) should be sanitized."""
    content = """---
title: "How to Create ZIP File in Memory using C#"
date: '2023-04-01'
tags:
  - .NET Standard
  - Compression Libraries
---`
## Introduction

Creating a zip file directly from memory is an essential operation."""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)

    # Verify YAML is parseable
    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    yaml_content = '\n'.join(lines[1:yaml_end])
    parsed = yaml.safe_load(yaml_content)
    assert parsed is not None
    assert isinstance(parsed, dict)
    assert parsed['title'] == 'How to Create ZIP File in Memory using C#'

    # Verify closing delimiter is clean (no backtick)
    assert lines[yaml_end] == '---'
    assert lines[yaml_end] != '---`'


def test_enforce_with_trailing_fence_marker_on_delimiter():
    """Closing delimiter with trailing fence marker (--- ```) should be sanitized."""
    content = """---
title: "Test Post"
date: '2023-04-01'
--- ```
## Content Here"""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)

    # Verify closing delimiter is clean
    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    assert lines[yaml_end] == '---'


def test_enforce_with_bom_before_delimiter():
    """BOM or whitespace before opening delimiter should be stripped."""
    content = "\ufeff  ---\ntitle: Test\ndate: 2024-01-01\n---\n\n# Content"

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)
    assert result.startswith('---')

    # Verify YAML is parseable
    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    yaml_content = '\n'.join(lines[1:yaml_end])
    parsed = yaml.safe_load(yaml_content)
    assert parsed is not None
    assert isinstance(parsed, dict)


def test_enforce_with_double_opening_delimiter():
    """Double --- at start (malformed: ---\n---\ntitle:) should be fixed."""
    content = """---
---
title: Test Post
date: 2024-01-01
---

# Content Here"""

    result = enforce_frontmatter(content)
    assert has_valid_frontmatter(result)

    # Verify YAML is parseable
    lines = result.split('\n')
    yaml_end = lines.index('---', 1)
    yaml_content = '\n'.join(lines[1:yaml_end])
    parsed = yaml.safe_load(yaml_content)
    assert parsed is not None
    assert isinstance(parsed, dict)
    assert parsed['title'] == 'Test Post'


def test_sanitize_delimiter_idempotency():
    """Running enforce_frontmatter twice should not change the output."""
    content = """---
title: "Test Post"
date: '2023-04-01'
---`
## Content Here"""

    result1 = enforce_frontmatter(content)
    result2 = enforce_frontmatter(result1)

    assert result1 == result2
    assert has_valid_frontmatter(result2)
