"""Content Expansion Utility

Automatically expands content that falls below size thresholds by adding
meaningful, relevant sections to meet production quality requirements.

Production Quality Fix - Deterministic Size Enforcement
"""
import re
import logging
from typing import Optional
from src.utils.frontmatter_normalize import extract_frontmatter

logger = logging.getLogger(__name__)

# Thresholds
MIN_BYTES_THRESHOLD = 1800  # Hard minimum from quality gate
TARGET_BYTES = 2200  # Safety buffer
MAX_EXPANSION_ATTEMPTS = 2


def needs_expansion(content: str, min_bytes: int = MIN_BYTES_THRESHOLD) -> bool:
    """Check if content needs expansion based on size threshold.

    Args:
        content: Content to check
        min_bytes: Minimum byte threshold

    Returns:
        True if content is below threshold and needs expansion
    """
    return len(content.encode('utf-8')) < min_bytes


def expand_content(
    content: str,
    llm_service,
    topic: Optional[str] = None,
    target_bytes: int = TARGET_BYTES,
    max_attempts: int = MAX_EXPANSION_ATTEMPTS
) -> str:
    """Expand short content to meet minimum size requirements.

    This function adds meaningful sections to content that is below
    the size threshold. It preserves the original content and frontmatter,
    adding relevant sections like FAQs, common pitfalls, best practices, etc.

    Args:
        content: Original content (potentially short)
        llm_service: LLM service for generating expansion
        topic: Optional topic for context
        target_bytes: Target size in bytes (default: 2200)
        max_attempts: Maximum expansion attempts (default: 2)

    Returns:
        Expanded content meeting size requirements

    Raises:
        ValueError: If content cannot be expanded after max attempts
    """
    if not needs_expansion(content, target_bytes):
        logger.debug(f"Content already meets size requirement: {len(content)} bytes")
        return content

    original_size = len(content.encode('utf-8'))
    logger.info(f"Content below threshold ({original_size} bytes), initiating expansion")

    # Extract frontmatter and body
    frontmatter = extract_frontmatter(content)
    if frontmatter and content.lstrip().startswith('---'):
        # Split frontmatter from body
        lines = content.lstrip().split('\n')
        second_marker = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                second_marker = i
                break
        if second_marker > 0:
            frontmatter_block = '\n'.join(lines[:second_marker+1])
            body = '\n'.join(lines[second_marker+1:]).strip()
        else:
            frontmatter_block = ""
            body = content
    else:
        frontmatter_block = ""
        body = content

    # Extract title for context
    title = topic
    if frontmatter and 'title' in frontmatter:
        title = frontmatter['title']
    elif not title:
        # Try to extract from first heading
        heading_match = re.search(r'^#\s+(.+?)$', body, re.MULTILINE)
        if heading_match:
            title = heading_match.group(1).strip()

    # Perform expansion attempts
    expanded_body = body
    for attempt in range(1, max_attempts + 1):
        current_size = len(expanded_body.encode('utf-8'))
        bytes_needed = target_bytes - current_size

        logger.info(f"Expansion attempt {attempt}/{max_attempts}: current={current_size}, target={target_bytes}")

        # Generate expansion sections
        expansion_prompt = f"""The following content is too brief ({current_size} bytes) and needs to be expanded to approximately {target_bytes} bytes.

Current content:
{expanded_body}

Please add {1 if attempt == 1 else 2} meaningful section(s) to expand this content. Choose from:
- "## Frequently Asked Questions" - Common questions and answers about {title or 'this topic'}
- "## Common Pitfalls" - Typical mistakes and how to avoid them
- "## Best Practices" - Recommended approaches and tips
- "## Performance Considerations" - Optimization tips and performance notes
- "## Troubleshooting" - Common issues and solutions
- "## Additional Resources" - Related topics and further reading

Requirements:
- Add substantial content (aim for {bytes_needed // (1 if attempt == 1 else 2)} bytes per section)
- Keep technical accuracy and relevance
- Maintain consistency with existing content
- Do NOT repeat existing information
- Do NOT include frontmatter (it will be added separately)

Output only the expanded content (original + new sections), no explanations."""

        try:
            expansion = llm_service.generate(
                expansion_prompt,
                temperature=0.5,  # Lower temperature for more focused expansion
                max_tokens=1500
            )

            if not expansion or len(expansion.strip()) < 100:
                logger.warning(f"Expansion attempt {attempt} produced minimal output")
                continue

            # Clean up the expansion (remove any accidentally added frontmatter)
            expansion = expansion.strip()
            if expansion.startswith('---'):
                # LLM added frontmatter, strip it
                lines = expansion.split('\n')
                second_marker = -1
                for i in range(1, len(lines)):
                    if lines[i].strip() == '---':
                        second_marker = i
                        break
                if second_marker > 0:
                    expansion = '\n'.join(lines[second_marker+1:]).strip()

            expanded_body = expansion

            # Check if we've met the target
            new_size = len(expanded_body.encode('utf-8'))
            logger.info(f"Expansion attempt {attempt} resulted in {new_size} bytes")

            if new_size >= target_bytes:
                logger.info(f"Successfully expanded content: {original_size} → {new_size} bytes")
                # Reconstruct full content with frontmatter
                if frontmatter_block:
                    return f"{frontmatter_block}\n\n{expanded_body}"
                else:
                    return expanded_body

        except Exception as e:
            logger.error(f"Expansion attempt {attempt} failed: {e}")
            continue

    # Failed to expand after max attempts
    final_size = len(expanded_body.encode('utf-8'))
    error_msg = (
        f"Failed to expand content after {max_attempts} attempts. "
        f"Original: {original_size} bytes, Final: {final_size} bytes, Target: {target_bytes} bytes"
    )
    logger.error(error_msg)
    raise ValueError(error_msg)


def ensure_minimum_size(
    content: str,
    llm_service,
    topic: Optional[str] = None,
    min_bytes: int = TARGET_BYTES
) -> str:
    """Ensure content meets minimum size requirement, expanding if necessary.

    This is a convenience wrapper around expand_content that provides
    a simple interface for enforcing size requirements.

    Args:
        content: Content to check and potentially expand
        llm_service: LLM service for generating expansion
        topic: Optional topic for context
        min_bytes: Minimum size requirement in bytes

    Returns:
        Content meeting minimum size requirement

    Raises:
        ValueError: If content cannot be expanded to meet requirements
    """
    if not needs_expansion(content, min_bytes):
        return content

    return expand_content(
        content=content,
        llm_service=llm_service,
        topic=topic,
        target_bytes=min_bytes,
        max_attempts=MAX_EXPANSION_ATTEMPTS
    )
