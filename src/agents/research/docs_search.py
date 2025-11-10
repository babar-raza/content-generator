"""Docs Search Agent - Searches documentation for relevant context."""

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


class DocsSearchAgent(SelfCorrectingAgent, Agent):

    """Searches documentation for relevant context."""

    def __init__(self, config: Config, event_bus: EventBus, database_service: DatabaseService):

        self.database_service = database_service

        Agent.__init__(self, "DocsSearchAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="DocsSearchAgent",

            capabilities=["gather_rag_docs"],

            input_schema={"type": "object", "required": ["query"]},

            output_schema={"type": "object", "required": ["source", "context"]},

            publishes=["rag_complete"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_gather_rag_docs", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        # Build query
        if "topic" in event.data:

            topic = event.data["topic"]

            query = build_query(topic, "general")

        else:

            query = event.data.get("query", "")

        # Search docs content
        results = self.database_service.query(

            "docs",

            query,

            top_k=self.config.rag_top_k

        )

        # Extract documents
        context = results.get("documents", [[]])[0] if results.get("documents") else []

        # Deduplicate
        context = dedupe_context(context)

        logger.info(f"Found {len(context)} docs context chunks")

        return AgentEvent(

            event_type="rag_complete",

            data={"source": "docs", "context": context},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )
