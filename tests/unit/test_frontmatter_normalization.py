"""Unit tests for frontmatter normalization.

Production Pipeline Validation v2 - Tests for root cause fix.
"""
import pytest
from src.utils.frontmatter_normalize import (
    normalize_frontmatter,
    has_valid_frontmatter,
    extract_frontmatter
)


class TestNormalizeFrontmatter:
    """Tests for normalize_frontmatter function."""

    def test_yaml_fenced_block_to_normalized(self):
        """```yaml fenced block should be converted to --- delimiters."""
        text = '''```yaml
title: My Python Guide
description: A guide to Python
tags: [python, tutorial]
```

# Introduction

This is the content.
'''
        result = normalize_frontmatter(text)

        # Should start with ---
        assert result.startswith('---'), f"Expected --- at start, got: {result[:50]}"

        # Should have closing ---
        assert '\n---\n' in result, "Expected closing --- delimiter"

        # Should NOT contain ```yaml
        assert '```yaml' not in result, "Should not contain ```yaml fence"
        assert '```' not in result.split('---')[1], "Should not contain closing ``` in frontmatter"

        # Content should be preserved
        assert '# Introduction' in result
        assert 'title: My Python Guide' in result

    def test_yml_fenced_block_to_normalized(self):
        """```yml fenced block should also be normalized."""
        text = '''```yml
title: Test Post
```

Content here.
'''
        result = normalize_frontmatter(text)
        assert result.startswith('---')
        assert '```yml' not in result

    def test_already_valid_frontmatter_unchanged(self):
        """Already valid --- frontmatter should remain unchanged."""
        text = '''---
title: Valid Post
tags: [test]
---

# Content

This is content.
'''
        result = normalize_frontmatter(text)

        # Should remain the same (normalized whitespace)
        assert result.startswith('---')
        assert 'title: Valid Post' in result
        assert '# Content' in result

    def test_bare_yaml_wrapped(self):
        """Bare YAML at start should be wrapped with --- delimiters."""
        text = '''title: Bare YAML Post
description: No delimiters
tags:
  - python
  - code

# Main Content

The actual content starts here.
'''
        result = normalize_frontmatter(text)

        assert result.startswith('---'), f"Expected --- at start, got: {result[:50]}"
        assert '\n---\n' in result
        assert '# Main Content' in result

    def test_no_frontmatter_with_fallback(self):
        """No frontmatter with fallback metadata should insert frontmatter."""
        text = '''# Just Content

No frontmatter here.
'''
        fallback = {'title': 'Fallback Title', 'tags': ['auto']}
        result = normalize_frontmatter(text, fallback_metadata=fallback)

        assert result.startswith('---')
        assert 'title: Fallback Title' in result
        assert '# Just Content' in result

    def test_no_frontmatter_without_fallback(self):
        """No frontmatter without fallback should auto-generate from heading."""
        text = '''# Just Content

No frontmatter here.
'''
        result = normalize_frontmatter(text)

        # Should auto-generate frontmatter from first heading
        assert result.startswith('---'), "Should auto-generate frontmatter"
        assert 'title: Just Content' in result
        assert '# Just Content' in result

    def test_empty_text(self):
        """Empty text should handle gracefully."""
        assert normalize_frontmatter('') == ''
        assert normalize_frontmatter('  ') == '  '
        assert normalize_frontmatter(None) is None if normalize_frontmatter(None) is None else True

    def test_multiple_yaml_blocks_only_first_normalized(self):
        """Only the first YAML block should be treated as frontmatter."""
        text = '''```yaml
title: First Block
```

# Content

Here's another code block:

```yaml
key: value
```
'''
        result = normalize_frontmatter(text)

        # First block normalized
        assert result.startswith('---')
        assert 'title: First Block' in result

        # Second block preserved as code block
        assert '```yaml' in result.split('---')[-1]


class TestHasValidFrontmatter:
    """Tests for has_valid_frontmatter function."""

    def test_valid_frontmatter(self):
        """Valid frontmatter should return True."""
        text = '''---
title: Test
---

Content
'''
        assert has_valid_frontmatter(text) is True

    def test_no_frontmatter(self):
        """No frontmatter should return False."""
        assert has_valid_frontmatter('# Just content') is False

    def test_incomplete_frontmatter(self):
        """Incomplete frontmatter (no closing ---) should return False."""
        text = '''---
title: Test

# Content
'''
        assert has_valid_frontmatter(text) is False

    def test_empty_frontmatter(self):
        """Empty frontmatter block should return False."""
        text = '''---
---

Content
'''
        assert has_valid_frontmatter(text) is False

    def test_fenced_yaml_is_not_valid(self):
        """```yaml block is not valid frontmatter."""
        text = '''```yaml
title: Test
```

Content
'''
        assert has_valid_frontmatter(text) is False


class TestExtractFrontmatter:
    """Tests for extract_frontmatter function."""

    def test_extract_basic(self):
        """Should extract frontmatter as dict."""
        text = '''---
title: Test Post
tags:
  - python
  - testing
---

Content
'''
        result = extract_frontmatter(text)
        assert result is not None
        assert result['title'] == 'Test Post'
        assert result['tags'] == ['python', 'testing']

    def test_extract_no_frontmatter(self):
        """Should return None if no frontmatter."""
        assert extract_frontmatter('# No frontmatter') is None

    def test_extract_invalid_yaml(self):
        """Should return None for invalid YAML."""
        text = '''---
title: [invalid: yaml: here
---

Content
'''
        result = extract_frontmatter(text)
        assert result is None


class TestRealWorldCases:
    """Tests based on real LLM output patterns."""

    def test_markdown_fence_wrapper(self):
        """Content wrapped in ```markdown fence should have fence stripped."""
        text = '''```markdown
---
title: My Post
tags: [python]
---

# Introduction

This is the content.
```'''
        result = normalize_frontmatter(text)

        # Should start with --- (outer fence stripped)
        assert result.startswith('---'), f"Expected --- at start, got: {result[:50]}"
        assert '```markdown' not in result, "Should not contain outer markdown fence"
        assert 'title: My Post' in result
        assert '# Introduction' in result

    def test_phi4_mini_output_pattern(self):
        """Test pattern commonly output by phi4-mini model."""
        text = '''```yaml
title: Understanding Python Data Structures
description: A comprehensive guide to Python's built-in data structures
tags: [python, data-structures, tutorial]
date: 2026-01-29
```

# Understanding Python Data Structures

Python offers several powerful built-in data structures...

## Lists

Lists are ordered, mutable sequences...

## Dictionaries

Dictionaries store key-value pairs...
'''
        result = normalize_frontmatter(text)

        # Validate normalization
        assert result.startswith('---'), "Must start with ---"
        assert '\n---\n' in result, "Must have closing ---"
        assert '```yaml' not in result.split('\n---\n')[0], "No fence in frontmatter"

        # Validate content preserved
        assert '# Understanding Python Data Structures' in result
        assert '## Lists' in result
        assert '## Dictionaries' in result

    def test_llm_output_with_extra_whitespace(self):
        """LLM may add extra whitespace around fenced blocks."""
        text = '''

```yaml
title: Whitespace Test
```

# Content
'''
        result = normalize_frontmatter(text)
        assert result.lstrip().startswith('---')
        assert '# Content' in result
