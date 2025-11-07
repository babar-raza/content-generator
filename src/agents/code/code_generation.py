"""Code Generation Agent - Generates code examples."""

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


class CodeGenerationAgent(SelfCorrectingAgent, Agent):

    """Generates complete C# code examples."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "CodeGenerationAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:
        return AgentContract(
            agent_id="CodeGenerationAgent",
            capabilities=["generate_code"],
            input_schema={"type": "object", "required": ["topic", "context_api"]},
            output_schema={"type": "object", "required": ["code_blocks"]},
            publishes=["code_generated"]
        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_generate_code", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        topic = event.data.get("topic", {})

        context_api = event.data.get("context_api", [])

        if not topic or not topic.get('title'):

            raise ValueError("topic with title is required but was missing or empty")

        prompt_template = PROMPTS.get("CODE_GENERATION", {"system": "You are a C# code generation specialist.", "user": "Generate C# code"})

        user_prompt = prompt_template["user"].format(

            topic_description=topic.get("title", ""),

            api_context="\n\n".join(context_api[:5])

        )

        code = self.llm_service.generate(

            prompt=user_prompt,

            system_prompt=prompt_template["system"],

            json_mode=False,

            model=self.config.ollama_code_model

        )

        return AgentEvent(

            event_type="code_generated",

            data={"code": code.strip()},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

