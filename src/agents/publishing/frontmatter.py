"""Frontmatter Agent - Generates frontmatter for blog posts."""

from typing import Optional, Dict, List, Any
from pathlib import Path
import logging

from ..base import (
    Agent, EventBus, AgentEvent, AgentContract, SelfCorrectingAgent,
    Config, LLMService, DatabaseService, EmbeddingService, GistService,
    LinkChecker, TrendsService, PROMPTS, SCHEMAS, CSHARP_LICENSE_HEADER,
    MarkdownDedup, read_file_with_fallback_encoding, chunk_text, 
    build_query, dedupe_context, insert_license, split_code_into_segments,
    validate_code_quality, validate_api_compliance, extract_keywords,
    inject_keywords_naturally, write_markdown_tree, create_frontmatter,
    create_gist_shortcode, create_code_block, extract_code_blocks,
    IngestionStateManager, build_section_prompt_enhancement,
    get_section_heading, is_section_enabled, logger
)


class FrontmatterAgent(SelfCorrectingAgent, Agent):

    """Adds frontmatter to blog post."""

    def __init__(self, config: Config, event_bus: EventBus):

        Agent.__init__(self, "FrontmatterAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="FrontmatterAgent",

            capabilities=["add_frontmatter"],

            input_schema={"type": "object", "required": ["content", "seo_metadata"]},

            output_schema={"type": "object", "required": ["markdown"]},

            publishes=["frontmatter_added"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_add_frontmatter", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        # Try to get content from multiple possible keys
        content = event.data.get("content") or event.data.get("assembled_content") or ""

        seo_metadata = event.data.get("seo_metadata", {})

        gist_data = event.data.get("gist_data")

        code_segments = event.data.get("code_segments", [])

        validated_code = event.data.get("validated_code", "")

        if not content or not content.strip():
            # Generate minimal content if missing
            logger.warning("Content missing for frontmatter, generating minimal placeholder")
            topic = event.data.get("topic", {})
            topic_title = topic.get("title", "Blog Post")
            content = f"# {topic_title}\n\nContent is being generated..."

        if "seo_metadata" not in event.data or not seo_metadata:
            logger.warning("SEO metadata missing, using defaults")
            topic = event.data.get("topic", {})
            from src.engine.slug_service import slugify
            topic_title = topic.get("title", "Blog Post")
            seo_metadata = {
                "title": topic_title,
                "seoTitle": topic_title[:60] if len(topic_title) <= 60 else topic_title[:60].rsplit(' ', 1)[0],
                "description": "A comprehensive guide",
                "tags": [],
                "keywords": [],
                "slug": topic.get("slug") or slugify(topic_title)
            }

        # Get family from config

        seo_metadata['family'] = self.config.FAMILY_NAME_MAP.get(

            self.config.family,

            'Words'

        ).replace('Aspose.', '')

        # Add content for description fallback

        seo_metadata['content'] = content

        # Create frontmatter using template

        frontmatter = create_frontmatter(seo_metadata, self.config)

        # Build final markdown

        parts = [frontmatter, content]

        # Add code sections

        if code_segments:

            parts.append("\n## Code Implementation\n")

            if gist_data:

                owner = gist_data.get("owner", "user")

                gist_id = gist_data.get("gist_id")

                filename = gist_data.get("filename")

                if not filename:

                    # KILO: FrontmatterAgent — tolerate missing filename

                    # Try to infer from raw_urls dict

                    raw = (gist_data.get("urls") or {}).get("raw_urls") or {}

                    if isinstance(raw, dict) and raw:

                        filename = next(iter(raw.keys()))

                    # use filename if present to build gist shortcode; else inline code fallback

                if gist_id and filename:

                    shortcode = create_gist_shortcode(owner, gist_id, filename)

                    parts.append(f"\n{shortcode}\n")

                else:

                    parts.append(create_code_block(validated_code, "cs"))

            # Add explained segments

            parts.append("\n### Code Explanation\n")

            for segment in code_segments:

                parts.append(f"\n#### {segment['label']}\n")

                parts.append(create_code_block(segment['code'], "cs"))

        final_markdown = "\n".join(parts)
        
        # Extract slug for file_writer (try multiple sources with logging)
        slug = None
        
        # Try from workflow state
        if event.data.get("slug"):
            slug = event.data.get("slug")
            logger.debug(f"Got slug from workflow state: {slug}")
        
        # Try from SEO metadata
        if not slug and seo_metadata and seo_metadata.get("slug"):
            slug = seo_metadata.get("slug")
            logger.debug(f"Got slug from SEO metadata: {slug}")
        
        # Final fallback - generate from topic or use default
        if not slug:
            topic = event.data.get("topic", {})
            if topic.get("title"):
                from src.engine.slug_service import slugify
                slug = slugify(topic.get("title"))
                logger.info(f"Generated slug from topic title: {slug}")
            else:
                slug = "blog-post"
                logger.warning("Using fallback slug: blog-post")

        return AgentEvent(

            event_type="frontmatter_added",

            data={
                "markdown": final_markdown,
                "slug": slug,
                "seo_metadata": seo_metadata
            },

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

