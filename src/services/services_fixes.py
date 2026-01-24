"""Service fixes and utilities for data normalization and validation."""

from typing import Any, Dict, List, Union, Optional


class SEOSchemaGate:
    """Gate for SEO schema validation and normalization."""

    @staticmethod
    def coerce_and_fill(data: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce and fill missing SEO fields with defaults.

        Args:
            data: Input data dictionary

        Returns:
            Normalized data with all required SEO fields
        """
        # Get title from various possible locations
        title = data.get("title") or data.get("metadata", {}).get("title") or "Untitled Post"

        # Generate slug from title if missing
        slug = data.get("slug") or title.lower().replace(" ", "-").replace("_", "-")

        # Default description
        description = data.get("description") or f"Learn about {title} - comprehensive guide and tutorial."

        # Normalize tags
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
        elif not isinstance(tags, list):
            tags = []

        # Normalize keywords
        keywords = data.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.replace(";", ",").split(",") if k.strip()]
        elif not isinstance(keywords, list):
            keywords = []

        return {
            "title": title,
            "seoTitle": data.get("seoTitle") or title,
            "description": description,
            "tags": tags,
            "keywords": keywords,
            "slug": slug
        }


class PrerequisitesNormalizer:
    """Normalizer for prerequisites field."""

    @staticmethod
    def normalize(value: Union[None, str, List[str], Any]) -> List[str]:
        """Normalize prerequisites to a list of strings.

        Args:
            value: Input value (None, string, list, or other)

        Returns:
            List of normalized prerequisite strings
        """
        if value is None or value == "":
            return []

        if isinstance(value, str):
            # Split by comma and clean up
            items = [item.strip() for item in value.split(",") if item.strip()]
            return items if items else []

        if isinstance(value, list):
            # Filter out None and empty strings
            return [str(item).strip() for item in value if item and str(item).strip()]

        # Convert other types to string
        return [str(value).strip()] if str(value).strip() else []


class NoMockGate:
    """Gate to validate responses don't contain mock/placeholder content."""

    MOCK_PATTERNS = [
        "your title here",
        "todo:",
        "placeholder",
        "lorem ipsum",
        "...",
        "[",  # Placeholder brackets
    ]

    def validate_response(self, data: Union[Dict, str]) -> tuple[bool, str]:
        """Validate that response doesn't contain mock content.

        Args:
            data: Response data (dict or string)

        Returns:
            Tuple of (is_valid, reason)
        """
        content_str = ""

        if isinstance(data, dict):
            content_str = str(data).lower()
        else:
            content_str = str(data).lower()

        for pattern in self.MOCK_PATTERNS:
            if pattern in content_str:
                return False, f"Contains mock content: {pattern}"

        return True, ""


class PyTrendsGuard:
    """Guard for PyTrends API calls with fallback."""

    def __init__(self, max_retries: int = 3, backoff: float = 1.0):
        self.max_retries = max_retries
        self.backoff = backoff

    def safe_fetch(self, query: str, fetch_fn: callable) -> Dict[str, Any]:
        """Safely fetch from PyTrends with fallback.

        Args:
            query: Search query
            fetch_fn: Function to fetch data

        Returns:
            Fetched data or fallback data
        """
        try:
            return fetch_fn(query)
        except Exception:
            # Return fallback data
            return {
                "note": "fallback_due_to_error",
                "score": 50,
                "query": query
            }


class TopicIdentificationFallback:
    """Fallback for topic identification."""

    @staticmethod
    def ensure_topic(data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure topic data has required fields.

        Args:
            data: Topic data

        Returns:
            Topic data with required fields
        """
        if not data or not data.get("title"):
            # Check for alternative field names
            title = data.get("name") or data.get("topic") or "Untitled Topic"
        else:
            title = data["title"]

        slug = data.get("slug") or title.lower().replace(" ", "-")

        return {
            "title": title,
            "slug": slug,
            **{k: v for k, v in data.items() if k not in ["title", "slug"]}
        }


class BlogSwitchPolicy:
    """Policy for blog switch path generation."""
    pass


class RunToResultGuarantee:
    """Guarantee that runs produce results."""

    @staticmethod
    def create_minimal_document(topic: str, slug: str) -> str:
        """Create a minimal fallback document.

        Args:
            topic: Document topic
            slug: Document slug

        Returns:
            Minimal markdown document
        """
        return f"""---
{{
  "title": "{topic}",
  "slug": "{slug}",
  "description": "Fallback content - generation incomplete",
  "tags": [],
  "keywords": [],
  "prerequisites": [],
  "draft": true
}}
---

# {topic}

This is a fallback document generated when the primary content generation failed.
"""


def apply_llm_service_fixes(service_class: type) -> None:
    """Apply fixes to LLM service class.

    This is a no-op function for compatibility with production_execution_engine.
    The actual NoMockGate validation is handled separately.

    Args:
        service_class: The LLM service class to apply fixes to
    """
    pass


__all__ = [
    'SEOSchemaGate',
    'PrerequisitesNormalizer',
    'NoMockGate',
    'PyTrendsGuard',
    'TopicIdentificationFallback',
    'BlogSwitchPolicy',
    'RunToResultGuarantee',
    'apply_llm_service_fixes',
]
