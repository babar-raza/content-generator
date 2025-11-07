"""Error Recovery Agent - Handles and recovers from errors."""

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


class ErrorRecoveryAgent(SelfCorrectingAgent, Agent):

    """Handles help requests and proposes alternatives."""

    def __init__(self, config: Config, event_bus: EventBus, registry):

        self.registry = registry

        Agent.__init__(self, "ErrorRecoveryAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="ErrorRecoveryAgent",

            capabilities=["recover_errors"],

            input_schema={"type": "object", "required": ["agent_id", "required_capabilities"]},

            output_schema={"type": "object"},

            publishes=["help_response"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("help_request", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        agent_id = event.data.get("agent_id")

        required_caps = event.data.get("required_capabilities", [])

        if not agent_id:

            raise ValueError("agent_id is required but was missing or empty")

        if not required_caps:

            raise ValueError("required_capabilities is required but was missing or empty")

        # Find alternate agents

        alternates = []

        for cap in required_caps:

            agents = self.registry.find_agents_by_capability(cap)

            for agent in agents:

                if agent.agent_id != agent_id:

                    alternates.append(agent.agent_id)

        return AgentEvent(

            event_type="help_response",

            data={

                "original_agent": agent_id,

                "alternate_agents": list(set(alternates)),

                "suggestion": "Try alternate agent or provider failover"

            },

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

