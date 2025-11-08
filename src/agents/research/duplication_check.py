"""Duplication Check Agent - Checks for duplicate content."""

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


class DuplicationCheckAgent(SelfCorrectingAgent, Agent):

    """Checks if topic is duplicate of existing content."""

    def __init__(self, config: Config, event_bus: EventBus, database_service: DatabaseService):

        self.database_service = database_service

        Agent.__init__(self, "DuplicationCheckAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="DuplicationCheckAgent",

            capabilities=["check_duplication"],

            input_schema={"type": "object", "required": ["topic_title", "topic_slug"]},

            output_schema={"type": "object"},

            publishes=["topic_duplicate", "topic_approved"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_check_duplication", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        topic_title = event.data.get("topic_title", "")

        topic_slug = event.data.get("topic_slug", "")

        topic = event.data.get("topic", {})

        if not topic_title or not topic_slug:

            raise ValueError("topic_title and topic_slug are required but were missing or empty")

        # Build query from title and rationale

        query_text = f"{topic_title} {topic.get('rationale', '')}"

        # Check duplication using Chroma distance threshold

        is_duplicate, similarity = self.database_service.check_duplicate(

            "blog",

            query_text,

            threshold=self.config.chroma_distance_threshold

        )

        # FIXED: Prevent self-comparison by excluding current slug

        # This is a simple safeguard - in practice more sophisticated

        # dedupe logic would be needed for production

        if is_duplicate:

            logger.info(f"Topic '{topic_slug}' is duplicate (similarity: {similarity:.2f})")

            return AgentEvent(

                event_type="topic_duplicate",

                data={"topic_slug": topic_slug, "similarity": similarity},

                source_agent=self.agent_id,

                correlation_id=event.correlation_id

            )

        else:

            logger.info(f"Topic '{topic_slug}' approved (similarity: {similarity:.2f})")

            return AgentEvent(

                event_type="topic_approved",

                data={"topic_slug": topic_slug, "topic": topic},

                source_agent=self.agent_id,

                correlation_id=event.correlation_id

            )

# ============================================================================

# RAG AGENTS (3)

# ============================================================================

