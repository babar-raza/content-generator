"""Section Writer Agent - Writes blog post sections."""

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


class SectionWriterAgent(SelfCorrectingAgent, Agent):

    """Writes detailed blog post sections."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):

        self.llm_service = llm_service

        Agent.__init__(self, "SectionWriterAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="SectionWriterAgent",

            capabilities=["write_sections"],

            input_schema={"type": "object", "required": ["outline", "intro"]},

            output_schema={"type": "object", "required": ["sections"]},

            publishes=["sections_written"]

        )

    def _subscribe_to_events(self):
        self.event_bus.subscribe("execute_write_sections", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        outline = event.data.get("outline", {})

        intro = event.data.get("intro", "")

        context = event.data.get("context", [])

        if not outline or not intro:

            raise ValueError("outline and intro are required but were missing or empty")

        sections = []

        section_list = outline.get("sections", [])

        logger.info(

            f"SECTION_WRITER_START | section_count={len(section_list)} | "

            f"intro_length={len(intro)} | context_chunks={len(context)} | "

            f"cid={event.correlation_id}"

        )

        # Generate each section

        for i, section in enumerate(section_list, 1):

            logger.info(

                f"SECTION_GEN_START | section={i}/{len(section_list)} | "

                f"title={section.get('title', 'N/A')} | "

                f"cid={event.correlation_id}"

            )

            prompt_template = PROMPTS.get("SECTION_WRITER", {"system": "You are a technical writing specialist.", "user": "Write section content"})

            user_prompt = prompt_template["user"].format(

                section_outline=json.dumps(section, indent=2),

                context="\n\n".join(context[:3]),

                intro=intro[:500]

            )

            # Enhance prompt with tone configuration for main_content section

            if self.config.tone_config:

                user_prompt = build_section_prompt_enhancement(

                    self.config.tone_config,

                    'main_content',

                    user_prompt

                )

            try:

                section_content = self.llm_service.generate(

                    prompt=user_prompt,

                    system_prompt=prompt_template["system"],

                    json_mode=False,

                    model=self.config.ollama_content_model

                )

                logger.info(

                    f"SECTION_GEN_SUCCESS | section={i}/{len(section_list)} | "

                    f"length={len(section_content)} | "

                    f"cid={event.correlation_id}"

                )

            except Exception as e:

                logger.error(

                    f"SECTION_GEN_FAIL | section={i}/{len(section_list)} | "

                    f"error={type(e).__name__}: {str(e)} | "

                    f"cid={event.correlation_id}",

                    exc_info=True

                )

                raise

            # Clean the generated section content before storing it
            cleaned_content = section_content or ""
            try:
                # Remove a heading at the top that matches the section title
                lines = cleaned_content.split('\n')
                if lines:
                    first_line = lines[0].strip()
                    m = re.match(r'^#{1,6}\s+(.+)$', first_line)
                    if m:
                        heading_text = m.group(1).strip().lower().strip(':.,;!?')
                        title_norm = section.get("title", "").strip().lower().strip(':.,;!?')
                        if heading_text == title_norm:
                            start = 1
                            if len(lines) > 1 and not lines[1].strip():
                                start += 1
                            cleaned_content = '\n'.join(lines[start:])
                # Enforce maximum section length if defined in templates
                max_len = None
                try:
                    blog_tmpl = self.config.templates.get('blog_templates', {}).get(self.config.active_blog_template, {})
                    assembly_rules = blog_tmpl.get('assembly_rules', {})
                    max_len = assembly_rules.get('max_section_length')
                except Exception:
                    max_len = None
                if max_len and isinstance(max_len, int) and len(cleaned_content) > max_len:
                    truncated = cleaned_content[:max_len]
                    last_space = truncated.rfind(' ')
                    if last_space > 0:
                        truncated = truncated[:last_space]
                    cleaned_content = truncated + '...'
            except Exception:
                cleaned_content = section_content or ""
            sections.append({
                "title": section["title"],
                "content": cleaned_content.strip()
            })

        logger.info(

            f"SECTION_WRITER_COMPLETE | generated={len(sections)} sections | "

            f"cid={event.correlation_id}"

        )

        return AgentEvent(

            event_type="sections_written",

            data={"sections": sections},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

