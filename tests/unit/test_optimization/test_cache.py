"""
Unit tests for cache module.

Tests the caching decorator and cache key generation.
"""

import pytest
from src.optimization.cache import cache_result


def test_cache_result_decorator_basic():
    """Test basic caching functionality."""
    call_count = 0

    @cache_result(max_size=10, ttl_seconds=60)
    def expensive_function(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call - should execute function
    result1 = expensive_function(5)
    assert result1 == 10
    assert call_count == 1

    # Second call with same arg - should use cache
    result2 = expensive_function(5)
    assert result2 == 10
    assert call_count == 1  # Should not increment

    # Call with different arg - should execute function
    result3 = expensive_function(10)
    assert result3 == 20
    assert call_count == 2


def test_cache_result_with_kwargs():
    """Test caching with keyword arguments."""
    @cache_result(max_size=10, ttl_seconds=60)
    def func_with_kwargs(a: int, b: int = 2) -> int:
        return a + b

    result1 = func_with_kwargs(5, b=3)
    assert result1 == 8

    result2 = func_with_kwargs(5, b=3)
    assert result2 == 8


def test_cache_result_with_complex_types():
    """Test caching with complex argument types."""
    call_count = 0

    @cache_result(max_size=10, ttl_seconds=60)
    def func_with_dict(data: dict) -> str:
        nonlocal call_count
        call_count += 1
        return str(data)

    # Should handle dict arguments via pickle
    result1 = func_with_dict({"key": "value"})
    assert call_count == 1

    result2 = func_with_dict({"key": "value"})
    assert call_count == 1  # Should use cache
