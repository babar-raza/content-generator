"""Outline Creation Agent - Creates blog post outlines."""

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


class OutlineCreationAgent(SelfCorrectingAgent, Agent):

    """Creates structured outline for blog post."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "OutlineCreationAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="OutlineCreationAgent",

            capabilities=["create_outline"],

            input_schema={"type": "object", "required": ["topic"]},

            output_schema=SCHEMAS.get("outline", {"type": "object"}),

            publishes=["outline_created"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_create_outline", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        topic = event.data.get("topic", {})

        context_kb = event.data.get("context_kb", [])

        context_blog = event.data.get("context_blog", [])

        # Validate that we have context

        if not context_kb and not context_blog:

            raise ValueError("ValidationFail: Both context_kb and context_blog are missing")

        # Combine context

        combined_context = "\n\n".join(context_kb[:3] + context_blog[:2])

        prompt_template = PROMPTS.get("OUTLINE_CREATION", {"system": "You are a technical writing specialist.", "user": "Create outline for topic"})

        user_prompt = prompt_template["user"].format(

            topic=json.dumps(topic),

            context=combined_context[:3000],

            json_schema=json.dumps(SCHEMAS.get("outline", {"type": "object"}), indent=2)

        )

        response = self.llm_service.generate(

            prompt=user_prompt,

            system_prompt=prompt_template["system"],

            json_mode=True,

            json_schema=SCHEMAS.get("outline", {"type": "object"}),

            model=self.config.ollama_content_model

        )

        outline_data = json.loads(response)

        logger.info(f"Created outline with {len(outline_data['sections'])} sections")

        return AgentEvent(

            event_type="outline_created",

            data=outline_data,

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

