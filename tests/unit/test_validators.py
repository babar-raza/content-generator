"""Unit tests for src/utils/validators.py.

Tests all validation functions including:
- Config validation
- Input validation with various constraints
- URL, email, port, IPv4 validation
- Range and structure validation
- Path and JSON schema validation
"""

import pytest
from pathlib import Path
import tempfile
import os

from src.utils.validators import (
    validate_config,
    validate_input,
    validate_url,
    validate_email,
    validate_port,
    validate_ipv4,
    validate_path,
    validate_json_schema,
    validate_range,
    validate_dict_structure,
)


# ============================================================================
# Test validate_config
# ============================================================================

class TestValidateConfig:
    """Test validate_config function."""

    def test_valid_config_basic(self):
        """Test basic valid config validation."""
        config = {"key1": "value1", "key2": "value2"}
        # Should not raise
        validate_config(config)

    def test_config_must_be_dict(self):
        """Test that config must be a dictionary."""
        with pytest.raises(ValueError, match="Config must be a dict"):
            validate_config("not a dict")

    def test_required_fields_present(self):
        """Test config with all required fields present."""
        config = {"field1": "value1", "field2": "value2", "field3": "value3"}
        validate_config(config, required_fields=["field1", "field2"])

    def test_required_fields_missing(self):
        """Test config missing required fields."""
        config = {"field1": "value1"}
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_config(config, required_fields=["field1", "field2", "field3"])

    def test_schema_validation_correct_types(self):
        """Test schema validation with correct types."""
        config = {"name": "test", "age": 25, "active": True}
        schema = {"name": str, "age": int, "active": bool}
        validate_config(config, schema=schema)

    def test_schema_validation_wrong_type(self):
        """Test schema validation with wrong type."""
        config = {"name": "test", "age": "twenty-five"}  # Wrong type
        schema = {"name": str, "age": int}
        with pytest.raises(ValueError, match="wrong type"):
            validate_config(config, schema=schema)

    def test_strict_mode_no_extra_keys(self):
        """Test strict mode with no extra keys."""
        config = {"field1": "value1", "field2": "value2"}
        schema = {"field1": str, "field2": str}
        validate_config(config, schema=schema, strict=True)

    def test_strict_mode_extra_keys(self):
        """Test strict mode with extra keys."""
        config = {"field1": "value1", "field2": "value2", "field3": "extra"}
        schema = {"field1": str, "field2": str}
        with pytest.raises(ValueError, match="Unexpected fields"):
            validate_config(config, schema=schema, strict=True)

    def test_schema_validation_partial_fields(self):
        """Test schema validation with only some fields present."""
        config = {"field1": "value1"}
        schema = {"field1": str, "field2": int}  # field2 not in config
        # Should not raise - only validates fields that exist
        validate_config(config, schema=schema)


# ============================================================================
# Test validate_input
# ============================================================================

class TestValidateInput:
    """Test validate_input function."""

    def test_not_none_constraint_pass(self):
        """Test not_none constraint with non-None value."""
        validate_input("value", "field", not_none=True)

    def test_not_none_constraint_fail(self):
        """Test not_none constraint with None value."""
        with pytest.raises(ValueError, match="cannot be None"):
            validate_input(None, "field", not_none=True)

    def test_not_empty_constraint_string_pass(self):
        """Test not_empty constraint with non-empty string."""
        validate_input("value", "field", not_empty=True)

    def test_not_empty_constraint_string_fail(self):
        """Test not_empty constraint with empty string."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_input("", "field", not_empty=True)

    def test_not_empty_constraint_list_fail(self):
        """Test not_empty constraint with empty list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_input([], "field", not_empty=True)

    def test_type_validation_correct(self):
        """Test type validation with correct type."""
        validate_input(42, "number", expected_type=int)
        validate_input("text", "string", expected_type=str)
        validate_input([1, 2, 3], "list", expected_type=list)

    def test_type_validation_incorrect(self):
        """Test type validation with incorrect type."""
        with pytest.raises(TypeError, match="must be of type"):
            validate_input("42", "number", expected_type=int)

    def test_min_value_validation_pass(self):
        """Test min_value validation passing."""
        validate_input(10, "number", min_value=5)
        validate_input(5.0, "number", min_value=5.0)

    def test_min_value_validation_fail(self):
        """Test min_value validation failing."""
        with pytest.raises(ValueError, match="must be >="):
            validate_input(3, "number", min_value=5)

    def test_max_value_validation_pass(self):
        """Test max_value validation passing."""
        validate_input(10, "number", max_value=15)

    def test_max_value_validation_fail(self):
        """Test max_value validation failing."""
        with pytest.raises(ValueError, match="must be <="):
            validate_input(20, "number", max_value=15)

    def test_min_length_validation_string_pass(self):
        """Test min_length validation for strings."""
        validate_input("hello", "text", min_length=3)

    def test_min_length_validation_string_fail(self):
        """Test min_length validation for strings failing."""
        with pytest.raises(ValueError, match="length must be >="):
            validate_input("hi", "text", min_length=5)

    def test_max_length_validation_string_pass(self):
        """Test max_length validation for strings."""
        validate_input("hello", "text", max_length=10)

    def test_max_length_validation_string_fail(self):
        """Test max_length validation for strings failing."""
        with pytest.raises(ValueError, match="length must be <="):
            validate_input("hello world", "text", max_length=5)

    def test_pattern_validation_pass(self):
        """Test pattern validation passing."""
        validate_input("hello123", "text", pattern=r'^[a-z0-9]+$')

    def test_pattern_validation_fail(self):
        """Test pattern validation failing."""
        with pytest.raises(ValueError, match="does not match required pattern"):
            validate_input("hello world!", "text", pattern=r'^[a-z0-9]+$')

    def test_allowed_values_validation_pass(self):
        """Test allowed_values validation passing."""
        validate_input("red", "color", allowed_values=["red", "green", "blue"])

    def test_allowed_values_validation_fail(self):
        """Test allowed_values validation failing."""
        with pytest.raises(ValueError, match="must be one of"):
            validate_input("yellow", "color", allowed_values=["red", "green", "blue"])

    def test_none_values_skip_validation(self):
        """Test that None values skip most validations."""
        # Should not raise even with constraints, as value is None
        validate_input(None, "field", min_value=5, max_value=10, pattern=r'^\d+$')


# ============================================================================
# Test validate_url
# ============================================================================

class TestValidateUrl:
    """Test validate_url function."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert validate_url("http://example.com") is True

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert validate_url("https://example.com") is True

    def test_url_with_path(self):
        """Test URL with path."""
        assert validate_url("https://example.com/path/to/resource") is True

    def test_url_with_query(self):
        """Test URL with query parameters."""
        assert validate_url("https://example.com/path?key=value") is True

    def test_empty_url(self):
        """Test empty URL."""
        assert validate_url("") is False

    def test_url_no_scheme(self):
        """Test URL without scheme."""
        assert validate_url("example.com") is False

    def test_url_no_netloc(self):
        """Test URL without network location."""
        assert validate_url("http://") is False

    def test_url_custom_scheme_allowed(self):
        """Test URL with custom allowed scheme."""
        assert validate_url("ftp://example.com", schemes=["ftp"]) is True

    def test_url_custom_scheme_not_allowed(self):
        """Test URL with scheme not in allowed list."""
        assert validate_url("ftp://example.com", schemes=["http", "https"]) is False

    def test_invalid_url_exception(self):
        """Test that invalid URLs return False."""
        assert validate_url("not a url at all!") is False


# ============================================================================
# Test validate_email
# ============================================================================

class TestValidateEmail:
    """Test validate_email function."""

    def test_valid_email(self):
        """Test valid email address."""
        assert validate_email("user@example.com") is True

    def test_valid_email_with_dots(self):
        """Test valid email with dots."""
        assert validate_email("user.name@example.com") is True

    def test_valid_email_with_plus(self):
        """Test valid email with plus sign."""
        assert validate_email("user+tag@example.com") is True

    def test_empty_email(self):
        """Test empty email."""
        assert validate_email("") is False

    def test_email_no_at_sign(self):
        """Test email without @ sign."""
        assert validate_email("userexample.com") is False

    def test_email_no_domain(self):
        """Test email without domain."""
        assert validate_email("user@") is False

    def test_email_no_tld(self):
        """Test email without TLD."""
        assert validate_email("user@example") is False

    def test_localhost_email_not_allowed(self):
        """Test localhost email not allowed by default."""
        assert validate_email("user@localhost") is False

    def test_localhost_email_allowed(self):
        """Test localhost email allowed when configured."""
        assert validate_email("user@localhost", allow_localhost=True) is True

    def test_invalid_characters(self):
        """Test email with invalid characters."""
        assert validate_email("user name@example.com") is False


# ============================================================================
# Test validate_port
# ============================================================================

class TestValidatePort:
    """Test validate_port function."""

    def test_valid_port_int(self):
        """Test valid port as integer."""
        assert validate_port(8080) is True

    def test_valid_port_string(self):
        """Test valid port as string."""
        assert validate_port("8080") is True

    def test_privileged_port_not_allowed(self):
        """Test privileged port not allowed by default."""
        assert validate_port(80) is False

    def test_privileged_port_allowed(self):
        """Test privileged port allowed when configured."""
        assert validate_port(80, allow_privileged=True) is True

    def test_port_too_low(self):
        """Test port number too low."""
        assert validate_port(0) is False

    def test_port_too_high(self):
        """Test port number too high."""
        assert validate_port(65536) is False

    def test_port_max_valid(self):
        """Test maximum valid port."""
        assert validate_port(65535) is True

    def test_port_invalid_string(self):
        """Test invalid port string."""
        assert validate_port("not a port") is False

    def test_port_float(self):
        """Test port as float."""
        assert validate_port(80.5) is False


# ============================================================================
# Test validate_ipv4
# ============================================================================

class TestValidateIpv4:
    """Test validate_ipv4 function."""

    def test_valid_ipv4(self):
        """Test valid IPv4 address."""
        assert validate_ipv4("192.168.1.1") is True

    def test_valid_ipv4_localhost(self):
        """Test localhost IPv4."""
        assert validate_ipv4("127.0.0.1") is True

    def test_valid_ipv4_zeros(self):
        """Test IPv4 with zeros."""
        assert validate_ipv4("0.0.0.0") is True

    def test_valid_ipv4_max(self):
        """Test IPv4 with max values."""
        assert validate_ipv4("255.255.255.255") is True

    def test_ipv4_non_string(self):
        """Test non-string input."""
        assert validate_ipv4(192) is False

    def test_ipv4_too_few_octets(self):
        """Test IPv4 with too few octets."""
        assert validate_ipv4("192.168.1") is False

    def test_ipv4_too_many_octets(self):
        """Test IPv4 with too many octets."""
        assert validate_ipv4("192.168.1.1.1") is False

    def test_ipv4_value_too_high(self):
        """Test IPv4 with value > 255."""
        assert validate_ipv4("192.168.1.256") is False

    def test_ipv4_value_too_low(self):
        """Test IPv4 with negative value."""
        assert validate_ipv4("192.168.1.-1") is False

    def test_ipv4_non_numeric(self):
        """Test IPv4 with non-numeric octets."""
        assert validate_ipv4("192.168.1.abc") is False


# ============================================================================
# Test validate_range
# ============================================================================

class TestValidateRange:
    """Test validate_range function."""

    def test_range_within_inclusive(self):
        """Test value within inclusive range."""
        assert validate_range(5, 1, 10, inclusive=True) is True

    def test_range_at_min_inclusive(self):
        """Test value at minimum with inclusive range."""
        assert validate_range(1, 1, 10, inclusive=True) is True

    def test_range_at_max_inclusive(self):
        """Test value at maximum with inclusive range."""
        assert validate_range(10, 1, 10, inclusive=True) is True

    def test_range_below_min_inclusive(self):
        """Test value below minimum."""
        assert validate_range(0, 1, 10, inclusive=True) is False

    def test_range_above_max_inclusive(self):
        """Test value above maximum."""
        assert validate_range(11, 1, 10, inclusive=True) is False

    def test_range_within_exclusive(self):
        """Test value within exclusive range."""
        assert validate_range(5, 1, 10, inclusive=False) is True

    def test_range_at_min_exclusive(self):
        """Test value at minimum with exclusive range."""
        assert validate_range(1, 1, 10, inclusive=False) is False

    def test_range_at_max_exclusive(self):
        """Test value at maximum with exclusive range."""
        assert validate_range(10, 1, 10, inclusive=False) is False

    def test_range_float_values(self):
        """Test range validation with floats."""
        assert validate_range(5.5, 1.0, 10.0, inclusive=True) is True

    def test_range_non_numeric(self):
        """Test range with non-numeric value."""
        assert validate_range("5", 1, 10) is False


# ============================================================================
# Test validate_dict_structure
# ============================================================================

class TestValidateDictStructure:
    """Test validate_dict_structure function."""

    def test_required_keys_present(self):
        """Test dict with all required keys."""
        data = {"key1": "value1", "key2": "value2"}
        assert validate_dict_structure(data, required_keys=["key1", "key2"]) is True

    def test_required_keys_missing(self):
        """Test dict missing required keys."""
        data = {"key1": "value1"}
        assert validate_dict_structure(data, required_keys=["key1", "key2"]) is False

    def test_optional_keys_allowed(self):
        """Test dict with optional keys."""
        data = {"key1": "value1", "key2": "value2", "opt1": "optional"}
        assert validate_dict_structure(
            data,
            required_keys=["key1", "key2"],
            optional_keys=["opt1"]
        ) is True

    def test_strict_mode_no_extra_keys(self):
        """Test strict mode with no extra keys."""
        data = {"key1": "value1", "opt1": "optional"}
        assert validate_dict_structure(
            data,
            required_keys=["key1"],
            optional_keys=["opt1"],
            strict=True
        ) is True

    def test_strict_mode_with_extra_keys(self):
        """Test strict mode with extra keys."""
        data = {"key1": "value1", "extra": "not allowed"}
        assert validate_dict_structure(
            data,
            required_keys=["key1"],
            strict=True
        ) is False

    def test_non_dict_input(self):
        """Test with non-dict input."""
        assert validate_dict_structure("not a dict", required_keys=["key1"]) is False

    def test_empty_required_keys(self):
        """Test with empty required keys list."""
        data = {"any": "value"}
        assert validate_dict_structure(data, required_keys=[]) is True


# ============================================================================
# Test validate_path
# ============================================================================

class TestValidatePath:
    """Test validate_path function."""

    def test_valid_path_not_checking_existence(self):
        """Test valid path without checking existence."""
        assert validate_path("/some/path/to/file") is True

    def test_existing_path(self):
        """Test path that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert validate_path(tmpdir, must_exist=True) is True

    def test_non_existing_path_must_exist(self):
        """Test non-existing path when must_exist=True."""
        assert validate_path("/nonexistent/path/file.txt", must_exist=True) is False

    def test_non_existing_path_optional(self):
        """Test non-existing path when existence not required."""
        assert validate_path("/nonexistent/path/file.txt", must_exist=False) is True

    def test_file_exists(self):
        """Test with existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        try:
            assert validate_path(tmp_path, must_exist=True) is True
        finally:
            os.unlink(tmp_path)

    def test_invalid_path_characters(self):
        """Test path with invalid characters (OS-dependent)."""
        # Most systems will handle this, so just test it doesn't crash
        result = validate_path("path/to/file")
        assert isinstance(result, bool)


# ============================================================================
# Test validate_json_schema
# ============================================================================

class TestValidateJsonSchema:
    """Test validate_json_schema function."""

    def test_valid_simple_schema(self):
        """Test valid data against simple schema."""
        data = {"name": "John", "age": 30}
        schema = {
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
        assert validate_json_schema(data, schema) is True

    def test_missing_required_field(self):
        """Test data missing required field."""
        data = {"name": "John"}
        schema = {
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
        assert validate_json_schema(data, schema) is False

    def test_wrong_string_type(self):
        """Test data with wrong type for string field."""
        data = {"name": 123}
        schema = {
            "properties": {
                "name": {"type": "string"}
            }
        }
        assert validate_json_schema(data, schema) is False

    def test_wrong_integer_type(self):
        """Test data with wrong type for integer field."""
        data = {"age": "thirty"}
        schema = {
            "properties": {
                "age": {"type": "integer"}
            }
        }
        assert validate_json_schema(data, schema) is False

    def test_number_type_accepts_int_and_float(self):
        """Test number type accepts both int and float."""
        data1 = {"value": 42}
        data2 = {"value": 42.5}
        schema = {
            "properties": {
                "value": {"type": "number"}
            }
        }
        assert validate_json_schema(data1, schema) is True
        assert validate_json_schema(data2, schema) is True

    def test_boolean_type(self):
        """Test boolean type validation."""
        data = {"active": True}
        schema = {
            "properties": {
                "active": {"type": "boolean"}
            }
        }
        assert validate_json_schema(data, schema) is True

    def test_array_type(self):
        """Test array type validation."""
        data = {"items": [1, 2, 3]}
        schema = {
            "properties": {
                "items": {"type": "array"}
            }
        }
        assert validate_json_schema(data, schema) is True

    def test_object_type(self):
        """Test object type validation."""
        data = {"config": {"key": "value"}}
        schema = {
            "properties": {
                "config": {"type": "object"}
            }
        }
        assert validate_json_schema(data, schema) is True

    def test_non_dict_data(self):
        """Test with non-dict data."""
        assert validate_json_schema("not a dict", {}) is False

    def test_non_dict_schema(self):
        """Test with non-dict schema."""
        assert validate_json_schema({}, "not a dict") is False

    def test_extra_fields_allowed(self):
        """Test that extra fields not in schema are allowed."""
        data = {"name": "John", "extra": "field"}
        schema = {
            "required": ["name"],
            "properties": {
                "name": {"type": "string"}
            }
        }
        assert validate_json_schema(data, schema) is True
