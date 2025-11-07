"""Slug generation service - deterministic URL-safe slugs."""

import re
import unicodedata
from typing import Optional


def slugify(text: str, max_length: Optional[int] = None) -> str:
    """Generate URL-safe slug from text.
    
    Rules:
    1. Lowercase
    2. Unicode → ASCII (transliterate where possible)
    3. Replace any sequence of non [a-z0-9] with -
    4. Collapse repeated - to single -
    5. Trim leading/trailing -
    6. Truncate at word boundary if max_length specified
    
    Args:
        text: Input text
        max_length: Optional maximum length (truncates at word boundary)
        
    Returns:
        URL-safe slug
        
    Examples:
        >>> slugify("C# 10 Features: Pattern Matching+")
        'c-10-features-pattern-matching'
        >>> slugify("Python's Best Practices & Tips (2024)!")
        'pythons-best-practices-tips-2024'
        >>> slugify("Very Long Title Here", max_length=10)
        'very-long'
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Unicode → ASCII
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Replace non-alphanumeric with hyphen
    text = re.sub(r'[^a-z0-9]+', '-', text)
    
    # Collapse repeated hyphens
    text = re.sub(r'-+', '-', text)
    
    # Trim leading/trailing hyphens
    text = text.strip('-')
    
    # Apply max_length if specified
    if max_length and len(text) > max_length:
        # Truncate at word boundary
        truncated = text[:max_length]
        # Find last hyphen for word boundary
        last_hyphen = truncated.rfind('-')
        # Only truncate at hyphen if it's reasonably close to the end
        if last_hyphen > max_length * 0.6:  # At least 60% of max_length
            text = truncated[:last_hyphen]
        else:
            text = truncated
    
    return text


def validate_slug(slug: str) -> bool:
    """Validate if a slug is properly formatted.
    
    Args:
        slug: Slug to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not slug:
        return False
    
    # Check format: lowercase letters, numbers, and hyphens only
    if not re.match(r'^[a-z0-9-]+$', slug):
        return False
    
    # No consecutive hyphens
    if '--' in slug:
        return False
    
    # No leading or trailing hyphens
    if slug.startswith('-') or slug.endswith('-'):
        return False
    
    return True


def ensure_unique_slug(base_slug: str, existing_slugs: list) -> str:
    """Ensure slug is unique by appending number if needed.
    
    Args:
        base_slug: Base slug to make unique
        existing_slugs: List of existing slugs
        
    Returns:
        Unique slug
    """
    if base_slug not in existing_slugs:
        return base_slug
    
    counter = 1
    while True:
        new_slug = f"{base_slug}-{counter}"
        if new_slug not in existing_slugs:
            return new_slug
        counter += 1
        if counter > 100:  # Safety limit
            # Use timestamp for uniqueness
            import time
            return f"{base_slug}-{int(time.time())}"
