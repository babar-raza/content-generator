"""Content Assembly Agent - Assembles final blog content."""

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

from src.utils.dedup_utils import deduplicate_headings


class ContentAssemblyAgent(SelfCorrectingAgent, Agent):

    """Assembles final blog post content from parts using templates."""

    def __init__(self, config: Config, event_bus: EventBus):

        Agent.__init__(self, "ContentAssemblyAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="ContentAssemblyAgent",

            capabilities=["assemble_content"],

            input_schema={"type": "object", "required": ["intro", "sections"]},

            output_schema={"type": "object", "required": ["content"]},

            publishes=["content_generated"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_assemble_content", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        """        Assemble final blog content. Guarantees 'intro' is present.

        Falls back to synthesis if upstream omitted it."""

        # Extract data from event payload

        intro = event.data.get("intro", "")

        sections = event.data.get("sections", [])

        conclusion = event.data.get("conclusion", "")

        supplementary = event.data.get("supplementary", {})

        outline = event.data.get("outline", {})

        meta = event.data.get("meta", {})

        topic_slug = event.data.get("slug") or event.data.get("topic_slug", "untitled-topic")

        # 1) If intro missing/empty -> synthesize from outline/sections/meta

        if not intro or not str(intro).strip():

            logger.warning(

                f"intro missing for topic {topic_slug}, synthesizing... (cid={event.correlation_id})"

            )

            self.event_bus.publish(AgentEvent(

                event_type="agent_progress",

                data={

                    "agent": self.agent_id,

                    "phase": "assemble_content",

                    "message": "intro missing, synthesizing...",

                    "topic": topic_slug,

                },

                source_agent=self.agent_id,

                correlation_id=event.correlation_id

            ))

            intro = self._synthesize_intro(

                topic=topic_slug, outline=outline, sections=sections, meta=meta

            )

            # As a final safety net

            if not intro or not str(intro).strip():

                intro = self._fallback_intro_from_sections(sections) or\
                        f"## Introduction\n\n{topic_slug.replace('-', ' ').title()} — overview."

            logger.info(f"Synthesized intro: {len(intro)} chars (cid={event.correlation_id})")

        # 2) Validate minimally but do not raise for intro

        if not isinstance(sections, list):

            sections = []

        # 3) Use template-driven assembly based on blog_templates.yaml

        blog_template = self._get_blog_template()

        # CRITICAL: Pass the entire event.data so _assemble_from_template can access code data

        content = self._assemble_from_template(

            blog_template, intro, sections, conclusion, supplementary, event.data

        )

        logger.info(

            f"Assembled content ({len(content)} chars, {len(sections)} main sections, "

            f"{len(supplementary)} supplementary sections) (cid={event.correlation_id})"

        )

        return AgentEvent(

            event_type="content_generated",

            data={"content": content},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

    def _synthesize_intro(self, topic: str, outline: Dict, sections: List[Dict], meta: Dict) -> str:

        """Synthesize introduction from available context when missing."""

        try:

            # Use outline title and first section

            title = outline.get('title', topic)

            first_section = sections[0] if sections else {}

            first_content = first_section.get('content', '')[:300]

            intro = f"{title}\n\n"

            if first_content:

                # Extract first 2 sentences

                sentences = first_content.split('. ')[:2]

                intro += '. '.join(sentences) + '.'

            else:

                intro += f"This guide covers {topic.replace('-', ' ')}."

            return intro

        except Exception as e:

            logger.error(f"Failed to synthesize intro: {e}")

            return f"## Introduction\n\nThis guide covers {topic.replace('-', ' ')}."

    def _fallback_intro_from_sections(self, sections: List[Dict]) -> str:

        """Create basic intro from first section as absolute fallback."""

        if not sections:

            return ""

        first_section = sections[0]

        content = first_section.get('content', '')

        # Take first paragraph

        paragraphs = content.split('\n\n')

        if paragraphs:

            return f"## Introduction\n\n{paragraphs[0]}"

        return ""

    def _get_blog_template(self) -> Dict[str, Any]:

        """Get blog template from config with better fallback logic."""

        try:

            blog_templates = self.config.templates.get('blog_templates', {})

            blog_structure = blog_templates.get('blog_structure', {})

            # Choose template based on content analysis

            template_name = self._determine_template_type()

            template = blog_structure.get(template_name, blog_structure.get('default'))

            if template:

                logger.info(f"Using blog template: {template_name}")

                return template

        except Exception as e:

            logger.error(f"Error loading blog template: {e}")

        # Enhanced fallback with code-first structure

        logger.warning("Using enhanced fallback blog template")

        return {

            'sections': [

                'introduction',

                'code_implementation',     # Early!

                'code_explanation',        # After code

                'prerequisites',           # After showing value

                'main_content',

                'troubleshooting',

                'faq',

                'use_cases',

                'best_practices',

                'conclusion'

            ],

            'section_spacing': '\n\n'

        }

    def _determine_template_type(self) -> str:

        """Determine which template to use based on content analysis."""

        # Default to tutorial format for technical content

        return 'tutorial'

    def _get_section_heading(self, section_name: str) -> str:
        """Get the template-defined heading for a section.

        Returns the heading from blog_templates.yaml section_templates,
        or a default heading if not found."""
        try:
            blog_templates = self.config.templates.get('blog_templates', {})
            section_templates = blog_templates.get('section_templates', {})
            section_config = section_templates.get(section_name, {})
            heading = section_config.get('heading', '')

            if heading:
                # Template headings already include level markers (##)
                return heading + '\n'
        except Exception as e:
            logger.warning(f"Could not load template heading for {section_name}: {e}")

        # Fallback to default heading format
        default_headings = {
            'introduction': '## Introduction\n',
            'prerequisites': '## Prerequisites\n',
            'code_implementation': '## Code Implementation\n',
            'code_explanation': '## Code Explanation\n',
            'troubleshooting': '## Troubleshooting & Common Issues\n',
            'faq': '## FAQs\n',
            'use_cases': '## Use Cases and Applications\n',
            'best_practices': '## Best Practices: Quick Reference Table\n',
            'supported_formats': '## Supported Input/Output Formats\n',
            'conclusion': '## Conclusion\n'
        }
        return default_headings.get(section_name, f'## {section_name.title()}\n')

    def _assemble_from_template(

        self,

        blog_template: Dict[str, Any],

        intro: str,

        sections: List[Dict],

        conclusion: str,

        supplementary: Dict[str, Any],

        event_data: Dict[str, Any]

    ) -> str:

        """Assemble content following template structure with code-first approach."""

        parts = []

        section_order = blog_template.get('sections', [])

        section_spacing = blog_template.get('section_spacing', '\n\n')

        # Extract code-related data from event_data

        code_segments = event_data.get("code_segments", [])

        validated_code = event_data.get("validated_code", "")

        gist_data = event_data.get("gist_data")

        for section_name in section_order:

            if section_name == 'introduction':

                parts.append(intro)

                parts.append(section_spacing)

            elif section_name == 'code_implementation':

                # Show code EARLY - right after introduction

                if code_segments or validated_code or gist_data:

                    parts.append(self._get_section_heading("code_implementation"))

                    # Prefer gist (embedded, interactive)

                    if gist_data:

                        owner = gist_data.get("owner", "user")

                        gist_id = gist_data.get("gist_id")

                        filename = gist_data.get("filename")

                        # Try to get filename if missing

                        if not filename:

                            raw = (gist_data.get("urls") or {}).get("raw_urls") or {}

                            if isinstance(raw, dict) and raw:

                                filename = next(iter(raw.keys()))

                        if gist_id and filename:

                            shortcode = create_gist_shortcode(owner, gist_id, filename)

                            parts.append(f"\n{shortcode}\n")

                        elif validated_code:

                            # Fallback to inline if gist incomplete

                            parts.append(create_code_block(validated_code, "cs"))

                    elif validated_code:

                        # No gist, show inline code

                        parts.append(create_code_block(validated_code, "cs"))

                    parts.append(section_spacing)

            elif section_name == 'code_explanation':

                # Detailed breakdown AFTER showing code

                if code_segments:

                    parts.append(self._get_section_heading("code_explanation"))

                    parts.append("Let's break down the key components of this implementation:\n")

                    parts.append(section_spacing)

                    for segment in code_segments:

                        parts.append(f"### {segment['label']}\n")

                        parts.append(create_code_block(segment['code'], "cs"))

                        parts.append(section_spacing)

            elif section_name == 'prerequisites':

                # Prerequisites AFTER showing value

                if supplementary.get("prerequisites"):

                    parts.append(self._get_section_heading("prerequisites"))

                    parts.append(supplementary["prerequisites"])

                    parts.append(section_spacing)

            elif section_name == 'main_content':

                # Add all main sections

                for section in sections:

                    parts.append(f"## {section['title']}\n")

                    parts.append(section['content'])

                    parts.append(section_spacing)

            elif section_name == 'troubleshooting':

                if supplementary.get("troubleshooting"):

                    parts.append(self._get_section_heading("troubleshooting"))

                    parts.append(supplementary["troubleshooting"])

                    parts.append(section_spacing)

            elif section_name == 'faq':

                if supplementary.get("faq"):

                    parts.append(self._get_section_heading("faq"))

                    parts.append(supplementary["faq"])

                    parts.append(section_spacing)

            elif section_name == 'use_cases':

                if supplementary.get("use_cases"):

                    parts.append(self._get_section_heading("use_cases"))

                    parts.append(supplementary["use_cases"])

                    parts.append(section_spacing)

            elif section_name == 'best_practices':

                if supplementary.get("best_practices"):

                    parts.append(self._get_section_heading("best_practices"))

                    parts.append(supplementary["best_practices"])

                    parts.append(section_spacing)

            elif section_name == 'supported_formats':

                if supplementary.get("supported_formats"):

                    parts.append(self._get_section_heading("supported_formats"))

                    parts.append(supplementary["supported_formats"])

                    parts.append(section_spacing)

            elif section_name == 'conclusion':

                if conclusion:

                    parts.append(self._get_section_heading("conclusion"))

                    parts.append(conclusion)

                    parts.append(section_spacing)

        # Apply deduplication pass to remove consecutive duplicate headings

        final_content = "".join(parts)

        deduplicated_content, removed_dups = deduplicate_headings(final_content)

        if removed_dups:

            logger.info(f"Removed {len(removed_dups)} duplicate headings during assembly")

        # Apply code fence normalization to ensure all code blocks use template format
        normalized_content = self._normalize_code_fences(deduplicated_content)

        return normalized_content

    def _normalize_code_fences(self, content: str) -> str:
        """        Normalize all code fences in content to conform to code_template.

        Args:
            content: Markdown content with code fences

        Returns:
            Content with normalized code fences"""
        import re

        # Get template configuration
        code_templates = self.config.templates.get('code_templates', {})
        code_block_config = code_templates.get('code_block', {})
        default_lang = code_block_config.get('language', 'cs')

        # Pattern to match code fences with optional language and metadata
        pattern = r'```(\w*)(.*?)\r?\n(.*?)```'

        def normalize_fence(match):
            lang = match.group(1)
            code = match.group(3)

            # Infer language if not provided
            if not lang:
                if any(keyword in code for keyword in ['Install-Package', 'PM>', 'dotnet ', 'nuget ']):
                    lang = 'shell'
                elif 'using Aspose' in code or 'namespace ' in code or 'class ' in code:
                    lang = 'cs'
                else:
                    lang = default_lang

            # Ensure CRLF line endings
            code_normalized = code.replace('\r\n', '\n').replace('\r', '\n')
            code_lines = code_normalized.split('\n')
            code_normalized = '\r\n'.join(line.rstrip() for line in code_lines)

            # Build normalized fence
            return f"```{lang}\r\n{code_normalized.rstrip()}\r\n```"

        # Replace all code fences with normalized versions
        normalized = re.sub(pattern, normalize_fence, content, flags=re.DOTALL)

        # Count normalizations for logging
        original_fences = len(re.findall(pattern, content, re.DOTALL))
        if original_fences > 0:
            logger.info(f"Normalized {original_fences} code fence(s) to template format")

        return normalized

# ============================================================================

# CODE AGENTS (5)

# ============================================================================

