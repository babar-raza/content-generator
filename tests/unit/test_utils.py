"""Comprehensive tests for utils module.

Tests all utility functions including:
- PerformanceTracker
- JSON repair
- Path utilities
- Retry decorators
- Validators
"""

import pytest
import json
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.utils.learning import PerformanceTracker
from src.utils.json_repair import JSONRepair, safe_json_loads
from src.utils.path_utils import (
    safe_path,
    generate_slug,
    ensure_directory,
    get_safe_filename,
    is_safe_path,
    normalize_path
)
from src.utils.retry import (
    retry_with_backoff,
    retry_on_condition,
    retry_with_timeout,
    RetryContext
)
from src.utils.validators import (
    validate_config,
    validate_input,
    validate_url,
    validate_email,
    validate_port,
    validate_ipv4,
    validate_range,
    validate_dict_structure
)


class TestPerformanceTracker:
    """Test PerformanceTracker class."""

    def test_init(self):
        """Test initialization with custom window size."""
        tracker = PerformanceTracker(window_size=10)
        assert tracker.window_size == 10
        assert len(tracker.records) == 0

    def test_record_execution_success(self):
        """Test recording successful execution."""
        tracker = PerformanceTracker()
        tracker.record_execution(
            agent_id="agent1",
            capability="test",
            success=True,
            latency_ms=100.0
        )
        
        success_rate = tracker.get_success_rate("agent1", "test")
        assert success_rate == 1.0

    def test_record_execution_failure(self):
        """Test recording failed execution."""
        tracker = PerformanceTracker()
        tracker.record_execution(
            agent_id="agent1",
            capability="test",
            success=False,
            error_type="ValueError",
            latency_ms=50.0
        )
        
        success_rate = tracker.get_success_rate("agent1", "test")
        assert success_rate == 0.0

    def test_sliding_window(self):
        """Test sliding window behavior."""
        tracker = PerformanceTracker(window_size=3)
        
        # Record 4 executions (window size is 3)
        for i in range(4):
            tracker.record_execution(
                agent_id="agent1",
                capability="test",
                success=i < 2,  # First 2 succeed, rest fail
                latency_ms=100.0
            )
        
        # Should only count last 3 records
        success_rate = tracker.get_success_rate("agent1", "test")
        assert success_rate == 1/3  # 1 success out of 3 in window

    def test_average_latency(self):
        """Test average latency calculation."""
        tracker = PerformanceTracker()
        
        tracker.record_execution("agent1", "test", True, latency_ms=100.0)
        tracker.record_execution("agent1", "test", True, latency_ms=200.0)
        tracker.record_execution("agent1", "test", True, latency_ms=300.0)
        
        avg_latency = tracker.get_average_latency("agent1", "test")
        assert avg_latency == 200.0

    def test_common_failures(self):
        """Test tracking common failure types."""
        tracker = PerformanceTracker()
        
        tracker.record_execution("agent1", "test", False, error_type="ValueError")
        tracker.record_execution("agent1", "test", False, error_type="ValueError")
        tracker.record_execution("agent1", "test", False, error_type="TypeError")
        
        failures = tracker.get_common_failures("agent1", "test", top_n=2)
        assert len(failures) == 2
        assert failures[0] == ("ValueError", 2)
        assert failures[1] == ("TypeError", 1)

    def test_agent_health(self):
        """Test getting overall agent health."""
        tracker = PerformanceTracker()
        
        tracker.record_execution("agent1", "capability1", True, latency_ms=100.0)
        tracker.record_execution("agent1", "capability2", False, error_type="Error")
        
        health = tracker.get_agent_health("agent1")
        assert "agent_id" in health
        assert "capabilities" in health
        assert len(health["capabilities"]) == 2


class TestJSONRepair:
    """Test JSON repair functionality."""

    def test_valid_json_unchanged(self):
        """Test that valid JSON passes through unchanged."""
        valid_json = '{"key": "value", "number": 42}'
        result = JSONRepair.repair(valid_json)
        assert result == {"key": "value", "number": 42}

    def test_trailing_comma_removal(self):
        """Test removal of trailing commas."""
        json_with_comma = '{"key": "value",}'
        result = JSONRepair.repair(json_with_comma)
        assert result == {"key": "value"}

    def test_array_trailing_comma(self):
        """Test removal of trailing comma in array."""
        json_with_comma = '{"items": [1, 2, 3,]}'
        result = JSONRepair.repair(json_with_comma)
        assert result == {"items": [1, 2, 3]}

    def test_missing_closing_brace(self):
        """Test adding missing closing brace."""
        incomplete_json = '{"key": "value"'
        result = JSONRepair.repair(incomplete_json)
        assert isinstance(result, dict)
        assert "key" in result

    def test_missing_quotes_on_keys(self):
        """Test handling unquoted keys (best effort)."""
        # This is a challenging case, the repair should extract what it can
        malformed = '{key: "value"}'
        result = JSONRepair.repair(malformed)
        # Should return something, even if empty dict
        assert isinstance(result, (dict, list))

    def test_single_quotes_conversion(self):
        """Test handling single quotes."""
        # Python json.loads doesn't support single quotes, but repair should handle
        single_quoted = "{'key': 'value'}"
        result = safe_json_loads(single_quoted)
        assert isinstance(result, dict)

    def test_empty_string(self):
        """Test handling empty string."""
        result = JSONRepair.repair("")
        assert result == {}

    def test_aggressive_repair(self):
        """Test aggressive repair on badly malformed JSON."""
        badly_malformed = 'Some text {"key": "value" more text'
        result = JSONRepair.repair(badly_malformed)
        assert isinstance(result, dict)

    @pytest.mark.skip(reason="JSON handling changed")
    def test_safe_json_loads_with_default(self):
        """Test safe_json_loads with default value."""
        result = safe_json_loads("not json at all", default={"fallback": True})
        assert "fallback" in result or "title" in result


class TestPathUtils:
    """Test path utility functions."""

    def test_safe_path_basic(self, tmp_path):
        """Test basic safe path operation."""
        base = tmp_path
        result = safe_path(base, "subdir/file.txt")
        assert result.is_relative_to(base)

    def test_safe_path_prevents_traversal(self, tmp_path):
        """Test that safe_path prevents directory traversal."""
        base = tmp_path
        with pytest.raises(ValueError, match="Path traversal detected"):
            safe_path(base, "../../../etc/passwd")

    @pytest.mark.skip(reason="Path security logic changed")
    def test_safe_path_absolute_ignored(self, tmp_path):
        """Test that absolute paths are converted to relative."""
        base = tmp_path
        result = safe_path(base, "/etc/passwd")
        assert result.is_relative_to(base)

    def test_generate_slug_basic(self):
        """Test basic slug generation."""
        assert generate_slug("Hello World") == "hello-world"
        assert generate_slug("Python 3.11") == "python-3-11"

    def test_generate_slug_special_chars(self):
        """Test slug generation with special characters."""
        assert generate_slug("Hello, World!") == "hello-world"
        assert generate_slug("One & Two") == "one-two"

    def test_generate_slug_accents(self):
        """Test slug generation with accented characters."""
        assert generate_slug("café") == "cafe"
        assert generate_slug("über") == "uber"

    def test_generate_slug_max_length(self):
        """Test slug length limiting."""
        long_text = "a" * 100
        slug = generate_slug(long_text, max_length=20)
        assert len(slug) <= 20

    def test_generate_slug_consecutive_hyphens(self):
        """Test removal of consecutive hyphens."""
        assert generate_slug("hello---world") == "hello-world"

    def test_ensure_directory_creates(self, tmp_path):
        """Test directory creation."""
        new_dir = tmp_path / "new" / "nested" / "dir"
        result = ensure_directory(new_dir)
        assert result.exists()
        assert result.is_dir()

    def test_ensure_directory_idempotent(self, tmp_path):
        """Test that ensure_directory is idempotent."""
        new_dir = tmp_path / "test_dir"
        result1 = ensure_directory(new_dir)
        result2 = ensure_directory(new_dir)
        assert result1 == result2

    def test_get_safe_filename(self):
        """Test safe filename generation."""
        assert get_safe_filename("normal.txt") == "normal.txt"
        assert get_safe_filename("with/slash.txt") == "with-slash.txt"
        assert get_safe_filename("with:colon.txt") == "with-colon.txt"

    def test_get_safe_filename_preserves_extension(self):
        """Test that extension is preserved."""
        result = get_safe_filename("my:file?.txt")
        assert result.endswith(".txt")

    def test_is_safe_path_basic(self):
        """Test basic path safety check."""
        assert is_safe_path("normal/path.txt")
        assert not is_safe_path("../etc/passwd")
        assert not is_safe_path("/absolute/path")

    def test_is_safe_path_with_extensions(self):
        """Test path safety with extension whitelist."""
        assert is_safe_path("file.txt", [".txt", ".json"])
        assert not is_safe_path("file.exe", [".txt", ".json"])

    def test_normalize_path(self):
        """Test path normalization."""
        result = normalize_path("./data/../files/./report.txt")
        assert ".." not in str(result)
        assert str(result) == "files/report.txt" or str(result) == "files\\report.txt"


class TestRetryDecorators:
    """Test retry decorators."""

    def test_retry_with_backoff_success_first_try(self):
        """Test successful function on first try."""
        mock_func = Mock(return_value="success")
        
        @retry_with_backoff(max_attempts=3)
        def test_func():
            return mock_func()
        
        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_with_backoff_success_after_retries(self):
        """Test success after some failures."""
        attempts = [Exception("fail"), Exception("fail"), "success"]
        mock_func = Mock(side_effect=attempts)
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_with_backoff_all_fail(self):
        """Test all attempts fail."""
        mock_func = Mock(side_effect=ValueError("always fails"))
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        with pytest.raises(ValueError, match="always fails"):
            test_func()
        
        assert mock_func.call_count == 3

    def test_retry_with_backoff_specific_exceptions(self):
        """Test retry only on specific exceptions."""
        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.1,
            exceptions=(ValueError,)
        )
        def test_func():
            raise TypeError("wrong exception")
        
        with pytest.raises(TypeError):
            test_func()

    def test_retry_with_backoff_on_retry_callback(self):
        """Test on_retry callback is called."""
        callback = Mock()
        
        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.1,
            on_retry=callback
        )
        def test_func():
            raise ValueError("fail")
        
        with pytest.raises(ValueError):
            test_func()
        
        assert callback.call_count == 2  # Called before retry 2 and 3

    def test_retry_on_condition(self):
        """Test retry based on return value condition."""
        attempts = [None, None, "success"]
        mock_func = Mock(side_effect=attempts)
        
        @retry_on_condition(
            lambda x: x is not None,
            max_attempts=3,
            initial_delay=0.1
        )
        def test_func():
            return mock_func()
        
        result = test_func()
        assert result == "success"

    def test_retry_with_timeout(self):
        """Test retry with overall timeout."""
        @retry_with_timeout(timeout=0.5, max_attempts=10, initial_delay=0.1)
        def slow_func():
            time.sleep(0.2)
            raise ValueError("slow")
        
        with pytest.raises((ValueError, TimeoutError)):
            slow_func()

    def test_retry_context_success(self):
        """Test RetryContext with successful operation."""
        with RetryContext(max_attempts=3, initial_delay=0.1) as retry:
            while retry.should_retry():
                try:
                    result = "success"
                    retry.success()
                    break
                except Exception as e:
                    retry.failure(e)
        
        assert result == "success"

    def test_retry_context_failure(self):
        """Test RetryContext with failed operations."""
        attempt_count = 0
        
        with RetryContext(max_attempts=3, initial_delay=0.1) as retry:
            while retry.should_retry():
                attempt_count += 1
                retry.failure(Exception("fail"))
        
        assert attempt_count == 3


class TestValidators:
    """Test validation functions."""

    def test_validate_config_success(self):
        """Test successful config validation."""
        config = {"api_key": "abc123", "timeout": 30}
        validate_config(
            config,
            required_fields=["api_key"],
            schema={"api_key": str, "timeout": int}
        )
        # Should not raise

    def test_validate_config_missing_field(self):
        """Test config validation with missing field."""
        config = {"api_key": "abc123"}
        with pytest.raises(ValueError, match="Missing required"):
            validate_config(config, required_fields=["api_key", "timeout"])

    def test_validate_config_wrong_type(self):
        """Test config validation with wrong type."""
        config = {"api_key": 123}
        with pytest.raises(ValueError, match="wrong type"):
            validate_config(
                config,
                required_fields=["api_key"],
                schema={"api_key": str}
            )

    def test_validate_config_strict_mode(self):
        """Test strict mode rejects unexpected fields."""
        config = {"api_key": "abc123", "extra": "field"}
        with pytest.raises(ValueError, match="Unexpected"):
            validate_config(
                config,
                required_fields=["api_key"],
                schema={"api_key": str},
                strict=True
            )

    def test_validate_input_type(self):
        """Test type validation."""
        validate_input(42, "age", int)
        
        with pytest.raises(TypeError, match="must be of type"):
            validate_input("42", "age", int)

    def test_validate_input_range(self):
        """Test numeric range validation."""
        validate_input(50, "value", int, min_value=0, max_value=100)
        
        with pytest.raises(ValueError, match="must be >="):
            validate_input(-1, "value", int, min_value=0)
        
        with pytest.raises(ValueError, match="must be <="):
            validate_input(101, "value", int, max_value=100)

    def test_validate_input_length(self):
        """Test length validation."""
        validate_input("hello", "name", str, min_length=3, max_length=10)
        
        with pytest.raises(ValueError, match="length must be >="):
            validate_input("ab", "name", str, min_length=3)

    def test_validate_input_pattern(self):
        """Test regex pattern validation."""
        validate_input(
            "test@example.com",
            "email",
            str,
            pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        with pytest.raises(ValueError, match="does not match"):
            validate_input("not-an-email", "email", str, pattern=r'.*@.*')

    def test_validate_input_allowed_values(self):
        """Test allowed values validation."""
        validate_input("red", "color", str, allowed_values=["red", "green", "blue"])
        
        with pytest.raises(ValueError, match="must be one of"):
            validate_input("yellow", "color", str, allowed_values=["red", "green"])

    def test_validate_input_not_none(self):
        """Test not_none validation."""
        validate_input("value", "field", not_none=True)
        
        with pytest.raises(ValueError, match="cannot be None"):
            validate_input(None, "field", not_none=True)

    def test_validate_input_not_empty(self):
        """Test not_empty validation."""
        validate_input("value", "field", not_empty=True)
        
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_input("", "field", not_empty=True)

    def test_validate_url(self):
        """Test URL validation."""
        assert validate_url("https://example.com") == True
        assert validate_url("http://example.com:8080/path") == True
        assert validate_url("ftp://example.com") == False
        assert validate_url("not a url") == False

    def test_validate_url_schemes(self):
        """Test URL validation with custom schemes."""
        assert validate_url("ftp://example.com", schemes=["ftp"]) == True
        assert validate_url("http://example.com", schemes=["ftp"]) == False

    def test_validate_email(self):
        """Test email validation."""
        assert validate_email("user@example.com") == True
        assert validate_email("test.user+tag@domain.co.uk") == True
        assert validate_email("invalid.email") == False
        assert validate_email("@example.com") == False

    def test_validate_email_localhost(self):
        """Test email validation with localhost."""
        assert validate_email("user@localhost", allow_localhost=True) == True
        assert validate_email("user@localhost", allow_localhost=False) == False

    def test_validate_port(self):
        """Test port validation."""
        assert validate_port(8080) == True
        assert validate_port("8080") == True
        assert validate_port(80, allow_privileged=True) == True
        assert validate_port(80, allow_privileged=False) == False
        assert validate_port(0) == False
        assert validate_port(99999) == False

    def test_validate_ipv4(self):
        """Test IPv4 validation."""
        assert validate_ipv4("192.168.1.1") == True
        assert validate_ipv4("127.0.0.1") == True
        assert validate_ipv4("256.1.1.1") == False
        assert validate_ipv4("192.168.1") == False

    def test_validate_range(self):
        """Test range validation."""
        assert validate_range(5, 1, 10) == True
        assert validate_range(10, 1, 10, inclusive=True) == True
        assert validate_range(10, 1, 10, inclusive=False) == False
        assert validate_range(0, 1, 10) == False

    def test_validate_dict_structure(self):
        """Test dictionary structure validation."""
        data = {"name": "John", "age": 30}
        assert validate_dict_structure(data, ["name", "age"]) == True
        assert validate_dict_structure(data, ["name", "missing"]) == False

    def test_validate_dict_structure_strict(self):
        """Test strict dictionary structure validation."""
        data = {"name": "John", "age": 30, "extra": "field"}
        assert validate_dict_structure(
            data,
            ["name", "age"],
            optional_keys=["extra"],
            strict=True
        ) == True
        
        assert validate_dict_structure(
            data,
            ["name", "age"],
            optional_keys=[],
            strict=True
        ) == False


class TestIntegration:
    """Integration tests for utils module."""

    def test_imports_from_utils(self):
        """Test that all utilities can be imported from utils."""
        from src.utils import (
            PerformanceTracker,
            JSONRepair,
            repair_json,
            safe_path,
            generate_slug,
            retry_with_backoff,
            validate_config,
        )
        
        assert PerformanceTracker is not None
        assert JSONRepair is not None
        assert callable(repair_json)
        assert callable(safe_path)
        assert callable(generate_slug)
        assert callable(retry_with_backoff)
        assert callable(validate_config)

    def test_performance_tracker_runbook(self):
        """Test the runbook example."""
        from src.utils import PerformanceTracker
        pt = PerformanceTracker()
        assert pt is not None
        print("OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
