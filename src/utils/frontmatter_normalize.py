"""Frontmatter Normalization Utility

Ensures LLM-generated content has proper YAML frontmatter with --- delimiters,
even if the LLM outputs ```yaml fenced blocks or bare YAML.

Production Pipeline Validation v2 - Root Cause Fix
"""
import re
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def normalize_frontmatter(text: str, fallback_metadata: Optional[Dict[str, Any]] = None) -> str:
    """Normalize frontmatter to use proper --- delimiters.

    Handles these cases:
    1. ```yaml or ```yml fenced block at start -> extract and wrap with ---
    2. Bare YAML at start (title: ...) without delimiters -> wrap with ---
    3. Already valid --- ... --- -> leave unchanged
    4. No frontmatter -> optionally insert from fallback_metadata

    Args:
        text: Raw content that may have malformed frontmatter
        fallback_metadata: Optional dict to use if no frontmatter found

    Returns:
        Content with properly normalized frontmatter (--- delimited)

    Examples:
        >>> # Fenced block gets normalized
        >>> text = '''```yaml
        ... title: My Post
        ... tags: [python]
        ... ```
        ... # Content here'''
        >>> result = normalize_frontmatter(text)
        >>> result.startswith('---')
        True

        >>> # Already valid frontmatter unchanged
        >>> text = '''---
        ... title: My Post
        ... ---
        ... # Content'''
        >>> normalize_frontmatter(text) == text
        True
    """
    if not text or not text.strip():
        if fallback_metadata:
            return _create_frontmatter(fallback_metadata) + "\n"
        return text

    text = text.lstrip()

    # Case 0: Content wrapped in ```markdown fence - strip the outer fence first
    markdown_fence_pattern = r'^```(?:markdown|md)\s*\n(.*?)```\s*$'
    markdown_match = re.match(markdown_fence_pattern, text, re.DOTALL | re.IGNORECASE)
    if markdown_match:
        # Extract content from inside markdown fence
        inner_content = markdown_match.group(1)
        logger.info("Stripped outer ```markdown fence, processing inner content")
        # Recursively process the inner content
        return normalize_frontmatter(inner_content.strip(), fallback_metadata)

    # Case 1: Already valid frontmatter with --- delimiters
    if text.startswith('---'):
        # Handle case of double --- at start (malformed: ---\n---\ntitle:)
        lines = text.split('\n')
        if len(lines) > 1 and lines[1].strip() == '---':
            # Remove the duplicate --- and reprocess
            logger.info("Detected double --- at start, fixing malformed frontmatter")
            fixed_text = '---\n' + '\n'.join(lines[2:])
            return normalize_frontmatter(fixed_text, fallback_metadata)

        # Verify it's complete (has closing ---)
        second_marker = text.find('---', 3)
        if second_marker > 0:
            # Check that content between markers is valid YAML-like
            yaml_content = text[3:second_marker].strip()
            if yaml_content and ':' in yaml_content:
                logger.debug("Frontmatter already valid with --- delimiters")
                return text
        # Incomplete --- block, try to fix
        logger.warning("Incomplete --- frontmatter block, attempting repair")
        # Find where YAML ends (first blank line or markdown heading)
        lines = text[3:].split('\n')
        yaml_end = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == '---':
                yaml_end = i
                break
            if stripped == '' or stripped.startswith('#'):
                yaml_end = i
                break
        if yaml_end > 0:
            yaml_lines = lines[:yaml_end]
            rest_lines = lines[yaml_end:]
            yaml_content = '\n'.join(yaml_lines).strip()
            rest = '\n'.join(rest_lines).lstrip('\n-').strip()
            return f"---\n{yaml_content}\n---\n\n{rest}"

    # Case 2: ```yaml or ```yml fenced block at start
    fence_pattern = r'^```(?:yaml|yml)\s*\n(.*?)```'
    match = re.match(fence_pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        yaml_content = match.group(1).strip()
        rest = text[match.end():].lstrip()

        # Check if the content inside the fence already has --- delimiters
        if yaml_content.startswith('---'):
            # Content inside fence is already proper frontmatter + body
            # Just return it directly (recursively process to handle any issues)
            logger.info("Stripped ```yaml fence containing existing frontmatter")
            return normalize_frontmatter(yaml_content + "\n\n" + rest, fallback_metadata)

        logger.info("Normalized ```yaml fenced block to --- delimiters")
        return f"---\n{yaml_content}\n---\n\n{rest}"

    # Case 3: Bare YAML at start (no delimiters)
    # Check if first line looks like YAML (key: value)
    first_line = text.split('\n')[0].strip()
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*:', first_line):
        # Find where YAML section ends
        lines = text.split('\n')
        yaml_end = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            # End of YAML: blank line, markdown heading, or non-YAML content
            if stripped == '':
                yaml_end = i
                break
            if stripped.startswith('#') and not stripped.startswith('# '):
                # Markdown heading (not YAML comment)
                yaml_end = i
                break
            if not (re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*:', stripped) or
                    stripped.startswith('-') or
                    stripped.startswith(' ') or
                    stripped.startswith('\t') or
                    stripped.startswith('[') or
                    stripped == ''):
                # Likely content, not YAML
                yaml_end = i
                break
            yaml_end = i + 1

        if yaml_end > 0:
            yaml_lines = lines[:yaml_end]
            rest_lines = lines[yaml_end:]
            yaml_content = '\n'.join(yaml_lines).strip()
            rest = '\n'.join(rest_lines).strip()

            logger.info("Wrapped bare YAML with --- delimiters")
            return f"---\n{yaml_content}\n---\n\n{rest}"

    # Case 4: No frontmatter found
    if fallback_metadata:
        logger.info("No frontmatter found, inserting from fallback metadata")
        return _create_frontmatter(fallback_metadata) + "\n\n" + text

    # Case 5: No frontmatter and no fallback - try to extract title from first heading
    # and create minimal frontmatter to ensure validation passes
    heading_match = re.match(r'^#\s+(.+?)(?:\n|$)', text)
    if heading_match:
        title = heading_match.group(1).strip()
        # Remove emojis and special characters from title for YAML safety
        title = re.sub(r'[^\w\s\-:,]', '', title).strip()
        if title:
            logger.info(f"No frontmatter found, creating from first heading: {title[:50]}")
            auto_metadata = {
                'title': title,
                'tags': ['auto-generated'],
                'date': 'auto'
            }
            return _create_frontmatter(auto_metadata) + "\n\n" + text

    # No frontmatter, no fallback, no heading - return as-is
    logger.debug("No frontmatter found and no fallback provided")
    return text


def _create_frontmatter(metadata: Dict[str, Any]) -> str:
    """Create YAML frontmatter from metadata dict."""
    import yaml

    # Ensure required fields
    if 'title' not in metadata:
        metadata['title'] = 'Untitled'

    yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str.strip()}\n---"


def has_valid_frontmatter(text: str) -> bool:
    """Check if text has valid YAML frontmatter with --- delimiters.

    Args:
        text: Content to check

    Returns:
        True if valid frontmatter exists, False otherwise
    """
    if not text:
        return False

    text = text.lstrip()

    if not text.startswith('---'):
        return False

    second_marker = text.find('---', 3)
    if second_marker <= 0:
        return False

    yaml_content = text[3:second_marker].strip()
    if not yaml_content or ':' not in yaml_content:
        return False

    return True


def extract_frontmatter(text: str) -> Optional[Dict[str, Any]]:
    """Extract frontmatter as a dictionary.

    Args:
        text: Content with frontmatter

    Returns:
        Dict of frontmatter fields, or None if no valid frontmatter
    """
    import yaml

    if not has_valid_frontmatter(text):
        return None

    text = text.lstrip()
    second_marker = text.find('---', 3)
    yaml_content = text[3:second_marker].strip()

    try:
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse frontmatter YAML: {e}")
        return None
