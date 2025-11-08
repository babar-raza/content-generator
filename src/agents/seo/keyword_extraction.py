"""Keyword Extraction Agent - Extracts keywords from content."""

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


class KeywordExtractionAgent(SelfCorrectingAgent, Agent):

    """Extracts keywords from content."""

    def __init__(self, config: Config, event_bus: EventBus,

                 llm_service: LLMService, trends_service: TrendsService):

        self.llm_service = llm_service

        self.trends_service = trends_service

        Agent.__init__(self, "KeywordExtractionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="KeywordExtractionAgent",

            capabilities=["extract_keywords"],

            input_schema={"type": "object", "required": ["content"]},

            output_schema=SCHEMAS.get("keywords", {"type": "object"}),

            publishes=["keywords_extracted"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_extract_keywords", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        content = event.data.get("content", "")

        # Extract keywords using heuristic first (fallback)

        keywords = extract_keywords(content, getattr(self.config, "seo_max_keywords", 8))

        # Validate content before processing

        if not content or len(content.strip()) < 100:

            logger.warning("Content too short for keyword extraction, using heuristic only")

            return AgentEvent(

                event_type="keywords_extracted",

                data={"keywords": keywords},

                source_agent=self.agent_id,

                correlation_id=event.correlation_id

            )

        # Try Gemini with retries for transient failures

        max_retries = 3

        retry_delay = 1.0

        for attempt in range(max_retries):

            try:

                # Get trends data with sanitization

                trends_data = ""

                try:

                    raw_trends = self.trends_service.format_for_prompt(keywords[:3])

                    # Sanitize trends data to prevent JSON breaking

                    trends_data = raw_trends.replace('"', "'").replace('\n', ' ')[:500]

                except Exception as e:

                    logger.warning(f"Trends data unavailable: {e}")

                    trends_data = "No trend data available"

                # Build prompt with sanitized content

                prompt_template = PROMPTS.get("KEYWORD_EXTRACTION", {"system": "You are a keyword extraction specialist. Generate valid JSON only.", "user": "Extract keywords"})

                # Sanitize content to prevent prompt injection

                safe_content = content[:2000].replace('"', "'").replace('\n', ' ')

                user_prompt = prompt_template["user"].format(

                    content=safe_content,

                    trends_data=trends_data,

                    json_schema=json.dumps(SCHEMAS.get("keywords", {"type": "object"}), indent=2)

                )

                # Add explicit instruction for JSON output

                enhanced_system = prompt_template["system"] + "\n\nIMPORTANT: You must respond with valid JSON only. No explanations, no markdown, just pure JSON."

                logger.info(f"Calling Gemini for keyword extraction (attempt {attempt + 1}/{max_retries})")

                response = self.llm_service.generate(

                    prompt=user_prompt,

                    system_prompt=enhanced_system,

                    json_mode=True,

                    model=self.config.gemini_model,

                    provider="GEMINI"

                )

                # VALIDATE response thoroughly

                if not response:

                    logger.warning(f"Gemini returned None (attempt {attempt + 1})")

                    if attempt < max_retries - 1:

                        import time

                        time.sleep(retry_delay * (attempt + 1))

                        continue

                    else:

                        raise ValueError("Gemini returned None after all retries")

                response_stripped = response.strip()

                if not response_stripped:

                    logger.warning(f"Gemini returned empty string (attempt {attempt + 1})")

                    if attempt < max_retries - 1:

                        import time

                        time.sleep(retry_delay * (attempt + 1))

                        continue

                    else:

                        raise ValueError("Gemini returned empty string after all retries")

                # Log response preview for debugging

                logger.info(f"Gemini response preview: {response_stripped[:100]}")

                # Try to clean up response if it's wrapped in markdown

                if response_stripped.startswith('```'):

                    # Remove markdown code block

                    response_stripped = re.sub(r'^```json\s*', '', response_stripped)

                    response_stripped = re.sub(r'^```\s*', '', response_stripped)

                    response_stripped = re.sub(r'\s*```$', '', response_stripped)

                    response_stripped = response_stripped.strip()

                    logger.info("Removed markdown wrapper from response")

                # Validate JSON structure

                try:

                    keywords_data = json.loads(response_stripped)

                except json.JSONDecodeError as e:

                    logger.warning(f"Gemini response is not valid JSON (attempt {attempt + 1}): {e}")

                    logger.warning(f"Response preview: {response_stripped[:200]}")

                    if attempt < max_retries - 1:

                        import time

                        time.sleep(retry_delay * (attempt + 1))

                        continue

                    else:

                        raise ValueError(f"Invalid JSON from Gemini after all retries: {e}")

                # Validate we got keywords

                if not keywords_data.get("keywords"):

                    logger.warning(f"No keywords in Gemini response (attempt {attempt + 1})")

                    if attempt < max_retries - 1:

                        import time

                        time.sleep(retry_delay * (attempt + 1))

                        continue

                    else:

                        raise ValueError("No keywords in response after all retries")

                # Ensure keywords is a list

                extracted_keywords = keywords_data.get("keywords", [])

                if not isinstance(extracted_keywords, list):

                    logger.warning("Keywords field is not a list, converting")

                    extracted_keywords = [str(extracted_keywords)]

                # Filter out empty keywords

                extracted_keywords = [k for k in extracted_keywords if k and str(k).strip()]

                if not extracted_keywords:

                    logger.warning("All keywords were empty after filtering")

                    raise ValueError("No valid keywords after filtering")

                logger.info(f"Extracted {len(extracted_keywords)} keywords via Gemini")

                return AgentEvent(

                    event_type="keywords_extracted",

                    data={"keywords": extracted_keywords},

                    source_agent=self.agent_id,

                    correlation_id=event.correlation_id

                )

            except Exception as e:

                logger.warning(f"Gemini keyword extraction failed (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:

                    import time

                    time.sleep(retry_delay * (attempt + 1))

                    continue

                else:

                    # All retries exhausted, use heuristic fallback

                    logger.warning(f"Gemini keyword extraction failed after {max_retries} attempts, using heuristic fallback")

                    break

        # Fallback: Use heuristic keywords

        logger.info(f"Using heuristic fallback keywords: {len(keywords)} keywords")

        return AgentEvent(

            event_type="keywords_extracted",

            data={"keywords": keywords},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

