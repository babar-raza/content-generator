"""Unit tests for src/utils/tone_utils.py.

Tests tone and editorial utilities including:
- Section configuration retrieval
- Global voice configuration
- Prompt enhancement with tone directives
- Structure directives
- Requirements and constraints
- Section headings
- Section enablement checks
- Content preferences and quality checks
"""

import pytest
from src.utils.tone_utils import (
    get_section_config,
    get_global_voice,
    build_section_prompt_enhancement,
    get_section_heading,
    is_section_enabled,
    get_content_preferences,
    should_enforce_quality_checks,
    get_quality_check_config,
    _build_tone_directive,
    _build_structure_directive,
    _build_requirements_directive,
    _build_constraints_directive
)


# ============================================================================
# Test get_section_config
# ============================================================================

class TestGetSectionConfig:
    """Test get_section_config function."""

    def test_get_section_config_exists(self):
        """Test getting existing section config."""
        tone_config = {
            'section_controls': {
                'introduction': {'tone': 'engaging', 'structure': 'prose'}
            }
        }
        result = get_section_config(tone_config, 'introduction')
        assert result == {'tone': 'engaging', 'structure': 'prose'}

    def test_get_section_config_not_exists(self):
        """Test getting non-existent section config."""
        tone_config = {
            'section_controls': {
                'introduction': {'tone': 'engaging'}
            }
        }
        result = get_section_config(tone_config, 'conclusion')
        assert result == {}

    def test_get_section_config_empty_tone_config(self):
        """Test with empty tone config."""
        result = get_section_config({}, 'introduction')
        assert result == {}

    def test_get_section_config_none_tone_config(self):
        """Test with None tone config."""
        result = get_section_config(None, 'introduction')
        assert result == {}

    def test_get_section_config_missing_section_controls(self):
        """Test with missing section_controls key."""
        tone_config = {'global_voice': {}}
        result = get_section_config(tone_config, 'introduction')
        assert result == {}


# ============================================================================
# Test get_global_voice
# ============================================================================

class TestGetGlobalVoice:
    """Test get_global_voice function."""

    def test_get_global_voice_exists(self):
        """Test getting global voice config."""
        tone_config = {
            'global_voice': {
                'pov': 'second_person',
                'formality': 'professional_conversational'
            }
        }
        result = get_global_voice(tone_config)
        assert result == {'pov': 'second_person', 'formality': 'professional_conversational'}

    def test_get_global_voice_missing(self):
        """Test with missing global_voice key."""
        tone_config = {'section_controls': {}}
        result = get_global_voice(tone_config)
        assert result == {}

    def test_get_global_voice_empty_config(self):
        """Test with empty config."""
        result = get_global_voice({})
        assert result == {}

    def test_get_global_voice_none_config(self):
        """Test with None config."""
        result = get_global_voice(None)
        assert result == {}


# ============================================================================
# Test build_section_prompt_enhancement
# ============================================================================

class TestBuildSectionPromptEnhancement:
    """Test build_section_prompt_enhancement function."""

    def test_enhancement_with_full_config(self):
        """Test prompt enhancement with full configuration."""
        tone_config = {
            'global_voice': {
                'pov': 'second_person',
                'formality': 'professional_conversational',
                'technical_depth': 'intermediate'
            },
            'section_controls': {
                'introduction': {
                    'tone': 'engaging',
                    'structure': 'prose',
                    'word_count_target': 200
                }
            }
        }
        base_prompt = "Write an introduction."
        result = build_section_prompt_enhancement(tone_config, 'introduction', base_prompt)

        assert "Write an introduction." in result
        assert "TONE AND STYLE REQUIREMENTS:" in result
        assert "STRUCTURE REQUIREMENTS:" in result
        assert "second-person" in result
        assert "professional yet conversational" in result

    def test_enhancement_with_empty_config(self):
        """Test enhancement with empty config returns base prompt."""
        result = build_section_prompt_enhancement({}, 'introduction', "Write intro")
        assert result == "Write intro"

    def test_enhancement_with_none_config(self):
        """Test enhancement with None config returns base prompt."""
        result = build_section_prompt_enhancement(None, 'introduction', "Write intro")
        assert result == "Write intro"

    def test_enhancement_with_missing_section(self):
        """Test enhancement when section not in config."""
        tone_config = {
            'global_voice': {'pov': 'first_person'},
            'section_controls': {'conclusion': {}}
        }
        result = build_section_prompt_enhancement(tone_config, 'introduction', "Write intro")
        assert result == "Write intro"

    def test_enhancement_includes_requirements(self):
        """Test enhancement includes requirements."""
        tone_config = {
            'global_voice': {},
            'section_controls': {
                'code_section': {
                    'required_elements': ['code_example', 'explanation']
                }
            }
        }
        base_prompt = "Write code section."
        result = build_section_prompt_enhancement(tone_config, 'code_section', base_prompt)

        assert "CONTENT REQUIREMENTS:" in result
        assert "Code Example" in result
        assert "Explanation" in result

    def test_enhancement_includes_constraints(self):
        """Test enhancement includes constraints."""
        tone_config = {
            'global_voice': {},
            'section_controls': {
                'introduction': {
                    'avoid_phrases': ['in conclusion', 'to sum up']
                }
            },
            'sentence_structure': {
                'avg_sentence_length': 'short'
            }
        }
        base_prompt = "Write intro."
        result = build_section_prompt_enhancement(tone_config, 'introduction', base_prompt)

        assert "AVOID THESE PHRASES:" in result
        assert '"in conclusion"' in result
        assert '"to sum up"' in result


# ============================================================================
# Test _build_tone_directive
# ============================================================================

class TestBuildToneDirective:
    """Test _build_tone_directive function."""

    def test_tone_directive_defaults(self):
        """Test tone directive with default values."""
        section_config = {}
        global_voice = {}
        result = _build_tone_directive(section_config, global_voice)

        assert "second-person" in result
        assert "professional yet conversational" in result
        assert "intermediate knowledge" in result

    def test_tone_directive_first_person(self):
        """Test tone directive with first person POV."""
        section_config = {'voice_override': {'pov': 'first_person'}}
        global_voice = {}
        result = _build_tone_directive(section_config, global_voice)

        assert "first-person" in result
        assert "we, our" in result

    def test_tone_directive_third_person(self):
        """Test tone directive with third person POV."""
        section_config = {'voice_override': {'pov': 'third_person'}}
        global_voice = {}
        result = _build_tone_directive(section_config, global_voice)

        assert "third-person" in result

    def test_tone_directive_casual_formality(self):
        """Test tone directive with casual formality."""
        section_config = {}
        global_voice = {'formality': 'casual'}
        result = _build_tone_directive(section_config, global_voice)

        assert "casual" in result

    def test_tone_directive_formal_formality(self):
        """Test tone directive with formal formality."""
        section_config = {}
        global_voice = {'formality': 'formal'}
        result = _build_tone_directive(section_config, global_voice)

        assert "formal, technical" in result

    def test_tone_directive_academic_formality(self):
        """Test tone directive with academic formality."""
        section_config = {}
        global_voice = {'formality': 'academic'}
        result = _build_tone_directive(section_config, global_voice)

        assert "academic" in result

    def test_tone_directive_beginner_depth(self):
        """Test tone directive with beginner technical depth."""
        section_config = {}
        global_voice = {'technical_depth': 'beginner'}
        result = _build_tone_directive(section_config, global_voice)

        assert "beginner" in result

    def test_tone_directive_advanced_depth(self):
        """Test tone directive with advanced technical depth."""
        section_config = {}
        global_voice = {'technical_depth': 'advanced'}
        result = _build_tone_directive(section_config, global_voice)

        assert "advanced" in result

    def test_tone_directive_expert_depth(self):
        """Test tone directive with expert technical depth."""
        section_config = {}
        global_voice = {'technical_depth': 'expert'}
        result = _build_tone_directive(section_config, global_voice)

        assert "expert" in result

    def test_tone_directive_section_tone(self):
        """Test tone directive with section-specific tone."""
        section_config = {'tone': 'technical_precise'}
        global_voice = {}
        result = _build_tone_directive(section_config, global_voice)

        assert "technical precise" in result

    def test_tone_directive_voice_override(self):
        """Test voice override takes precedence."""
        section_config = {'voice_override': {'pov': 'first_person'}}
        global_voice = {'pov': 'second_person'}
        result = _build_tone_directive(section_config, global_voice)

        assert "first-person" in result
        assert "second-person" not in result


# ============================================================================
# Test _build_structure_directive
# ============================================================================

class TestBuildStructureDirective:
    """Test _build_structure_directive function."""

    def test_structure_directive_prose(self):
        """Test structure directive for prose."""
        section_config = {'structure': 'prose'}
        result = _build_structure_directive(section_config)
        assert "paragraph form" in result

    def test_structure_directive_bullets(self):
        """Test structure directive for bullets."""
        section_config = {'structure': 'bullets'}
        result = _build_structure_directive(section_config)
        assert "bullet points" in result

    def test_structure_directive_numbered(self):
        """Test structure directive for numbered lists."""
        section_config = {'structure': 'numbered'}
        result = _build_structure_directive(section_config)
        assert "numbered lists" in result

    def test_structure_directive_mixed(self):
        """Test structure directive for mixed format."""
        section_config = {'structure': 'mixed'}
        result = _build_structure_directive(section_config)
        assert "Mix prose and lists" in result

    def test_structure_directive_qa_pairs(self):
        """Test structure directive for Q&A pairs."""
        section_config = {'structure': 'qa_pairs'}
        result = _build_structure_directive(section_config)
        assert "Q&A format" in result

    def test_structure_directive_step_by_step(self):
        """Test structure directive for step-by-step."""
        section_config = {'structure': 'step_by_step'}
        result = _build_structure_directive(section_config)
        assert "step-by-step" in result

    def test_structure_directive_max_paragraphs(self):
        """Test structure directive with max paragraphs."""
        section_config = {'max_paragraphs': 5}
        result = _build_structure_directive(section_config)
        assert "at most 5 paragraphs" in result

    def test_structure_directive_min_paragraphs(self):
        """Test structure directive with min paragraphs."""
        section_config = {'min_paragraphs': 3}
        result = _build_structure_directive(section_config)
        assert "at least 3 paragraphs" in result

    def test_structure_directive_paragraph_range(self):
        """Test structure directive with paragraph range."""
        section_config = {'min_paragraphs': 3, 'max_paragraphs': 5}
        result = _build_structure_directive(section_config)
        assert "3-5 paragraphs" in result

    def test_structure_directive_word_count(self):
        """Test structure directive with word count target."""
        section_config = {'word_count_target': 500}
        result = _build_structure_directive(section_config)
        assert "500 words" in result

    def test_structure_directive_default(self):
        """Test structure directive with no specified structure."""
        section_config = {}
        result = _build_structure_directive(section_config)
        # Default is prose structure
        assert "paragraph form" in result or "prose" in result


# ============================================================================
# Test _build_requirements_directive
# ============================================================================

class TestBuildRequirementsDirective:
    """Test _build_requirements_directive function."""

    def test_requirements_with_required_elements(self):
        """Test requirements directive with required elements."""
        section_config = {
            'required_elements': ['code_example', 'explanation', 'best_practices']
        }
        result = _build_requirements_directive(section_config)

        assert "CONTENT REQUIREMENTS:" in result
        assert "Code Example" in result
        assert "Explanation" in result
        assert "Best Practices" in result

    def test_requirements_with_optional_elements(self):
        """Test requirements directive with optional elements."""
        section_config = {
            'optional_elements': ['diagram', 'links']
        }
        result = _build_requirements_directive(section_config)

        assert "Optional elements" in result
        assert "Diagram" in result
        assert "Links" in result

    def test_requirements_with_both(self):
        """Test requirements directive with both required and optional."""
        section_config = {
            'required_elements': ['code_example'],
            'optional_elements': ['diagram']
        }
        result = _build_requirements_directive(section_config)

        assert "Required elements:" in result
        assert "Optional elements" in result
        assert "Code Example" in result
        assert "Diagram" in result

    def test_requirements_with_none(self):
        """Test requirements directive with no elements."""
        section_config = {}
        result = _build_requirements_directive(section_config)
        assert result == ""

    def test_requirements_empty_lists(self):
        """Test requirements directive with empty lists."""
        section_config = {
            'required_elements': [],
            'optional_elements': []
        }
        result = _build_requirements_directive(section_config)
        assert result == ""


# ============================================================================
# Test _build_constraints_directive
# ============================================================================

class TestBuildConstraintsDirective:
    """Test _build_constraints_directive function."""

    def test_constraints_with_avoid_phrases(self):
        """Test constraints directive with avoid phrases."""
        section_config = {
            'avoid_phrases': ['in conclusion', 'to sum up', 'needless to say']
        }
        tone_config = {}
        result = _build_constraints_directive(section_config, tone_config)

        assert "AVOID THESE PHRASES:" in result
        assert '"in conclusion"' in result
        assert '"to sum up"' in result
        assert '"needless to say"' in result

    def test_constraints_with_short_sentences(self):
        """Test constraints directive with short sentence preference."""
        section_config = {}
        tone_config = {
            'sentence_structure': {'avg_sentence_length': 'short'}
        }
        result = _build_constraints_directive(section_config, tone_config)

        assert "short, concise sentences" in result
        assert "8-15 words" in result

    def test_constraints_with_long_sentences(self):
        """Test constraints directive with long sentence preference."""
        section_config = {}
        tone_config = {
            'sentence_structure': {'avg_sentence_length': 'long'}
        }
        result = _build_constraints_directive(section_config, tone_config)

        assert "longer, detailed sentences" in result
        assert "25-40 words" in result

    def test_constraints_with_varied_sentences(self):
        """Test constraints directive with varied sentence preference."""
        section_config = {}
        tone_config = {
            'sentence_structure': {'avg_sentence_length': 'varied'}
        }
        result = _build_constraints_directive(section_config, tone_config)

        assert "Vary sentence length" in result

    def test_constraints_with_both(self):
        """Test constraints directive with both phrases and structure."""
        section_config = {
            'avoid_phrases': ['basically']
        }
        tone_config = {
            'sentence_structure': {'avg_sentence_length': 'short'}
        }
        result = _build_constraints_directive(section_config, tone_config)

        assert "AVOID THESE PHRASES:" in result
        assert '"basically"' in result
        assert "short, concise" in result

    def test_constraints_empty(self):
        """Test constraints directive with no constraints."""
        section_config = {}
        tone_config = {}
        result = _build_constraints_directive(section_config, tone_config)
        assert result == ""


# ============================================================================
# Test get_section_heading
# ============================================================================

class TestGetSectionHeading:
    """Test get_section_heading function."""

    def test_heading_with_template(self):
        """Test heading with configured template."""
        tone_config = {
            'section_controls': {
                'introduction': {
                    'heading': '## Introduction: {dynamic_title}'
                }
            }
        }
        result = get_section_heading(tone_config, 'introduction', 'Getting Started')
        assert result == '## Introduction: Getting Started'

    def test_heading_without_dynamic_title(self):
        """Test heading template without providing dynamic title."""
        tone_config = {
            'section_controls': {
                'introduction': {
                    'heading': '## Welcome'
                }
            }
        }
        result = get_section_heading(tone_config, 'introduction')
        assert result == '## Welcome'

    def test_heading_fallback_for_missing_section(self):
        """Test heading fallback for missing section."""
        tone_config = {
            'section_controls': {}
        }
        result = get_section_heading(tone_config, 'code_implementation')
        assert result == '## Code Implementation'

    def test_heading_with_section_title_placeholder(self):
        """Test heading with {section_title} placeholder."""
        tone_config = {
            'section_controls': {
                'examples': {
                    'heading': '## {section_title}'
                }
            }
        }
        result = get_section_heading(tone_config, 'examples', 'Practical Examples')
        assert result == '## Practical Examples'

    def test_heading_section_title_without_dynamic(self):
        """Test {section_title} placeholder without dynamic title."""
        tone_config = {
            'section_controls': {
                'examples': {
                    'heading': '## {section_title}'
                }
            }
        }
        result = get_section_heading(tone_config, 'examples')
        assert result == '## Examples'


# ============================================================================
# Test is_section_enabled
# ============================================================================

class TestIsSectionEnabled:
    """Test is_section_enabled function."""

    def test_section_enabled_true(self):
        """Test section explicitly enabled."""
        tone_config = {
            'section_controls': {
                'introduction': {'enabled': True}
            }
        }
        assert is_section_enabled(tone_config, 'introduction') is True

    def test_section_enabled_false(self):
        """Test section explicitly disabled."""
        tone_config = {
            'section_controls': {
                'introduction': {'enabled': False}
            }
        }
        assert is_section_enabled(tone_config, 'introduction') is False

    def test_section_default_enabled(self):
        """Test section defaults to enabled."""
        tone_config = {
            'section_controls': {
                'introduction': {}
            }
        }
        assert is_section_enabled(tone_config, 'introduction') is True

    def test_section_missing_defaults_enabled(self):
        """Test missing section defaults to enabled."""
        tone_config = {
            'section_controls': {}
        }
        assert is_section_enabled(tone_config, 'introduction') is True


# ============================================================================
# Test get_content_preferences
# ============================================================================

class TestGetContentPreferences:
    """Test get_content_preferences function."""

    def test_get_content_preferences_exists(self):
        """Test getting content preferences."""
        tone_config = {
            'content_preferences': {
                'use_analogies': True,
                'use_examples': True,
                'technical_examples': 'code_snippets'
            }
        }
        result = get_content_preferences(tone_config)
        assert result['use_analogies'] is True
        assert result['use_examples'] is True
        assert result['technical_examples'] == 'code_snippets'

    def test_get_content_preferences_missing(self):
        """Test with missing content_preferences."""
        tone_config = {}
        result = get_content_preferences(tone_config)
        assert result == {}

    def test_get_content_preferences_none(self):
        """Test with None config."""
        result = get_content_preferences(None)
        assert result == {}


# ============================================================================
# Test should_enforce_quality_checks
# ============================================================================

class TestShouldEnforceQualityChecks:
    """Test should_enforce_quality_checks function."""

    def test_enforce_word_counts_true(self):
        """Test enforcement when word counts enabled."""
        tone_config = {
            'quality_checks': {
                'enforce_word_counts': True,
                'enforce_required_elements': False
            }
        }
        assert should_enforce_quality_checks(tone_config) is True

    def test_enforce_required_elements_true(self):
        """Test enforcement when required elements enabled."""
        tone_config = {
            'quality_checks': {
                'enforce_word_counts': False,
                'enforce_required_elements': True
            }
        }
        assert should_enforce_quality_checks(tone_config) is True

    def test_enforce_both_true(self):
        """Test enforcement when both enabled."""
        tone_config = {
            'quality_checks': {
                'enforce_word_counts': True,
                'enforce_required_elements': True
            }
        }
        assert should_enforce_quality_checks(tone_config) is True

    def test_enforce_both_false(self):
        """Test no enforcement when both disabled."""
        tone_config = {
            'quality_checks': {
                'enforce_word_counts': False,
                'enforce_required_elements': False
            }
        }
        assert should_enforce_quality_checks(tone_config) is False

    def test_enforce_missing_config(self):
        """Test no enforcement with missing config."""
        tone_config = {}
        assert should_enforce_quality_checks(tone_config) is False

    def test_enforce_none_config(self):
        """Test no enforcement with None config."""
        assert should_enforce_quality_checks(None) is False


# ============================================================================
# Test get_quality_check_config
# ============================================================================

class TestGetQualityCheckConfig:
    """Test get_quality_check_config function."""

    def test_get_quality_check_config_exists(self):
        """Test getting quality check config."""
        tone_config = {
            'quality_checks': {
                'enforce_word_counts': True,
                'min_words_per_section': 100,
                'max_words_per_section': 500
            }
        }
        result = get_quality_check_config(tone_config)
        assert result['enforce_word_counts'] is True
        assert result['min_words_per_section'] == 100
        assert result['max_words_per_section'] == 500

    def test_get_quality_check_config_missing(self):
        """Test with missing quality_checks."""
        tone_config = {}
        result = get_quality_check_config(tone_config)
        assert result == {}

    def test_get_quality_check_config_none(self):
        """Test with None config."""
        result = get_quality_check_config(None)
        assert result == {}


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_prompt_enhancement_workflow(self):
        """Test complete prompt enhancement workflow."""
        tone_config = {
            'global_voice': {
                'pov': 'second_person',
                'formality': 'professional_conversational',
                'technical_depth': 'intermediate'
            },
            'section_controls': {
                'code_implementation': {
                    'tone': 'technical_precise',
                    'structure': 'code_with_explanation',
                    'required_elements': ['code_example', 'explanation', 'best_practices'],
                    'optional_elements': ['common_pitfalls'],
                    'avoid_phrases': ['simply', 'just', 'obviously'],
                    'word_count_target': 400,
                    'enabled': True,
                    'heading': '## Implementation: {dynamic_title}'
                }
            },
            'sentence_structure': {
                'avg_sentence_length': 'medium'
            },
            'quality_checks': {
                'enforce_word_counts': True,
                'enforce_required_elements': True
            }
        }

        # Test all functions work together
        assert is_section_enabled(tone_config, 'code_implementation') is True

        heading = get_section_heading(tone_config, 'code_implementation', 'User Authentication')
        assert heading == '## Implementation: User Authentication'

        enhanced_prompt = build_section_prompt_enhancement(
            tone_config,
            'code_implementation',
            "Write implementation code for user authentication."
        )

        assert "Write implementation code" in enhanced_prompt
        assert "TONE AND STYLE REQUIREMENTS:" in enhanced_prompt
        assert "technical precise" in enhanced_prompt
        assert "code followed by explanation" in enhanced_prompt
        assert "Code Example" in enhanced_prompt
        assert "Best Practices" in enhanced_prompt
        assert '"simply"' in enhanced_prompt
        assert "400 words" in enhanced_prompt

        assert should_enforce_quality_checks(tone_config) is True

        quality_config = get_quality_check_config(tone_config)
        assert quality_config['enforce_word_counts'] is True

    def test_minimal_configuration_workflow(self):
        """Test workflow with minimal configuration."""
        tone_config = {
            'section_controls': {
                'introduction': {}
            }
        }

        # Should work with defaults
        assert is_section_enabled(tone_config, 'introduction') is True

        heading = get_section_heading(tone_config, 'introduction')
        assert '##' in heading

        enhanced = build_section_prompt_enhancement(
            tone_config,
            'introduction',
            "Write intro"
        )
        # With empty section config, returns base prompt
        assert enhanced == "Write intro"
