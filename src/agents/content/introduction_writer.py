"""Introduction Writer Agent - Writes blog post introductions."""

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


class IntroductionWriterAgent(SelfCorrectingAgent, Agent):

    """Writes engaging blog post introduction."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "IntroductionWriterAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="IntroductionWriterAgent",

            capabilities=["write_introduction"],

            input_schema={"type": "object", "required": ["outline"]},

            output_schema={"type": "object", "required": ["introduction"]},

            publishes=["introduction_written"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_write_introduction", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        outline = event.data.get("outline", {})

        # Get base prompt template

        prompt_template = PROMPTS.get("INTRODUCTION_WRITER", {"system": "You are a technical writing specialist.", "user": "Write introduction"})

        user_prompt = prompt_template["user"].format(

            outline=json.dumps(outline, indent=2)

        )

        # Enhance prompt with tone configuration

        if self.config.tone_config:

            user_prompt = build_section_prompt_enhancement(

                self.config.tone_config,

                'introduction',

                user_prompt

            )

        intro = self.llm_service.generate(

            prompt=user_prompt,

            system_prompt=prompt_template["system"],

            json_mode=False,

            model=self.config.ollama_content_model

        )

        logger.info("Generated introduction with tone configuration")

        return AgentEvent(

            event_type="introduction_written",

            data={"introduction": intro.strip()},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

