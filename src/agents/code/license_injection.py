"""License Injection Agent - Injects license headers into code."""

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


class LicenseInjectionAgent(SelfCorrectingAgent, Agent):

    """Injects license header into code."""

    def __init__(self, config: Config, event_bus: EventBus):

        Agent.__init__(self, "LicenseInjectionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="LicenseInjectionAgent",

            capabilities=["inject_license"],

            input_schema={"type": "object", "required": ["code"]},

            output_schema={"type": "object", "required": ["code"]},

            publishes=["license_injected"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_inject_license", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        code = event.data.get("code", "")

        license_text = CSHARP_LICENSE_HEADER.replace(

            "[Company Name - Placeholder for LLM]",

            self.config.company_name

        )

        licensed_code = insert_license(code, license_text)

        return AgentEvent(

            event_type="license_injected",

            data={"code": licensed_code},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

# agents.py (continued)

