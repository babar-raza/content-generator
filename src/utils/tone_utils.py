# tone_utils.py
"""Utilities for applying tone and editorial configuration to content generation."""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def get_section_config(tone_config: Dict[str, Any], section_name: str) -> Dict[str, Any]:
    """Get configuration for a specific section.

    Args:
        tone_config: The loaded tone configuration
        section_name: Name of the section (e.g., 'introduction', 'code_implementation')

    Returns:
        Section configuration dict or empty dict if not found"""
    if not tone_config:
        return {}

    section_controls = tone_config.get('section_controls', {})
    return section_controls.get(section_name, {})

def get_global_voice(tone_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get global voice configuration.

    Args:
        tone_config: The loaded tone configuration

    Returns:
        Global voice configuration dict"""
    if not tone_config:
        return {}

    return tone_config.get('global_voice', {})

def build_section_prompt_enhancement(
    tone_config: Dict[str, Any],
    section_name: str,
    base_prompt: str
) -> str:
    """Enhance a base prompt with tone and structure directives.

    Args:
        tone_config: The loaded tone configuration
        section_name: Name of the section
        base_prompt: The base prompt to enhance

    Returns:
        Enhanced prompt with tone directives"""
    if not tone_config:
        return base_prompt

    section_config = get_section_config(tone_config, section_name)
    global_voice = get_global_voice(tone_config)

    if not section_config:
        return base_prompt

    # Build tone directive
    tone_directive = _build_tone_directive(section_config, global_voice)
    structure_directive = _build_structure_directive(section_config)
    requirements_directive = _build_requirements_directive(section_config)
    constraints_directive = _build_constraints_directive(section_config, tone_config)

    # Combine all directives
    enhanced_prompt = f"""{base_prompt}

**TONE AND STYLE REQUIREMENTS:**
{tone_directive}

**STRUCTURE REQUIREMENTS:**
{structure_directive}

{requirements_directive}

{constraints_directive}"""

    return enhanced_prompt

def _build_tone_directive(section_config: Dict[str, Any], global_voice: Dict[str, Any]) -> str:
    """Build tone directive from configuration."""
    directives = []

    # Get voice override or use global
    voice_override = section_config.get('voice_override') or {}
    pov = voice_override.get('pov') or global_voice.get('pov', 'second_person')
    formality = global_voice.get('formality', 'professional_conversational')
    technical_depth = global_voice.get('technical_depth', 'intermediate')

    # POV directive
    pov_map = {
        'first_person': 'Use first-person perspective (we, our)',
        'second_person': 'Use second-person perspective (you, your)',
        'third_person': 'Use third-person perspective'
    }
    directives.append(pov_map.get(pov, 'Use second-person perspective'))

    # Formality directive
    formality_map = {
        'casual': 'Use casual, conversational language',
        'professional_conversational': 'Use professional yet conversational tone',
        'formal': 'Use formal, technical language',
        'academic': 'Use academic, scholarly tone'
    }
    directives.append(formality_map.get(formality, 'Use professional yet conversational tone'))

    # Technical depth directive
    depth_map = {
        'beginner': 'Explain concepts simply for beginners',
        'intermediate': 'Assume intermediate knowledge, explain advanced concepts',
        'advanced': 'Use advanced terminology, assume strong technical background',
        'expert': 'Write for expert audience, use specialized terminology freely'
    }
    directives.append(depth_map.get(technical_depth, 'Assume intermediate knowledge'))

    # Section-specific tone
    section_tone = section_config.get('tone', '')
    if section_tone:
        directives.append(f"Section tone: {section_tone.replace('_', ' ')}")

    return '\n'.join(f"- {d}" for d in directives)

def _build_structure_directive(section_config: Dict[str, Any]) -> str:
    """Build structure directive from configuration."""
    directives = []

    structure = section_config.get('structure', 'prose')
    structure_map = {
        'prose': 'Write in paragraph form (prose)',
        'bullets': 'Use bullet points',
        'numbered': 'Use numbered lists',
        'mixed': 'Mix prose and lists appropriately',
        'table': 'Present information in table format',
        'qa_pairs': 'Use Q&A format with bold questions',
        'problem_solution_pairs': 'Use problem-solution pairs',
        'segmented_walkthrough': 'Break into segments with explanations',
        'step_by_step': 'Use step-by-step numbered format',
        'prose_with_subheadings': 'Use prose organized with subheadings',
        'code_with_explanation': 'Present code followed by explanation',
        'bullets_with_description': 'Use bullets with detailed descriptions'
    }

    structure_directive = structure_map.get(structure, 'Write in appropriate format')
    directives.append(structure_directive)

    # Paragraph limits
    max_para = section_config.get('max_paragraphs')
    min_para = section_config.get('min_paragraphs')
    if max_para or min_para:
        if max_para and min_para:
            directives.append(f"Write {min_para}-{max_para} paragraphs")
        elif max_para:
            directives.append(f"Write at most {max_para} paragraphs")
        elif min_para:
            directives.append(f"Write at least {min_para} paragraphs")

    # Word count
    word_count = section_config.get('word_count_target', '')
    if word_count:
        directives.append(f"Target word count: {word_count} words")

    return '\n'.join(f"- {d}" for d in directives)

def _build_requirements_directive(section_config: Dict[str, Any]) -> str:
    """Build requirements directive from configuration."""
    required = section_config.get('required_elements', [])
    optional = section_config.get('optional_elements', [])

    if not required and not optional:
        return ""

    parts = ["**CONTENT REQUIREMENTS:**"]

    if required:
        parts.append("Required elements:")
        for elem in required:
            parts.append(f"- {elem.replace('_', ' ').title()}")

    if optional:
        parts.append("\nOptional elements (include if relevant):")
        for elem in optional:
            parts.append(f"- {elem.replace('_', ' ').title()}")

    return '\n'.join(parts)

def _build_constraints_directive(section_config: Dict[str, Any], tone_config: Dict[str, Any]) -> str:
    """Build constraints directive from configuration."""
    constraints = []

    # Avoid phrases
    avoid_phrases = section_config.get('avoid_phrases', [])
    if avoid_phrases:
        constraints.append("**AVOID THESE PHRASES:**")
        for phrase in avoid_phrases:
            constraints.append(f"- \"{phrase}\"")

    # Sentence structure from global config
    sentence_prefs = tone_config.get('sentence_structure', {})
    if sentence_prefs:
        length = sentence_prefs.get('avg_sentence_length', 'medium')
        if length == 'short':
            constraints.append("\n- Use short, concise sentences (8-15 words average)")
        elif length == 'long':
            constraints.append("\n- Use longer, detailed sentences (25-40 words average)")
        elif length == 'varied':
            constraints.append("\n- Vary sentence length for readability")

    return '\n'.join(constraints)

def get_section_heading(tone_config: Dict[str, Any], section_name: str, dynamic_title: Optional[str] = None) -> str:
    """Get the heading for a section.

    Args:
        tone_config: The loaded tone configuration
        section_name: Name of the section
        dynamic_title: Optional dynamic title for sections that use templates

    Returns:
        The section heading"""
    section_config = get_section_config(tone_config, section_name)

    if not section_config:
        # Fallback to default
        return f"## {section_name.replace('_', ' ').title()}"

    heading_template = section_config.get('heading', f"## {section_name.replace('_', ' ').title()}")

    # Replace dynamic title placeholder
    if dynamic_title and '{dynamic_title}' in heading_template:
        return heading_template.replace('{dynamic_title}', dynamic_title)
    elif '{section_title}' in heading_template:
        if dynamic_title:
            return heading_template.replace('{section_title}', dynamic_title)
        else:
            return heading_template.replace('{section_title}', section_name.replace('_', ' ').title())

    return heading_template

def is_section_enabled(tone_config: Dict[str, Any], section_name: str) -> bool:
    """Check if a section is enabled in the configuration.

    Args:
        tone_config: The loaded tone configuration
        section_name: Name of the section

    Returns:
        True if section is enabled, False otherwise (defaults to True)"""
    section_config = get_section_config(tone_config, section_name)

    if not section_config:
        return True  # Default to enabled if not configured

    return section_config.get('enabled', True)

def get_content_preferences(tone_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get content preferences (analogies, examples, etc.).

    Args:
        tone_config: The loaded tone configuration

    Returns:
        Content preferences dict"""
    if not tone_config:
        return {}

    return tone_config.get('content_preferences', {})

def should_enforce_quality_checks(tone_config: Dict[str, Any]) -> bool:
    """Check if quality checks should be enforced.

    Args:
        tone_config: The loaded tone configuration

    Returns:
        True if quality checks should be enforced"""
    if not tone_config:
        return False

    quality_checks = tone_config.get('quality_checks', {})
    return quality_checks.get('enforce_word_counts', False) or\
           quality_checks.get('enforce_required_elements', False)

def get_quality_check_config(tone_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get quality check configuration.

    Args:
        tone_config: The loaded tone configuration

    Returns:
        Quality check configuration dict"""
    if not tone_config:
        return {}

    return tone_config.get('quality_checks', {})
# DOCGEN:LLM-FIRST@v4