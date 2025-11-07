"""Code Validation Agent - Validates code quality and correctness."""

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


class CodeValidationAgent(SelfCorrectingAgent, Agent):

    """Validates C# code quality and API compliance."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "CodeValidationAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="CodeValidationAgent",

            capabilities=["validate_code"],

            input_schema={"type": "object", "required": ["code"]},

            output_schema=SCHEMAS.get("code_validation", {"type": "object"}),

            publishes=["code_validated", "code_invalid"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_validate_code", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        code = event.data.get("code", "")

        api_refs = event.data.get("api_references", [])

        if not code:

            raise ValueError("code is required but was missing or empty")

        # Static validation

        is_valid, issues = validate_code_quality(code, getattr(self.config, "validation_mode", "basic"))

        # API compliance

        is_compliant, warnings = validate_api_compliance(code, api_refs)

        # Add warnings as minor issues

        for warning in warnings:

            issues.append({"type": "minor", "message": warning, "location": "api"})

        # Escalate warnings/minor issues to critical when strict

        if self.config.warnings_as_errors:

            for issue in issues:

                if issue.get("type") == "minor":

                    issue["type"] = "critical"

        critical_issues = [i for i in issues if i["type"] == "critical"]

        if critical_issues:

            return AgentEvent(

                event_type="code_invalid",

                data={"issues": issues},

                source_agent=self.agent_id,

                correlation_id=event.correlation_id

            )

        return AgentEvent(

            event_type="code_validated",

            data={"issues": issues},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

