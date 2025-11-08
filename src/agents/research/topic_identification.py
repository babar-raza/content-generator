"""Topic Identification Agent - Identifies and validates blog topics."""

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


class TopicIdentificationAgent(SelfCorrectingAgent, Agent):

    """Identifies blog post topics from KB article."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "TopicIdentificationAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="TopicIdentificationAgent",

            capabilities=["identify_blog_topics"],

            input_schema={"type": "object", "required": ["kb_article_content"]},

            output_schema=SCHEMAS.get("topics_identified", {"type": "object"}),

            publishes=["topics_identified"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_identify_blog_topics", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        kb_content = event.data.get("kb_article_content", "")

        if not kb_content:

            raise ValueError("No KB content provided")

        prompt_template = PROMPTS.get("TOPIC_IDENTIFICATION", {"system": "You are a technical content specialist.", "user": "Identify topics from KB content"})

        user_prompt = prompt_template["user"].format(

            kb_article_content=kb_content[:5000],

            json_schema=json.dumps(SCHEMAS.get("topics_identified", {"type": "object"}), indent=2)

        )

        response = self.llm_service.generate(

            prompt=user_prompt,

            system_prompt=prompt_template["system"],

            json_mode=True,

            json_schema=SCHEMAS.get("topics_identified", {"type": "object"}),

            model=self.config.ollama_topic_model

        )

        topics_data = json.loads(response)

        logger.info(f"Identified {len(topics_data['topics'])} topics")

        return AgentEvent(

            event_type="topics_identified",

            data=topics_data,

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

