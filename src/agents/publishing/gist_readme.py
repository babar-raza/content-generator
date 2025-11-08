"""Gist README Agent - Generates README for Gists."""

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


class GistREADMEAgent(SelfCorrectingAgent, Agent):

    """Creates README for Gist."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "GistREADMEAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="GistREADMEAgent",

            capabilities=["create_gist_readme"],

            input_schema={"type": "object", "required": ["code", "metadata"]},

            output_schema={"type": "object", "required": ["readme"]},

            publishes=["readme_generated"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_create_gist_readme", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        code = event.data.get("code", "")

        metadata = event.data.get("metadata", {})

        if not code:

            raise ValueError("code is required but was missing or empty")

        if "metadata" not in event.data:

            raise ValueError("metadata is required but was missing")

        prompt_template = PROMPTS.get("GIST_README", {"system": "You are a documentation specialist.", "user": "Create README for code"})

        user_prompt = prompt_template["user"].format(

            code=code[:1000],

            metadata=json.dumps(metadata, indent=2)

        )

        readme = self.llm_service.generate(

            prompt=user_prompt,

            system_prompt=prompt_template["system"],

            json_mode=False

        )

        readme = self._strip_links(readme or "")

        return AgentEvent(

            event_type="readme_generated",

            data={"readme": readme.strip()},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

    def _strip_links(self, md: str) -> str:

        # Remove markdown links [text](url) -> text

        return re.sub(r'\[([^\]]+)\]\((?!mailto:)[^)]+\)', r'\1', md)

