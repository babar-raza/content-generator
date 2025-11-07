"""Gist Upload Agent - Uploads code to GitHub Gist."""

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


class GistUploadAgent(SelfCorrectingAgent, Agent):

    """Uploads code to GitHub Gist."""

    def __init__(self, config: Config, event_bus: EventBus, gist_service: GistService):

        self.gist_service = gist_service

        Agent.__init__(self, "GistUploadAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="GistUploadAgent",

            capabilities=["upload_gist"],

            input_schema={"type": "object", "required": ["readme", "code", "topic_slug"]},

            output_schema={"type": "object"},

            publishes=["gist_uploaded", "gist_failed"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_upload_gist", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        # KILO: GistUploadAgent — filename must match current topic_slug

        readme = event.data.get("readme", "") or ""

        code = event.data.get("code", "") or ""

        topic_slug = (event.data.get("topic_slug") or "").strip()

        if not topic_slug:

            raise ValueError("topic_slug is required but was missing")

        filename = self.gist_service.generate_filename(topic_slug, extension="cs")

        files = { filename: code, "README.md": readme }

        gist_result = self.gist_service.create_gist(

            files=files,

            description=f"Example code for {topic_slug}",

            public=True

        )

        gist_result["filename"] = filename  # critical for downstream agents

        return AgentEvent(

            event_type="gist_uploaded",

            data=gist_result,  # contains gist_id, owner, urls, filename

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

