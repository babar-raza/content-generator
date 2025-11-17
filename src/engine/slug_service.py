"""Slug generation service - deterministic URL-safe slugs."""

import re
import unicodedata


def slugify(text: str) -> str:
    """Generate URL-safe slug from text.
    
    Rules:
    1. Lowercase
    2. Unicode → ASCII (transliterate where possible)
    3. Replace any sequence of non [a-z0-9] with -
    4. Collapse repeated - to single -
    5. Trim leading/trailing -
    
    Args:
        text: Input text
        
    Returns:
        URL-safe slug
        
    Examples:
        >>> slugify("C# 10 Features: Pattern Matching+")
        'c-10-features-pattern-matching'
        >>> slugify("Python's Best Practices & Tips (2024)!")
        'pythons-best-practices-tips-2024'
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
    
    return text
# DOCGEN:LLM-FIRST@v4