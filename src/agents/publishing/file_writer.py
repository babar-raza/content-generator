"""File Writer Agent - Writes final blog files to disk."""

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


class FileWriterAgent(SelfCorrectingAgent, Agent):

    """Writes final blog post to file."""

    def __init__(self, config: Config, event_bus: EventBus):

        Agent.__init__(self, "FileWriterAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="FileWriterAgent",

            capabilities=["write_file"],

            input_schema={"type": "object", "required": ["markdown", "slug"]},

            output_schema={"type": "object"},

            publishes=["blog_post_complete"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_write_file", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        markdown = event.data.get("markdown", "")

        slug = event.data.get("slug", "untitled")

        if "slug" not in event.data:

            raise ValueError("slug is required but was missing")

        write_markdown_tree(self.config.output_dir, slug, markdown)

        return AgentEvent(

            event_type="blog_post_complete",

            data={"slug": slug, "status": "complete"},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

# ============================================================================

# META AGENTS (2)

# ============================================================================

