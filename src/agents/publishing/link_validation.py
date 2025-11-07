"""Link Validation Agent - Validates links in content."""

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


class LinkValidationAgent(SelfCorrectingAgent, Agent):

    """Validates gist URLs."""

    def __init__(self, config: Config, event_bus: EventBus, link_checker: LinkChecker):

        self.link_checker = link_checker

        Agent.__init__(self, "LinkValidationAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="LinkValidationAgent",

            capabilities=["validate_links"],

            input_schema={"type": "object", "required": ["gist_urls"]},

            output_schema={"type": "object"},

            publishes=["links_validated"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_validate_links", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        # KILO: LinkValidationAgent — robust URL normalization

        gist_urls = event.data.get("gist_urls")

        urls = []

        if isinstance(gist_urls, dict):

            if "raw_urls" in gist_urls:

                raw = gist_urls.get("raw_urls") or {}

                if isinstance(raw, dict):

                    urls.extend([u for u in raw.values() if isinstance(u, str) and u.strip()])

                html = gist_urls.get("html_url")

                if isinstance(html, str) and html.strip():

                    urls.append(html)

            else:

                urls.extend([u for u in gist_urls.values() if isinstance(u, str) and u.strip()])

        elif isinstance(gist_urls, (list, tuple, set)):

            urls.extend([u for u in gist_urls if isinstance(u, str) and u.strip()])

        elif isinstance(gist_urls, str) and gist_urls.strip():

            urls.append(gist_urls)

        results = self.link_checker.validate_urls(urls) if urls else {}

        return AgentEvent(

            event_type="links_validated",

            data={"results": results},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

