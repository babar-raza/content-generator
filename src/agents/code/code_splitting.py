"""Code Splitting Agent - Splits code into manageable segments."""

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


class CodeSplittingAgent(SelfCorrectingAgent, Agent):

    """Splits code into segments for explanation."""

    def __init__(self, config: Config, event_bus: EventBus):

        Agent.__init__(self, "CodeSplittingAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="CodeSplittingAgent",

            capabilities=["split_code"],

            input_schema={"type": "object", "required": ["code"]},

            output_schema={"type": "object", "required": ["segments"]},

            publishes=["code_split"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_split_code", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        code = event.data.get("code", "")

        segments = split_code_into_segments(

            code,

            min_lines=getattr(self.config, "code_min_lines", 5),

            max_lines=getattr(self.config, "code_max_lines", 15),

            min_segments=getattr(self.config, "code_min_segments", 3),

            max_segments=getattr(self.config, "code_max_segments", 5),

            config=self.config

        )

        return AgentEvent(

            event_type="code_split",

            data={"segments": segments},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

# ============================================================================

# SEO AGENTS (3)

# ============================================================================

