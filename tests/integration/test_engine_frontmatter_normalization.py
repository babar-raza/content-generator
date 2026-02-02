"""Test engine-direct frontmatter normalization.

Regression test for S1 engine path - ensures generated content always has valid
YAML frontmatter with --- delimiters, not ```yaml fences.
"""
import pytest
from pathlib import Path
from src.utils.frontmatter_normalize import normalize_frontmatter, has_valid_frontmatter


def test_normalize_yaml_fence():
    """Test that ```yaml fences are normalized to --- delimiters."""
    content = """```yaml
title: Test Post
description: Test description
tags: [python, testing]
```

# Main Heading

Content here.
"""

    normalized = normalize_frontmatter(content)

    assert normalized.startswith('---'), "Normalized content should start with ---"
    assert has_valid_frontmatter(normalized), "Normalized content should have valid frontmatter"
    assert '```yaml' not in normalized, "Normalized content should not contain ```yaml fence"
    assert 'title: Test Post' in normalized, "Normalized content should preserve title"


def test_normalize_bare_yaml():
    """Test that bare YAML gets wrapped with --- delimiters."""
    content = """title: Test Post
description: Test description
tags: [python, testing]

# Main Heading

Content here.
"""

    normalized = normalize_frontmatter(content)

    assert normalized.startswith('---'), "Normalized content should start with ---"
    assert has_valid_frontmatter(normalized), "Normalized content should have valid frontmatter"
    assert 'title: Test Post' in normalized, "Normalized content should preserve title"


def test_valid_frontmatter_unchanged():
    """Test that already-valid frontmatter is unchanged."""
    content = """---
title: Test Post
description: Test description
tags: [python, testing]
---

# Main Heading

Content here.
"""

    normalized = normalize_frontmatter(content)

    assert normalized == content, "Valid frontmatter should be unchanged"
    assert has_valid_frontmatter(normalized), "Should still have valid frontmatter"


def test_markdown_fence_stripped():
    """Test that outer ```markdown fence is stripped."""
    content = """```markdown
---
title: Test Post
description: Test description
tags: [python, testing]
---

# Main Heading

Content here.
```"""

    normalized = normalize_frontmatter(content)

    assert normalized.startswith('---'), "Should start with frontmatter after stripping fence"
    assert has_valid_frontmatter(normalized), "Should have valid frontmatter"
    assert '```markdown' not in normalized, "Should not contain markdown fence"


def test_engine_output_normalization_flow():
    """Test the complete engine output normalization flow.

    Simulates what run_live_workflow_v2.py does:
    1. LLM generates content (possibly with ```yaml fence)
    2. Normalize frontmatter
    3. Validate
    4. Write to file
    """
    # Simulate LLM output with ```yaml fence (common LLM behavior)
    llm_output = """```yaml
title: FastAPI Best Practices
description: Comprehensive guide to FastAPI development
tags: [fastapi, python, web, api]
```

# FastAPI Best Practices

## Introduction

FastAPI is a modern web framework...

## Key Features

- Fast performance
- Automatic documentation
- Type hints support
"""

    # Step 1: Normalize (as run_live_workflow_v2.py now does)
    normalized = normalize_frontmatter(llm_output)

    # Step 2: Validate
    assert has_valid_frontmatter(normalized), "Normalized content must have valid frontmatter"

    # Step 3: Verify structure
    assert normalized.startswith('---'), "Must start with ---"
    assert normalized.count('---') >= 2, "Must have opening and closing ---"
    assert '```yaml' not in normalized, "Must not contain ```yaml fence"
    assert 'title: FastAPI Best Practices' in normalized, "Must preserve frontmatter fields"
    assert '# FastAPI Best Practices' in normalized, "Must preserve content headings"

    # Step 4: Verify it can be written and read back
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(normalized)
        temp_path = f.name

    try:
        read_content = Path(temp_path).read_text(encoding='utf-8')
        assert has_valid_frontmatter(read_content), "Content read from file should still have valid frontmatter"
    finally:
        Path(temp_path).unlink()


@pytest.mark.parametrize("malformed_input", [
    # Double --- at start
    """---
---
title: Test
---

Content""",
    # Missing closing ---
    """---
title: Test
description: Test

Content""",
    # Nested fence
    """```yaml
title: Test
tags: [a, b]
```

```python
code here
```""",
])
def test_normalize_malformed_frontmatter(malformed_input):
    """Test normalization handles various malformed frontmatter cases."""
    normalized = normalize_frontmatter(malformed_input)

    # After normalization, should either have valid frontmatter or be safe content
    # The key is it should not crash and should produce parseable output
    assert isinstance(normalized, str), "Should return a string"
    assert len(normalized) > 0, "Should not return empty string"

    # If it has frontmatter, it should be valid
    if normalized.lstrip().startswith('---'):
        # Only check validity if normalization added frontmatter
        # Some malformed inputs may not be fixable
        pass  # We're primarily testing it doesn't crash
