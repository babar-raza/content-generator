"""Model Selection Agent - Selects appropriate LLM model."""

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


class ModelSelectionAgent(SelfCorrectingAgent, Agent):

    """Selects best Ollama model for capability."""

    def __init__(self, config: Config, event_bus: EventBus, performance_tracker):

        self.performance_tracker = performance_tracker

        Agent.__init__(self, "ModelSelectionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="ModelSelectionAgent",

            capabilities=["select_model"],

            input_schema={"type": "object", "required": ["capability"]},

            output_schema=SCHEMAS.get("model_selection", {"type": "object"}),

            publishes=["model_selected"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("model_selection_request", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        capability = event.data.get("capability", "")

        # Get available models using new detector
        try:
            from src.utils.ollama_detector import get_ollama_detector
            
            detector = get_ollama_detector()
            available, status = detector.is_ollama_available()
            
            if available:
                # Use the best model for the capability
                model = detector.get_best_model_for_capability(capability.lower())
                
                if not model:
                    # Fallback to config defaults
                    if any(kw in capability.lower() for kw in ["code", "validate", "split"]):
                        model = self.config.ollama_code_model
                    elif any(kw in capability.lower() for kw in ["content", "write", "generate"]):
                        model = self.config.ollama_content_model
                    else:
                        model = self.config.ollama_topic_model
            else:
                # Fallback to config defaults
                if any(kw in capability.lower() for kw in ["code", "validate", "split"]):
                    model = self.config.ollama_code_model
                elif any(kw in capability.lower() for kw in ["content", "write", "generate"]):
                    model = self.config.ollama_content_model
                else:
                    model = self.config.ollama_topic_model
        
        except Exception as e:
            logger.warning(f"Failed to use Ollama detector, falling back to config: {e}")
            # Fallback to config defaults
            if any(kw in capability.lower() for kw in ["code", "validate", "split"]):
                model = self.config.ollama_code_model
            elif any(kw in capability.lower() for kw in ["content", "write", "generate"]):
                model = self.config.ollama_content_model
            else:
                model = self.config.ollama_topic_model

        return AgentEvent(

            event_type="model_selected",

            data={"model_name": model},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )


