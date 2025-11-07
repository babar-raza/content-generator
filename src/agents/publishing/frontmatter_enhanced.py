"""Enhanced Frontmatter Agent - Creates frontmatter with prerequisites normalization."""

from typing import Optional, Dict, List, Any
from pathlib import Path
import logging
import json
from datetime import datetime

from ..base import (
    Agent, EventBus, AgentEvent, AgentContract, SelfCorrectingAgent,
    Config, logger
)

class FrontmatterAgent(SelfCorrectingAgent, Agent):
    """Creates blog post frontmatter with proper normalization."""

    def __init__(self, config: Config, event_bus: EventBus):
        Agent.__init__(self, "FrontmatterAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:
        return AgentContract(
            agent_id="FrontmatterAgent",
            capabilities=["create_frontmatter"],
            input_schema={"type": "object", "required": ["seo_metadata"]},
            output_schema={"type": "object"},
            publishes=["frontmatter_created"]
        )

    def _subscribe_to_events(self):
        self.event_bus.subscribe("execute_create_frontmatter", self.execute)

    def _normalize_prerequisites(self, value: Any) -> List[str]:
        """Normalize prerequisites to always be a list of strings.
        
        This prevents the 'prerequisites' KeyError by ensuring the field
        always exists and is properly formatted.
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

    def _ensure_seo_completeness(self, seo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all SEO fields exist with proper defaults."""
        from src.engine.slug_service import slugify
        
        # Ensure required fields
        if 'title' not in seo_metadata or not seo_metadata['title']:
            seo_metadata['title'] = seo_metadata.get('seoTitle', 'Untitled Post')
        
        if 'seoTitle' not in seo_metadata or not seo_metadata['seoTitle']:
            seo_metadata['seoTitle'] = seo_metadata['title'][:60]  # SEO title max length
        
        if 'description' not in seo_metadata or not seo_metadata['description']:
            seo_metadata['description'] = f"Learn about {seo_metadata['title']}"
        
        if 'slug' not in seo_metadata or not seo_metadata['slug']:
            seo_metadata['slug'] = slugify(seo_metadata['title'])
        
        # Ensure lists for tags and keywords
        for field in ['tags', 'keywords']:
            if field not in seo_metadata:
                seo_metadata[field] = []
            elif isinstance(seo_metadata[field], str):
                # Convert string to list
                seo_metadata[field] = [s.strip() for s in seo_metadata[field].split(',') if s.strip()]
            elif not isinstance(seo_metadata[field], list):
                seo_metadata[field] = []
        
        return seo_metadata

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        """Create frontmatter with normalized fields."""
        
        # Get SEO metadata and ensure completeness
        seo_metadata = event.data.get("seo_metadata", {})
        if not isinstance(seo_metadata, dict):
            logger.warning(f"Invalid seo_metadata type: {type(seo_metadata)}, using defaults")
            seo_metadata = {}
        
        seo_metadata = self._ensure_seo_completeness(seo_metadata)
        
        # Extract other optional fields from event data
        topic = event.data.get("topic", {})
        if not isinstance(topic, dict):
            topic = {}
        
        # Build frontmatter with all fields
        frontmatter = {
            "title": seo_metadata.get("title", "Untitled"),
            "seoTitle": seo_metadata.get("seoTitle", seo_metadata.get("title", "Untitled")),
            "description": seo_metadata.get("description", ""),
            "date": datetime.now().isoformat(),
            "lastmod": datetime.now().isoformat(),
            "draft": False,
            "tags": seo_metadata.get("tags", []),
            "keywords": seo_metadata.get("keywords", []),
            "slug": seo_metadata.get("slug", "untitled"),
            "author": seo_metadata.get("author", "AI Blog Generator"),
            "prerequisites": [],  # Always initialize as empty list
        }
        
        # Handle prerequisites if provided (always normalize to list)
        if "prerequisites" in event.data:
            frontmatter["prerequisites"] = self._normalize_prerequisites(event.data["prerequisites"])
        elif "prerequisites" in seo_metadata:
            frontmatter["prerequisites"] = self._normalize_prerequisites(seo_metadata["prerequisites"])
        elif "prerequisites" in topic:
            frontmatter["prerequisites"] = self._normalize_prerequisites(topic["prerequisites"])
        else:
            # Already initialized as empty list above
            pass
        
        # Add any additional metadata
        if "category" in seo_metadata:
            frontmatter["category"] = seo_metadata["category"]
        
        if "featured_image" in seo_metadata:
            frontmatter["featured_image"] = seo_metadata["featured_image"]
        
        # Add technical metadata
        frontmatter["generator"] = "AI Blog Generator v9.5"
        frontmatter["correlation_id"] = event.correlation_id
        
        # Validate critical fields one more time
        required_fields = ["title", "slug", "prerequisites"]
        for field in required_fields:
            if field not in frontmatter:
                logger.warning(f"Missing required field '{field}' in frontmatter, adding default")
                if field == "prerequisites":
                    frontmatter[field] = []
                else:
                    frontmatter[field] = f"default-{field}"
        
        logger.info(f"Created frontmatter for slug: {frontmatter['slug']}")
        logger.debug(f"Prerequisites: {frontmatter['prerequisites']}")
        
        return AgentEvent(
            event_type="frontmatter_created",
            data={"frontmatter": frontmatter, "slug": frontmatter["slug"]},
            source_agent=self.agent_id,
            correlation_id=event.correlation_id
        )

    def format_frontmatter(self, metadata: Dict[str, Any]) -> str:
        """Format frontmatter as YAML for markdown files."""
        import yaml
        
        # Ensure prerequisites is always a list
        if "prerequisites" in metadata:
            metadata["prerequisites"] = self._normalize_prerequisites(metadata["prerequisites"])
        else:
            metadata["prerequisites"] = []
        
        # Convert to YAML
        yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Wrap in frontmatter delimiters
        return f"---\n{yaml_str}---\n"
