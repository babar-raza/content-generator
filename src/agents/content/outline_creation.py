"""Outline Creation Agent - Creates blog post outlines."""

from typing import Optional, Dict, List, Any
from pathlib import Path
import logging
import json

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

        # Validate that we have context (warn if missing but don't fail)
        if not context_kb and not context_blog:
            logger.warning("No context from KB or blog, generating outline with topic only")
            combined_context = ""
        else:
            # Combine context
            combined_context = "\n\n".join(context_kb[:3] + context_blog[:2])

        prompt_template = PROMPTS.get("OUTLINE_CREATION", {"system": "You are a technical writing specialist.", "user": "Create outline for topic"})

        # Extract topic fields
        topic_title = topic.get("title", "") if isinstance(topic, dict) else str(topic)
        topic_description = topic.get("description", "") if isinstance(topic, dict) else ""

        user_prompt = prompt_template["user"].format(

            topic_title=topic_title,

            topic_description=topic_description,

            json_schema=json.dumps(SCHEMAS.get("outline", {"type": "object"}), indent=2)

        )

        response = self.llm_service.generate(

            prompt=user_prompt,

            system_prompt=prompt_template["system"],

            json_mode=True,

            json_schema=SCHEMAS.get("outline", {"type": "object"}),

            model=self.config.ollama_content_model

        )
        
        from src.utils.json_repair import safe_json_loads
        outline_data = safe_json_loads(response, default={})
        
        # Normalize response structure - handle various formats
        if not isinstance(outline_data, dict):
            # If it's a list, wrap it
            if isinstance(outline_data, list):
                outline_data = {"sections": outline_data}
            else:
                outline_data = {"sections": []}
        
        # If sections key is missing, try to extract or create it
        if "sections" not in outline_data:
            # Try common alternative keys
            found_sections = False
            for key in ["outline", "content", "structure", "body", "chapters", "topics"]:
                if key in outline_data:
                    value = outline_data[key]
                    if isinstance(value, list):
                        outline_data["sections"] = value
                        found_sections = True
                        break
                    elif isinstance(value, dict) and "sections" in value:
                        outline_data["sections"] = value["sections"]
                        found_sections = True
                        break
            
            # If still no sections found, try to extract from nested structures
            if not found_sections:
                # Look for any list in the structure that might be sections
                for key, value in outline_data.items():
                    if isinstance(value, list) and len(value) > 0:
                        # Check if list items look like sections (have title/heading)
                        first_item = value[0]
                        if isinstance(first_item, dict) and any(k in first_item for k in ["title", "heading", "name", "section"]):
                            outline_data["sections"] = value
                            found_sections = True
                            break
            
            # Last resort: wrap the entire dict as a single section
            if not found_sections:
                if outline_data:
                    outline_data["sections"] = [outline_data.copy()]
                else:
                    outline_data["sections"] = []
        
        # Ensure sections is a list
        if not isinstance(outline_data.get("sections"), list):
            outline_data["sections"] = []

        logger.info(f"Created outline with {len(outline_data['sections'])} sections")

        return AgentEvent(

            event_type="outline_created",

            data=outline_data,

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

