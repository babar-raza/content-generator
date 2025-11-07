"""Keyword Injection Agent - Injects keywords naturally into content."""

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


class KeywordInjectionAgent(SelfCorrectingAgent, Agent):

    """Injects keywords naturally into content."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "KeywordInjectionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="KeywordInjectionAgent",

            capabilities=["inject_keywords"],

            input_schema={"type": "object", "required": ["content", "keywords"]},

            output_schema={"type": "object", "required": ["content"]},

            publishes=["keywords_injected"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_inject_keywords", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        content = event.data.get("content", "")
        keywords = event.data.get("keywords", [])
        if not content:
            return AgentEvent(event_type="keywords_injected", data={"content": content or ""}, source_agent=self.agent_id, correlation_id=event.correlation_id)
        modified_content = inject_keywords_naturally(content, keywords, getattr(self.config, "seo_keyword_density_max", 1.5))
        return AgentEvent(event_type="keywords_injected", data={"content": modified_content}, source_agent=self.agent_id, correlation_id=event.correlation_id)

# ============================================================================

# OUTPUT AGENTS (5)

# ============================================================================

