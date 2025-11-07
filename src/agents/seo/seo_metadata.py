"""SEO Metadata Agent - Generates SEO metadata for blog posts."""

from typing import Optional, Dict, List, Any
from pathlib import Path
import logging
import json
import re

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


class SEOMetadataAgent(SelfCorrectingAgent, Agent):

    """Generates SEO metadata."""

    def __init__(self, config: Config, event_bus: EventBus,

                 llm_service: LLMService, trends_service: TrendsService):

        self.llm_service = llm_service

        self.trends_service = trends_service

        Agent.__init__(self, "SEOMetadataAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="SEOMetadataAgent",

            capabilities=["generate_seo"],

            input_schema={"type": "object", "required": ["content"]},

            output_schema=SCHEMAS.get("seo_metadata", {"type": "object"}),

            publishes=["seo_generated"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_generate_seo", self.execute)
    
    def _normalize_seo_payload(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize SEO payload from various provider formats with NO-MOCK validation.
        
        Handles:
        - Nested responses like {"metadata": {...}}
        - Synonym fields (metaTitle, seo_title, etc.)
        - String keywords/tags converted to arrays
        - Auto-generates slug if missing
        - Rejects mock/placeholder content
        
        Args:
            raw_data: Raw response from LLM provider
            
        Returns:
            Normalized dictionary with standard field names
        """
        from src.engine.slug_service import slugify
        from src.services.services_fixes import NoMockGate, SEOSchemaGate
        
        # Apply SEO schema normalization
        normalized = SEOSchemaGate.coerce_and_fill(raw_data)
        
        # Validate for mock content
        no_mock = NoMockGate()
        for field, value in normalized.items():
            if isinstance(value, str):
                if no_mock.contains_mock(value):
                    logger.warning(f"Mock content detected in SEO field '{field}': {value[:50]}...")
                    # Replace with sensible default
                    if field == 'title':
                        normalized[field] = 'Blog Post'
                    elif field == 'seoTitle':
                        normalized[field] = normalized.get('title', 'Blog Post')
                    elif field == 'description':
                        normalized[field] = f"Learn about {normalized.get('title', 'this topic')}"
                    elif field == 'slug':
                        normalized[field] = slugify(normalized.get('title', 'untitled'))
        
        # Final validation - ensure all required fields exist
        required = ['title', 'seoTitle', 'description', 'tags', 'keywords', 'slug']
        for field in required:
            if field not in normalized:
                logger.warning(f"Missing required SEO field: {field}")
                if field in ['tags', 'keywords']:
                    normalized[field] = []
                elif field == 'slug':
                    normalized[field] = slugify(normalized.get('title', 'untitled'))
                else:
                    normalized[field] = f"default-{field}"
        
        logger.info(f"SEO normalized: title='{normalized['title']}', slug='{normalized['slug']}'")
        return normalized

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        content = event.data.get("content", "")

        topic = event.data.get("topic", {})

        # Extract initial keywords

        keywords = extract_keywords(content, getattr(self.config, "seo_max_keywords", 8))

        # Try Gemini with retries

        max_retries = 3

        retry_delay = 1.0

        for attempt in range(max_retries):

            try:

                # Get trends data with sanitization

                trends_data = ""

                try:

                    raw_trends = self.trends_service.format_for_prompt(keywords[:3])

                    trends_data = raw_trends.replace('"', "'").replace('\n', ' ')[:500]

                except Exception as e:

                    logger.warning(f"Trends data unavailable: {e}")

                    trends_data = "No trend data available"

                prompt_template = PROMPTS.get("SEO_METADATA", {"system": "You are an SEO specialist. Generate valid JSON only.", "user": "Generate SEO metadata"})

                # Sanitize content

                safe_content = content[:2000].replace('"', "'").replace('\n', ' ')

                user_prompt = prompt_template["user"].format(

                    content_body=safe_content,

                    trends_data=trends_data,

                    json_schema=json.dumps(SCHEMAS.get("seo_metadata", {"type": "object"}), indent=2)

                )

                # Enhanced system prompt

                enhanced_system = prompt_template["system"] + "\n\nIMPORTANT: You must respond with valid JSON only. No explanations, no markdown, just pure JSON."

                logger.info(f"Calling Gemini for SEO metadata (attempt {attempt + 1}/{max_retries})")

                response = self.llm_service.generate(

                    prompt=user_prompt,

                    system_prompt=enhanced_system,

                    json_mode=True,

                    json_schema=SCHEMAS.get("seo_metadata", {"type": "object"}),

                    model=self.config.gemini_model,

                    provider="GEMINI"

                )

                # VALIDATE response before parsing

                if not response:

                    logger.warning(f"SEO generation returned None (attempt {attempt + 1})")

                    if attempt < max_retries - 1:

                        import time

                        time.sleep(retry_delay * (attempt + 1))

                        continue

                    else:

                        raise ValueError("Empty response from Gemini after all retries")

                response_stripped = response.strip()

                if not response_stripped:

                    logger.warning(f"SEO generation returned empty string (attempt {attempt + 1})")

                    if attempt < max_retries - 1:

                        import time

                        time.sleep(retry_delay * (attempt + 1))

                        continue

                    else:

                        raise ValueError("Empty response from Gemini after all retries")

                # Log preview

                logger.info(f"Gemini SEO response preview: {response_stripped[:100]}")

                # Clean up markdown if present

                if response_stripped.startswith('```'):

                    response_stripped = re.sub(r'^```json\s*', '', response_stripped)

                    response_stripped = re.sub(r'^```\s*', '', response_stripped)

                    response_stripped = re.sub(r'\s*```$', '', response_stripped)

                    response_stripped = response_stripped.strip()

                    logger.info("Removed markdown wrapper from SEO response")

                # Validate JSON structure

                try:

                    from src.utils.json_repair import safe_json_loads
                    seo_data = safe_json_loads(response_stripped, default={})
                    
                    # Normalize the payload (unwrap nested, map synonyms, etc.)
                    seo_data = self._normalize_seo_payload(seo_data)

                except json.JSONDecodeError as e:

                    logger.warning(f"SEO response is not valid JSON (attempt {attempt + 1}): {e}")

                    logger.warning(f"Response preview: {response_stripped[:200]}")

                    if attempt < max_retries - 1:

                        import time

                        time.sleep(retry_delay * (attempt + 1))

                        continue

                    else:

                        raise ValueError(f"Invalid JSON from Gemini after all retries: {e}")

                # Validate required fields

                required_fields = ['title', 'seoTitle', 'description', 'tags', 'slug', 'keywords']

                missing = [f for f in required_fields if f not in seo_data]

                if missing:

                    logger.warning(f"SEO response missing fields: {missing} (attempt {attempt + 1})")

                    if attempt < max_retries - 1:

                        import time

                        time.sleep(retry_delay * (attempt + 1))

                        continue

                    else:

                        raise ValueError(f"Incomplete SEO metadata: missing {missing}")

                # Post-process to ensure quality

                seo_data = self._enhance_seo_metadata(seo_data, topic, content)

                logger.info("Successfully generated SEO metadata via Gemini")

                return AgentEvent(

                    event_type="seo_generated",

                    data={"seo_metadata": seo_data},

                    source_agent=self.agent_id,

                    correlation_id=event.correlation_id

                )

            except Exception as e:

                logger.warning(f"SEO generation failed (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:

                    import time

                    time.sleep(retry_delay * (attempt + 1))

                    continue

                else:

                    logger.warning(f"SEO generation failed after {max_retries} attempts, using fallback")

                    break

        # All Gemini attempts failed; try Ollama provider before falling back.
        try:
            logger.info("Gemini failed, attempting Ollama fallback for SEO metadata")
            local_response = self.llm_service.generate(
                prompt=user_prompt,
                system_prompt=enhanced_system,
                json_mode=True,
                json_schema=SCHEMAS.get("seo_metadata", {"type": "object"}),
                model=self.config.ollama_topic_model,
                provider="OLLAMA"
            )
            if local_response:
                local_stripped = local_response.strip()
                # Clean up markdown if present
                if local_stripped.startswith('```'):
                    local_stripped = re.sub(r'^```json\s*', '', local_stripped)
                    local_stripped = re.sub(r'^```\s*', '', local_stripped)
                    local_stripped = re.sub(r'\s*```$', '', local_stripped)
                    local_stripped = local_stripped.strip()
                try:
                    from src.utils.json_repair import safe_json_loads
                    local_data = safe_json_loads(local_stripped, default={})
                    
                    # Normalize the payload (unwrap nested, map synonyms, etc.)
                    local_data = self._normalize_seo_payload(local_data)
                    
                    # Validate required fields
                    required_fields = ['title', 'seoTitle', 'description', 'tags', 'slug', 'keywords']
                    missing = [f for f in required_fields if f not in local_data]
                    if missing:
                        logger.warning(f"Ollama SEO response missing fields: {missing}, using fallback")
                        raise ValueError(f"Missing fields: {missing}")
                    local_data = self._enhance_seo_metadata(local_data, topic, content)
                    logger.info("Successfully generated SEO metadata via Ollama")
                    return AgentEvent(
                        event_type="seo_generated",
                        data={"seo_metadata": local_data},
                        source_agent=self.agent_id,
                        correlation_id=event.correlation_id
                    )
                except Exception as e:
                    logger.warning(f"Ollama provider returned invalid response: {e}, falling back to heuristic")
        except Exception as le:
            logger.warning(f"Ollama provider SEO generation failed: {le}, using fallback")
        # Return fallback SEO metadata
        logger.info("Using fallback SEO metadata")
        fallback_seo = self._create_fallback_seo(topic, content, keywords)

        return AgentEvent(

            event_type="seo_generated",

            data={"seo_metadata": fallback_seo},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

    def _enhance_seo_metadata(self, seo_data: Dict, topic: Dict, content: str) -> Dict:

        """Enhance and validate SEO metadata quality."""

        # Ensure title is different from seoTitle

        title = seo_data.get("title", "")

        seo_title = seo_data.get("seoTitle", title)

        # If they're the same or too similar, create variation

        if title == seo_title or title[:50] == seo_title[:50]:

            # Use topic title as base title

            title = topic.get("title", title)

            # Keep seoTitle optimized

            if len(seo_title) > getattr(self.config, "seo_title_max_length", 60):

                # Find last complete word within limit

                seo_title = self._truncate_at_word(seo_title, getattr(self.config, "seo_title_max_length", 60))

        # Ensure description is complete and different from title

        description = seo_data.get("description", "")

        if len(description) > getattr(self.config, "seo_description_max_length", 160):

            description = self._truncate_at_word(description, getattr(self.config, "seo_description_max_length", 160))

        # Ensure description doesn't just repeat title

        if description.startswith(title[:30]):

            # Extract a different sentence from content

            sentences = content.split('. ')

            for sentence in sentences[1:4]:  # Try sentences 2-4

                if len(sentence) >= 50 and len(sentence) <= getattr(self.config, "seo_description_max_length", 160):

                    description = sentence.strip()

                    if not description.endswith('.'):

                        description += '.'

                    break

        return {

            "title": title[:100] if title else "Blog Post",

            "seoTitle": seo_title,

            "description": description,

            "tags": seo_data.get("tags", [])[:10],

            "slug": seo_data.get("slug", topic.get("slug", "generated-post")),

            "keywords": seo_data.get("keywords", [])[:getattr(self.config, "seo_max_keywords", 8)]

        }

    def _create_fallback_seo(self, topic: Dict, content: str, keywords: List[str]) -> Dict:

        """Create fallback SEO metadata when LLM fails."""

        title = topic.get("title", "Blog Post")

        # Extract first sentence for description

        sentences = content.split('. ')

        description = sentences[0] if sentences else content[:160]

        description = self._truncate_at_word(description, getattr(self.config, "seo_description_max_length", 160))

        # Create SEO title (shorter, optimized version)

        seo_title = self._truncate_at_word(title, getattr(self.config, "seo_title_max_length", 60))

        return {

            "title": title[:100],

            "seoTitle": seo_title,

            "description": description,

            "tags": keywords[:5],

            "slug": topic.get("slug", "generated-post"),

            "keywords": keywords[:getattr(self.config, "seo_max_keywords", 8)]

        }

    def _truncate_at_word(self, text: str, max_length: int) -> str:

        """Truncate text at word boundary within max_length."""

        if len(text) <= max_length:

            return text

        # Find last space before max_length

        truncated = text[:max_length]

        last_space = truncated.rfind(' ')

        if last_space > max_length * 0.8:  # At least 80% of desired length

            return truncated[:last_space].strip()

        else:

            return truncated.strip()

