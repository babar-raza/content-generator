# services_fixes.py
"""Service Fixes - NO-MOCK gate, PyTrends backoff, and error handling."""

import re
import time
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Mock/placeholder detection patterns
MOCK_PATTERNS = [
    r"Your Optimized Title Here",
    r"\{\{.*?\}\}",
    r"Compell(?:ing|)",
    r"\[PLACEHOLDER\]",
    r"Lorem ipsum",
    r"TODO:",
    r"FIXME:",
    r"Insert .* here",
    r"Add .* content",
    r"Write about",
    r"Describe .*",
    r"Example content",
    r"Sample text",
    r"Your .* here",
    r"Enter .* here",
    r"\.\.\.",  # Triple dots often indicate placeholder
    r"TBD",
    r"To be determined",
    r"Coming soon"
]

class NoMockGate:
    """Detector and rejector for mock/placeholder content."""
    
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in MOCK_PATTERNS]
        self.rejection_count = 0
    
    def contains_mock(self, text: str) -> bool:
        """Check if text contains mock/placeholder content."""
        if not text or len(text.strip()) < 10:
            return True  # Too short to be real content
        
        for pattern in self.patterns:
            if pattern.search(text):
                logger.warning(f"Mock content detected: {pattern.pattern}")
                self.rejection_count += 1
                return True
        
        return False
    
    def validate_response(self, response: Any) -> Tuple[bool, str]:
        """Validate LLM response for mock content.
        
        Returns:
            (is_valid, reason) tuple
        """
        if response is None:
            return False, "Response is None"
        
        # Check string responses
        if isinstance(response, str):
            if self.contains_mock(response):
                return False, "Contains mock/placeholder content"
            return True, ""
        
        # Check dict responses (JSON)
        if isinstance(response, dict):
            for key, value in response.items():
                if isinstance(value, str) and self.contains_mock(value):
                    return False, f"Field '{key}' contains mock content"
            return True, ""
        
        # Check list responses
        if isinstance(response, list):
            for idx, item in enumerate(response):
                if isinstance(item, str) and self.contains_mock(item):
                    return False, f"Item {idx} contains mock content"
            return True, ""
        
        return True, ""


class SEOSchemaGate:
    """Enforces and normalizes SEO schema requirements."""
    
    REQUIRED_FIELDS = ['title', 'seoTitle', 'description', 'tags', 'keywords', 'slug']
    
    @staticmethod
    def coerce_and_fill(meta: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce and fill missing SEO fields.
        
        Args:
            meta: Raw metadata dictionary
            
        Returns:
            Normalized dictionary with all required fields
        """
        from src.engine.slug_service import slugify
        
        # Handle nested structures
        if 'metadata' in meta and isinstance(meta['metadata'], dict):
            meta = meta['metadata']
        if 'data' in meta and isinstance(meta['data'], dict):
            if 'metadata' in meta['data']:
                meta = meta['data']['metadata']
        
        normalized = {}
        
        # Map synonyms to standard field names
        field_mappings = {
            'title': ['title', 'articleTitle', 'post_title', 'postTitle'],
            'seoTitle': ['seoTitle', 'seo_title', 'metaTitle', 'meta_title', 'title_tag'],
            'description': ['description', 'meta_description', 'metaDescription', 'seo_description', 'excerpt'],
            'tags': ['tags', 'tag', 'post_tags', 'categories'],
            'keywords': ['keywords', 'keyword', 'seo_keywords', 'search_keywords'],
            'slug': ['slug', 'url_slug', 'permalink', 'url'],
        }
        
        # Extract values using field mappings
        for target_field, possible_sources in field_mappings.items():
            for source in possible_sources:
                if source in meta:
                    value = meta[source]
                    
                    # Convert tags/keywords to lists if they're strings
                    if target_field in ['tags', 'keywords']:
                        if isinstance(value, str):
                            # Split by comma, semicolon, or pipe
                            value = [v.strip() for v in re.split(r'[,;|]', value) if v.strip()]
                        elif not isinstance(value, list):
                            value = []
                    
                    normalized[target_field] = value
                    break
        
        # Ensure title exists
        if 'title' not in normalized or not normalized['title']:
            if 'seoTitle' in normalized:
                normalized['title'] = normalized['seoTitle']
            else:
                normalized['title'] = 'Untitled Post'
        
        # Ensure seoTitle exists (truncate if needed)
        if 'seoTitle' not in normalized or not normalized['seoTitle']:
            title = normalized['title']
            if len(title) > 60:
                # Truncate at word boundary
                truncated = title[:60]
                last_space = truncated.rfind(' ')
                if last_space > 40:
                    title = truncated[:last_space]
                else:
                    title = truncated
            normalized['seoTitle'] = title
        
        # Ensure description exists
        if 'description' not in normalized or not normalized['description']:
            normalized['description'] = f"Learn about {normalized['title']} - comprehensive guide and tutorial."
        
        # Ensure tags and keywords are lists
        for field in ['tags', 'keywords']:
            if field not in normalized:
                normalized[field] = []
            elif not isinstance(normalized[field], list):
                normalized[field] = []
        
        # Auto-generate slug if missing
        if 'slug' not in normalized or not normalized['slug']:
            normalized['slug'] = slugify(normalized['title'])
            logger.info(f"Auto-generated slug: {normalized['slug']}")
        
        # Validate slug format (lowercase, hyphens only)
        slug = normalized['slug']
        slug = re.sub(r'[^a-z0-9-]', '-', slug.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        if not slug:
            slug = 'untitled-post'
        normalized['slug'] = slug
        
        return normalized


class PrerequisitesNormalizer:
    """Normalizes prerequisites field to always be a list."""
    
    @staticmethod
    def normalize(value: Any) -> List[str]:
        """Normalize prerequisites to a list of strings.
        
        Args:
            value: Raw prerequisites value (None, str, list, etc.)
            
        Returns:
            List of prerequisite strings (may be empty)
        """
        if value is None:
            return []
        
        if isinstance(value, str):
            # Handle comma-separated strings
            if ',' in value:
                return [v.strip() for v in value.split(',') if v.strip()]
            # Single prerequisite
            return [value.strip()] if value.strip() else []
        
        if isinstance(value, list):
            # Filter and convert to strings
            result = []
            for item in value:
                if item is not None:
                    str_item = str(item).strip()
                    if str_item:
                        result.append(str_item)
            return result
        
        # Fallback for other types
        try:
            str_value = str(value).strip()
            return [str_value] if str_value else []
        except:
            return []


class PyTrendsGuard:
    """Wrapper for PyTrends with retry logic and fallback."""
    
    def __init__(self, max_retries: int = 3, backoff: float = 2.0):
        self.max_retries = max_retries
        self.backoff = backoff
    
    def safe_fetch(self, query: str, fetch_func, fallback_value: Any = None) -> Any:
        """Safely fetch trends data with retries and fallback.
        
        Args:
            query: Search query
            fetch_func: Function to call for fetching
            fallback_value: Value to return on failure
            
        Returns:
            Fetched data or fallback value
        """
        delay = 1.0
        
        for attempt in range(self.max_retries):
            try:
                result = fetch_func(query)
                logger.info(f"PyTrends fetch successful for '{query}'")
                return result
            except Exception as e:
                logger.warning(f"PyTrends attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= self.backoff
                else:
                    # Final attempt failed, return fallback
                    logger.warning(f"PyTrends failed after {self.max_retries} attempts, using fallback")
                    if fallback_value is None:
                        fallback_value = {
                            "query": query,
                            "score": 50,  # Neutral score
                            "note": "fallback_due_to_error",
                            "trending": False
                        }
                    return fallback_value


class TopicIdentificationFallback:
    """Fallback logic for topic identification."""
    
    @staticmethod
    def ensure_topic(topic: Any) -> Dict[str, Any]:
        """Ensure topic has required fields with fallbacks.
        
        Args:
            topic: Raw topic data
            
        Returns:
            Normalized topic dictionary with title and slug
        """
        from src.engine.slug_service import slugify
        
        if not isinstance(topic, dict):
            topic = {}
        
        # Ensure title exists
        if 'title' not in topic or not topic.get('title'):
            # Try alternative fields
            title = (
                topic.get('name') or
                topic.get('topic') or
                topic.get('subject') or
                'Untitled Topic'
            )
            topic['title'] = title
            logger.warning(f"Topic missing title, using fallback: {title}")
        
        # Ensure slug exists
        if 'slug' not in topic or not topic.get('slug'):
            topic['slug'] = slugify(topic['title'])
            logger.info(f"Auto-generated topic slug: {topic['slug']}")
        
        # Ensure description exists
        if 'description' not in topic:
            topic['description'] = f"Content about {topic['title']}"
        
        return topic


class BlogSwitchPolicy:
    """Enforces blog switch output policy."""
    
    @staticmethod
    def get_output_path(config, slug: str) -> str:
        """Get the correct output path based on blog_switch policy.
        
        Args:
            config: Config object with blog_switch setting
            slug: Content slug
            
        Returns:
            Full path string for output file
        """
        from pathlib import Path
        
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if config.blog_switch:
            # Blog ON: ./output/{slug}/index.md
            slug_dir = output_dir / slug
            slug_dir.mkdir(parents=True, exist_ok=True)
            return str(slug_dir / "index.md")
        else:
            # Blog OFF: ./output/{slug}.md
            return str(output_dir / f"{slug}.md")


class RunToResultGuarantee:
    """Ensures output is always produced even on partial failures."""
    
    @staticmethod
    def create_minimal_document(topic: str = "Untitled", slug: str = "untitled") -> str:
        """Create a minimal but valid markdown document.
        
        Args:
            topic: Topic title
            slug: URL slug
            
        Returns:
            Minimal markdown document with frontmatter
        """
        frontmatter = {
            "title": topic,
            "seoTitle": topic,
            "description": f"Information about {topic}",
            "tags": [],
            "keywords": [],
            "slug": slug,
            "date": datetime.now().isoformat(),
            "author": "System",
            "prerequisites": [],
            "draft": True,
            "note": "Generated as fallback due to processing errors"
        }
        
        content = f"""---
{json.dumps(frontmatter, indent=2)}
---

# {topic}

## Introduction

This document provides information about {topic}.

## Overview

*Content is being generated. This is a placeholder document created to ensure output availability.*

## Key Points

- Topic: {topic}
- Status: Draft
- Further content to be added

## Conclusion

This document will be updated with more comprehensive content.

---
*Note: This is a minimal document generated due to processing constraints. Full content generation is pending.*
"""
        return content


def apply_llm_service_fixes(llm_service_class):
    """Apply NO-MOCK gate and other fixes to LLMService class."""
    
    # Store original generate method
    original_generate = llm_service_class.generate
    
    # Create NO-MOCK gate instance
    no_mock_gate = NoMockGate()
    
    def generate_with_validation(self, prompt: str, schema: Optional[Dict] = None, **kwargs):
        """Enhanced generate with NO-MOCK validation and retries."""
        max_attempts = kwargs.pop('max_attempts', 3)
        
        for attempt in range(max_attempts):
            try:
                # Call original generate
                response = original_generate(self, prompt, schema, **kwargs)
                
                # Validate response for mock content
                is_valid, reason = no_mock_gate.validate_response(response)
                
                if is_valid:
                    return response
                
                logger.warning(f"Attempt {attempt + 1}: Invalid response - {reason}")
                
                # Try with stricter prompt on retry
                if attempt < max_attempts - 1:
                    prompt = f"IMPORTANT: Provide real, specific content. No placeholders, examples, or generic text.\n\n{prompt}"
                    time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Generate attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    raise
        
        # All attempts failed
        raise ValueError(f"Failed to generate valid content after {max_attempts} attempts (mock content detected)")
    
    # Replace method
    llm_service_class.generate = generate_with_validation
    
    return llm_service_class
