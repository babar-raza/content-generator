"""Frontmatter Normalization Utility

Ensures LLM-generated content has proper YAML frontmatter with --- delimiters,
even if the LLM outputs ```yaml fenced blocks or bare YAML.

Production Pipeline Validation v2 - Root Cause Fix
"""
import re
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def _sanitize_delimiter_line(line: str) -> str:
    """Sanitize a frontmatter delimiter line to be exactly '---'.

    Handles cases like:
    - '---`' -> '---'
    - '--- ```' -> '---'
    - '---  \t' -> '---'
    - '---\r' -> '---'

    Args:
        line: A line that should be a --- delimiter

    Returns:
        Sanitized line (exactly '---' if it looks like a delimiter, original otherwise)
    """
    stripped = line.strip()
    # Check if line starts with --- (allowing trailing garbage)
    if stripped.startswith('---'):
        # Extract just the --- part (may have trailing characters)
        # Remove anything after the --- (backticks, spaces, etc.)
        return '---'
    return line


def _sanitize_frontmatter_delimiters(text: str) -> str:
    """Sanitize frontmatter delimiter lines to remove trailing garbage.

    This handles LLM-generated outputs like:
    ---
    title: "My Title"
    ---`    <-- Extra backtick here breaks YAML parsing

    Args:
        text: Content with potentially malformed delimiter lines

    Returns:
        Content with cleaned delimiter lines
    """
    if not text or not text.startswith('---'):
        return text

    lines = text.split('\n')

    # Sanitize first line (opening delimiter)
    if lines[0].strip().startswith('---'):
        lines[0] = _sanitize_delimiter_line(lines[0])

    # Find and sanitize closing delimiter
    for i in range(1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith('---'):
            lines[i] = _sanitize_delimiter_line(lines[i])
            # Only sanitize the first occurrence of closing delimiter
            break

    return '\n'.join(lines)


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
        # FIRST: Sanitize delimiter lines to remove trailing garbage (e.g., ---`)
        text = _sanitize_frontmatter_delimiters(text)

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

    This function performs both structural and semantic validation:
    1. Checks for proper --- delimiters
    2. Validates that YAML content is parseable with yaml.safe_load()

    Args:
        text: Content to check

    Returns:
        True if valid frontmatter exists, False otherwise
    """
    import yaml

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

    # CRITICAL: Parse YAML to ensure it's truly valid
    try:
        parsed = yaml.safe_load(yaml_content)
        # Frontmatter should parse as a dict
        if parsed is None or not isinstance(parsed, dict):
            logger.debug(f"Frontmatter YAML parsed but not a dict: {type(parsed)}")
            return False
        return True
    except yaml.YAMLError as e:
        logger.debug(f"Frontmatter YAML parsing failed: {e}")
        return False


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


def enforce_frontmatter(content: str, fallback_metadata: Optional[Dict[str, Any]] = None) -> str:
    """Enforce valid YAML frontmatter with strict validation and repair.

    This function implements a "normalize → validate → repair → validate" pipeline
    to ensure the output ALWAYS has valid, parseable YAML frontmatter.

    Pipeline:
    1. Strip any leading code fences (```markdown, etc.)
    2. Run normalize_frontmatter
    3. Validate YAML is parseable with yaml.safe_load
    4. If invalid, attempt aggressive repair
    5. Assert final result has valid frontmatter

    Args:
        content: Raw content that may have malformed frontmatter
        fallback_metadata: Optional metadata to use if repair is needed

    Returns:
        Content with guaranteed valid YAML frontmatter

    Raises:
        ValueError: If frontmatter cannot be made valid despite all repair attempts
    """
    import yaml
    from datetime import datetime

    if not content or not content.strip():
        if fallback_metadata:
            return _create_frontmatter(fallback_metadata) + "\n"
        # Create minimal valid frontmatter
        minimal = {
            'title': 'Untitled',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'tags': [],
            'draft': False
        }
        return _create_frontmatter(minimal) + "\n"

    # Step 1: Strip any leading markdown code fences
    content = content.lstrip()
    if content.startswith('```markdown') or content.startswith('```md'):
        # Find the closing fence
        fence_end = content.find('```', 3)
        if fence_end > 0:
            content = content[fence_end + 3:].lstrip()
            logger.info("Stripped leading markdown code fence")

    # Step 2: Normalize frontmatter structure
    normalized = normalize_frontmatter(content, fallback_metadata)

    # Step 3: Validate YAML is parseable
    if has_valid_frontmatter(normalized):
        # Extract and try to parse the YAML
        text = normalized.lstrip()
        second_marker = text.find('---', 3)
        if second_marker > 0:
            yaml_content = text[3:second_marker].strip()
            try:
                # Test parse the YAML
                parsed = yaml.safe_load(yaml_content)
                if parsed is not None and isinstance(parsed, dict):
                    # Valid YAML, return normalized content
                    return normalized
                else:
                    logger.warning(f"YAML parsed but not a dict: {type(parsed)}")
            except yaml.YAMLError as e:
                logger.warning(f"YAML parsing failed after normalization: {e}")
                # Continue to repair step

    # Step 4: Aggressive repair
    logger.info("Attempting aggressive frontmatter repair")

    # Extract the body content (everything after first potential frontmatter block)
    body = ""
    text = normalized.lstrip()

    if text.startswith('---'):
        # Try to find the end of frontmatter block
        lines = text.split('\n')
        body_start = 1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                body_start = i + 1
                break
        if body_start < len(lines):
            body = '\n'.join(lines[body_start:]).strip()
    else:
        # No frontmatter at all, use full content as body
        body = text

    # Try to extract title from body
    title = "Untitled"
    if fallback_metadata and 'title' in fallback_metadata:
        title = fallback_metadata['title']
    else:
        # Try to extract from first heading
        heading_match = re.match(r'^#\s+(.+?)(?:\n|$)', body, re.MULTILINE)
        if heading_match:
            title = heading_match.group(1).strip()
            # Remove emojis and special chars for YAML safety
            title = re.sub(r'[^\w\s\-:,\.]', '', title).strip()
            if not title:
                title = "Untitled"

    # Create minimal safe frontmatter
    safe_metadata = {
        'title': title,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'tags': fallback_metadata.get('tags', []) if fallback_metadata else [],
        'draft': False
    }

    # Rebuild content with safe frontmatter
    repaired = _create_frontmatter(safe_metadata) + "\n\n" + body

    # Step 5: Final validation
    if not has_valid_frontmatter(repaired):
        raise ValueError("Failed to create valid frontmatter despite repair attempts")

    # Verify YAML is parseable
    text = repaired.lstrip()
    second_marker = text.find('---', 3)
    yaml_content = text[3:second_marker].strip()
    try:
        parsed = yaml.safe_load(yaml_content)
        if parsed is None or not isinstance(parsed, dict):
            raise ValueError(f"YAML parsed but invalid type: {type(parsed)}")
    except yaml.YAMLError as e:
        raise ValueError(f"Final YAML validation failed: {e}")

    logger.info("Frontmatter repair successful")
    return repaired
