"""Conclusion Writer Agent - Writes blog post conclusions."""

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


class ConclusionWriterAgent(SelfCorrectingAgent, Agent):

    """Writes blog post conclusion."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "ConclusionWriterAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="ConclusionWriterAgent",

            capabilities=["write_conclusion"],

            input_schema={"type": "object", "required": ["sections", "topic"]},

            output_schema={"type": "object", "required": ["conclusion"]},

            publishes=["conclusion_written"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_write_conclusion", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        # Wrap execution with circuit breaker

        cb = self.config.resilience_manager.get_circuit_breaker("content_generation")

        pool = self.config.resilience_manager.get_resource_pool("content_agents")

        def _execute():

            with pool:

                sections = event.data.get("sections", [])

                topic = event.data.get("topic", {})

                if not sections:

                    raise ValueError("sections is required but was missing or empty")

                # Create summary of sections

                sections_summary = "\n".join([

                    f"- {s.get('title', 'Section')}: {s.get('content', '')[:200]}..."

                    for s in sections[:3]

                ])

                # Extract key points

                key_points = []

                for section in sections:

                    content = section.get('content', '')

                    # Extract first sentence of each section as key point

                    sentences = content.split('. ')

                    if sentences:

                        key_points.append(sentences[0])

                key_points_text = "\n".join([f"- {kp}" for kp in key_points[:5]])

                prompt_template = PROMPTS.get("CONCLUSION_WRITER", {"system": "You are a technical writing specialist.", "user": "Write conclusion"})

                user_prompt = prompt_template["user"].format(

                    sections_summary=sections_summary,

                    key_points=key_points_text

                )

                # Enhance prompt with tone configuration

                if self.config.tone_config:

                    user_prompt = build_section_prompt_enhancement(

                        self.config.tone_config,

                        'conclusion',

                        user_prompt

                    )

                try:

                    conclusion = self.llm_service.generate(

                        prompt=user_prompt,

                        system_prompt=prompt_template["system"],

                        json_mode=False,

                        model=self.config.ollama_content_model

                    )

                except Exception as e:

                    logger.error(f"Conclusion generation failed: {e}")

                    conclusion = self._generate_default_conclusion(topic)

                logger.info("Generated conclusion with tone configuration")

                return AgentEvent(

                    event_type="conclusion_written",

                    data={"conclusion": conclusion.strip()},

                    source_agent=self.agent_id,

                    correlation_id=event.correlation_id

                )

        return cb.call(_execute)

    def _generate_default_conclusion(self, topic: Dict) -> str:

        """Generate default conclusion if LLM fails."""

        topic_title = topic.get("title", "this topic")

        return f"""## Conclusion

In this comprehensive guide, we explored {topic_title} in detail. By following the steps outlined above, you can effectively implement this functionality in your .NET applications.

For more information and advanced use cases, please refer to the official documentation and support resources. If you have any questions or need assistance, don't hesitate to reach out to the community forums.

Start leveraging these powerful features in your projects today and experience the benefits of efficient, robust implementation."""

