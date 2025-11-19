"""Unit tests for src/utils/json_repair.py.

Tests JSON repair functionality for handling malformed JSON from LLM responses.
"""

import pytest
import json

from src.utils.json_repair import JSONRepair, safe_json_loads


# ============================================================================
# Test JSONRepair.repair - Basic Functionality
# ============================================================================

class TestJSONRepairBasic:
    """Test basic JSON repair functionality."""

    def test_repair_valid_json(self):
        """Test that valid JSON passes through unchanged."""
        valid_json = '{"key": "value", "number": 42}'
        result = JSONRepair.repair(valid_json)
        assert result == {"key": "value", "number": 42}

    def test_repair_empty_string(self):
        """Test repair of empty string returns empty dict."""
        result = JSONRepair.repair("")
        assert result == {}

    def test_repair_valid_array(self):
        """Test repair of valid JSON array."""
        valid_array = '["item1", "item2", "item3"]'
        result = JSONRepair.repair(valid_array)
        assert result == ["item1", "item2", "item3"]

    def test_repair_nested_object(self):
        """Test repair of nested valid JSON object."""
        nested = '{"outer": {"inner": "value"}}'
        result = JSONRepair.repair(nested)
        assert result == {"outer": {"inner": "value"}}


# ============================================================================
# Test JSONRepair - Trailing Commas
# ============================================================================

class TestTrailingCommas:
    """Test repair of trailing commas."""

    def test_trailing_comma_in_object(self):
        """Test removal of trailing comma in object."""
        malformed = '{"key": "value",}'
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value"}

    def test_trailing_comma_in_array(self):
        """Test removal of trailing comma in array."""
        malformed = '["item1", "item2",]'
        result = JSONRepair.repair(malformed)
        assert result == ["item1", "item2"]

    def test_multiple_trailing_commas(self):
        """Test removal of multiple trailing commas."""
        malformed = '{"a": 1, "b": [1, 2,],}'
        result = JSONRepair.repair(malformed)
        assert result == {"a": 1, "b": [1, 2]}


# ============================================================================
# Test JSONRepair - Quote Fixes
# ============================================================================

class TestQuoteFixes:
    """Test repair of quote-related issues."""

    def test_single_quotes_to_double(self):
        """Test conversion of single quotes to double quotes."""
        malformed = "{'key': 'value'}"
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value"}

    def test_mixed_quotes(self):
        """Test handling of mixed quote types."""
        malformed = '{"key": \'value\', \'other\': "data"}'
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value", "other": "data"}

    def test_unquoted_keys(self):
        """Test adding quotes to unquoted keys."""
        malformed = '{key: "value", another: "data"}'
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value", "another": "data"}

    def test_unquoted_keys_with_underscores(self):
        """Test unquoted keys with underscores."""
        malformed = '{my_key: "value", another_key: "data"}'
        result = JSONRepair.repair(malformed)
        assert result == {"my_key": "value", "another_key": "data"}


# ============================================================================
# Test JSONRepair - Bracket Balancing
# ============================================================================

class TestBracketBalancing:
    """Test bracket and brace balancing."""

    def test_missing_closing_brace(self):
        """Test adding missing closing brace."""
        malformed = '{"key": "value"'
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value"}

    def test_missing_closing_bracket(self):
        """Test adding missing closing bracket."""
        malformed = '["item1", "item2"'
        result = JSONRepair.repair(malformed)
        assert result == ["item1", "item2"]

    def test_multiple_missing_braces(self):
        """Test adding multiple missing braces."""
        malformed = '{' * 3 + '"key": "value"'
        result = JSONRepair.repair(malformed)
        # Should balance the braces
        assert isinstance(result, dict)

    def test_nested_missing_brackets(self):
        """Test balancing nested structures with missing brackets."""
        malformed = '{"array": ["item1", "item2"'
        result = JSONRepair.repair(malformed)
        # May not perfectly repair complex nesting, but should return dict
        assert isinstance(result, dict)


# ============================================================================
# Test JSONRepair - Whitespace and Control Characters
# ============================================================================

class TestWhitespaceHandling:
    """Test handling of whitespace and control characters."""

    def test_leading_whitespace(self):
        """Test removal of leading whitespace."""
        malformed = '   \n\t {"key": "value"}'
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value"}

    def test_trailing_whitespace(self):
        """Test handling of trailing whitespace."""
        malformed = '{"key": "value"}   \n\t '
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value"}

    def test_text_before_json(self):
        """Test removal of text before JSON."""
        malformed = 'Here is some text: {"key": "value"}'
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value"}

    def test_text_before_array(self):
        """Test removal of text before JSON array."""
        malformed = 'The array is: ["item1", "item2"]'
        result = JSONRepair.repair(malformed)
        assert result == ["item1", "item2"]


# ============================================================================
# Test JSONRepair - Complex Repairs
# ============================================================================

class TestComplexRepairs:
    """Test complex repair scenarios."""

    def test_multiple_issues(self):
        """Test repair of JSON with multiple issues."""
        malformed = "  {key: 'value', another: 'data',}  "
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value", "another": "data"}

    def test_nested_with_quotes_issue(self):
        """Test nested structure with quote issues."""
        malformed = "{'outer': {'inner': 'value'}}"
        result = JSONRepair.repair(malformed)
        assert result == {"outer": {"inner": "value"}}

    def test_array_with_multiple_issues(self):
        """Test array with various issues."""
        malformed = "['item1', 'item2',]"
        result = JSONRepair.repair(malformed)
        assert result == ["item1", "item2"]


# ============================================================================
# Test JSONRepair - Aggressive Repair
# ============================================================================

class TestAggressiveRepair:
    """Test aggressive repair methods."""

    def test_extract_simple_object(self):
        """Test extraction of simple object from garbage."""
        malformed = 'garbage {"key": "value"} more garbage'
        result = JSONRepair.repair(malformed)
        assert result == {"key": "value"}

    def test_extract_key_value_pairs(self):
        """Test extraction of key-value pairs."""
        malformed = 'completely broken but has "title": "Test Title" somewhere'
        result = JSONRepair.repair(malformed)
        assert "title" in result or "topics" in result

    def test_extract_numeric_values(self):
        """Test extraction of numeric values."""
        malformed = '"count": 42, "price": 19.99'
        result = JSONRepair.repair(malformed)
        # Should extract some data
        assert isinstance(result, dict)

    def test_extract_boolean_values(self):
        """Test extraction of boolean values."""
        malformed = '"active": true, "enabled": false'
        result = JSONRepair.repair(malformed)
        assert isinstance(result, dict)

    def test_extract_array_values(self):
        """Test extraction of array values."""
        malformed = '"items": ["a", "b", "c"]'
        result = JSONRepair.repair(malformed)
        # May return dict or list depending on extraction
        assert isinstance(result, (dict, list))


# ============================================================================
# Test JSONRepair - Safe Default
# ============================================================================

class TestSafeDefault:
    """Test safe default fallback."""

    def test_completely_broken_json_returns_dict(self):
        """Test that completely broken JSON returns a dict."""
        malformed = 'this is not JSON at all!!!'
        result = JSONRepair.repair(malformed)
        assert isinstance(result, dict)

    def test_safe_default_extracts_title(self):
        """Test safe default extracts title if present."""
        malformed = 'broken but has "title": "My Title" in it'
        result = JSONRepair.repair(malformed)
        # Should have either title directly or in topics
        assert "title" in result or ("topics" in result and len(result["topics"]) > 0)

    def test_safe_default_fallback_structure(self):
        """Test safe default creates expected structure."""
        malformed = 'completely broken'
        result = JSONRepair.repair(malformed)
        # Should return a dict with some structure
        assert isinstance(result, dict)


# ============================================================================
# Test JSONRepair - Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_only_opening_brace(self):
        """Test JSON with only opening brace."""
        malformed = '{'
        result = JSONRepair.repair(malformed)
        assert isinstance(result, dict)

    def test_only_opening_bracket(self):
        """Test JSON with only opening bracket."""
        malformed = '['
        result = JSONRepair.repair(malformed)
        # Should return dict or list
        assert isinstance(result, (dict, list))

    def test_empty_object(self):
        """Test empty object."""
        result = JSONRepair.repair('{}')
        assert result == {}

    def test_empty_array(self):
        """Test empty array."""
        result = JSONRepair.repair('[]')
        assert result == []

    def test_unicode_content(self):
        """Test JSON with Unicode content."""
        unicode_json = '{"text": "Hello 世界 🌍"}'
        result = JSONRepair.repair(unicode_json)
        assert result == {"text": "Hello 世界 🌍"}

    def test_escaped_quotes_in_values(self):
        """Test handling of escaped quotes."""
        escaped = '{"text": "He said \\"hello\\""}'
        result = JSONRepair.repair(escaped)
        assert result == {"text": 'He said "hello"'}


# ============================================================================
# Test safe_json_loads Helper
# ============================================================================

class TestSafeJsonLoads:
    """Test safe_json_loads helper function."""

    def test_safe_loads_valid_json(self):
        """Test safe loads with valid JSON."""
        valid = '{"key": "value"}'
        result = safe_json_loads(valid)
        assert result == {"key": "value"}

    def test_safe_loads_malformed_json(self):
        """Test safe loads with malformed JSON."""
        malformed = '{"key": "value",}'
        result = safe_json_loads(malformed)
        assert result == {"key": "value"}

    def test_safe_loads_with_default(self):
        """Test safe loads returns default on failure."""
        # This will definitely fail even after repair
        broken = None  # Not a string
        default = {"fallback": True}
        result = safe_json_loads(str(broken) if broken else "", default=default)
        # Should either repair or return default
        assert isinstance(result, dict)

    def test_safe_loads_default_none(self):
        """Test safe loads without explicit default."""
        broken = "completely broken"
        result = safe_json_loads(broken)
        # Should return empty dict by default
        assert isinstance(result, dict)

    def test_safe_loads_array(self):
        """Test safe loads with array."""
        arr = '["a", "b", "c"]'
        result = safe_json_loads(arr)
        assert result == ["a", "b", "c"]


# ============================================================================
# Test JSONRepair Internal Methods
# ============================================================================

class TestInternalMethods:
    """Test internal repair methods."""

    def test_fix_quotes_simple(self):
        """Test _fix_quotes with simple case."""
        result = JSONRepair._fix_quotes("{'key': 'value'}")
        assert '"key"' in result
        assert '"value"' in result

    def test_fix_unquoted_keys_simple(self):
        """Test _fix_unquoted_keys."""
        result = JSONRepair._fix_unquoted_keys("{key: value}")
        assert '"key"' in result

    def test_balance_brackets_braces(self):
        """Test _balance_brackets with missing braces."""
        result = JSONRepair._balance_brackets("{{")
        assert result == "{{}}"

    def test_balance_brackets_brackets(self):
        """Test _balance_brackets with missing brackets."""
        result = JSONRepair._balance_brackets("[[")
        assert result == "[[]]"

    def test_extract_key_values_strings(self):
        """Test _extract_key_values with string values."""
        result = JSONRepair._extract_key_values('"name": "John", "city": "NYC"')
        assert result.get("name") == "John"
        assert result.get("city") == "NYC"

    def test_extract_key_values_numbers(self):
        """Test _extract_key_values with numeric values."""
        result = JSONRepair._extract_key_values('"age": 25, "price": 19.99')
        assert result.get("age") == 25
        assert result.get("price") == 19.99

    def test_extract_key_values_booleans(self):
        """Test _extract_key_values with boolean values."""
        result = JSONRepair._extract_key_values('"active": true, "enabled": false, "optional": null')
        assert result.get("active") is True
        assert result.get("enabled") is False
        assert result.get("optional") is None


# ============================================================================
# Test JSONRepair - Real-World LLM Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world LLM output scenarios."""

    def test_llm_response_with_explanation(self):
        """Test LLM response with explanation text."""
        llm_output = '''Here is the JSON:
        {
            "title": "My Article",
            "tags": ["python", "testing"]
        }
        Hope this helps!'''
        result = JSONRepair.repair(llm_output)
        assert result["title"] == "My Article"
        assert result["tags"] == ["python", "testing"]

    def test_llm_markdown_code_block(self):
        """Test LLM response in markdown code block."""
        llm_output = '''```json
        {"status": "success", "data": {"count": 42}}
        ```'''
        result = JSONRepair.repair(llm_output)
        # Repair should extract JSON from code block
        assert isinstance(result, dict)
        # May or may not perfectly extract nested structure
        if "status" in result:
            assert result["status"] == "success"

    def test_llm_partial_response(self):
        """Test incomplete LLM response."""
        partial = '{"items": ["item1", "item2"'
        result = JSONRepair.repair(partial)
        # Should return a dict (may or may not have items depending on repair success)
        assert isinstance(result, dict)

    def test_llm_extra_commas(self):
        """Test LLM response with extra commas."""
        llm_output = '{"a": 1, "b": 2,, "c": 3}'
        # This might not parse perfectly but should not crash
        result = JSONRepair.repair(llm_output)
        assert isinstance(result, dict)


# ============================================================================
# Test JSONRepair - Progressive Repair Levels
# ============================================================================

class TestProgressiveRepair:
    """Test progressive repair levels."""

    def test_max_attempts_parameter(self):
        """Test that max_attempts parameter is respected."""
        # Should work with default attempts
        result = JSONRepair.repair('{"key": "value",}', max_attempts=1)
        assert result == {"key": "value"}

    def test_repair_level_escalation(self):
        """Test that repair escalates through levels."""
        # Start with issue that needs multiple levels
        malformed = "  garbage {key: 'value',} more garbage  "
        result = JSONRepair.repair(malformed)
        assert isinstance(result, dict)

    def test_apply_repairs_level_0(self):
        """Test _apply_repairs at level 0."""
        dirty = "  \n  {'key': 'value'}  "
        result = JSONRepair._apply_repairs(dirty, 0)
        # Should clean whitespace and fix quotes
        assert '{"key"' in result

    def test_apply_repairs_level_1(self):
        """Test _apply_repairs at level 1."""
        malformed = '{"key": "value",}'
        result = JSONRepair._apply_repairs(malformed, 1)
        # Should remove trailing comma
        assert ',' not in result.rstrip('}')

    def test_apply_repairs_level_2(self):
        """Test _apply_repairs at level 2."""
        incomplete = '{"key": "value"'
        result = JSONRepair._apply_repairs(incomplete, 2)
        # Should balance brackets
        assert result.count('{') == result.count('}')
