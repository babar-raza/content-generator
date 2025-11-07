"""Code Extraction Agent - Extracts code blocks from content."""

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


class CodeExtractionAgent(SelfCorrectingAgent, Agent):

    """Safety net to extract accidental code from prose."""

    def __init__(self, config: Config, event_bus: EventBus):

        Agent.__init__(self, "CodeExtractionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="CodeExtractionAgent",

            capabilities=["extract_code"],

            input_schema={"type": "object", "required": ["content"]},

            output_schema={"type": "object"},

            publishes=["code_extracted"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_extract_code", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        content = event.data.get("content", "")

        code_blocks = extract_code_blocks(content)

        return AgentEvent(

            event_type="code_extracted",

            data={"code_blocks": code_blocks},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

