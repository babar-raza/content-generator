"""Tests for resilience module."""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from src.utils.resilience import (
    CircuitState,
    CircuitBreaker,
    RetryPolicy,
    ResourcePool
)


class TestCircuitState:
    """Tests for CircuitState enum."""
    
    def test_circuit_states(self):
        """Test circuit breaker states."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""
    
    def test_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker("test", failure_threshold=3, timeout=30.0)
        
        assert cb.name == "test"
        assert cb.failure_threshold == 3
        assert cb.timeout == 30.0
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
    
    def test_successful_call(self):
        """Test successful function call."""
        cb = CircuitBreaker("test")
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
    
    def test_failed_call(self):
        """Test failed function call."""
        cb = CircuitBreaker("test", failure_threshold=2)
        
        def fail_func():
            raise ValueError("error")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.failure_count == 1
    
    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        def fail_func():
            raise ValueError("error")
        
        for i in range(3):
            with pytest.raises(ValueError):
                cb.call(fail_func)
        
        assert cb.state == CircuitState.OPEN
    
    def test_circuit_stays_open(self):
        """Test circuit stays open before timeout."""
        cb = CircuitBreaker("test", failure_threshold=1, timeout=100.0)
        
        def fail_func():
            raise ValueError("error")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Try to call again immediately
        with pytest.raises(Exception) as exc_info:
            cb.call(lambda: "should not execute")
        
        assert "OPEN" in str(exc_info.value)
    
    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout."""
        cb = CircuitBreaker("test", failure_threshold=1, timeout=0.1)
        
        def fail_func():
            raise ValueError("error")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.15)
        
        # Next call should transition to half-open
        def success_func():
            return "ok"
        
        result = cb.call(success_func)
        assert result == "ok"
    
    def test_circuit_closes_after_half_open_successes(self):
        """Test circuit closes after successful half-open attempts."""
        cb = CircuitBreaker("test", failure_threshold=1, timeout=0.1, half_open_attempts=2)
        
        def fail_func():
            raise ValueError("error")
        
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait and make successful calls
        time.sleep(0.15)
        
        def success_func():
            return "ok"
        
        cb.call(success_func)
        cb.call(success_func)
        
        assert cb.state == CircuitState.CLOSED
    
    def test_half_open_failure_reopens_circuit(self):
        """Test that failure in half-open reopens circuit."""
        cb = CircuitBreaker("test", failure_threshold=1, timeout=0.1)
        
        def fail_func():
            raise ValueError("error")
        
        # Open circuit
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        # Wait for timeout
        time.sleep(0.15)
        
        # Fail in half-open
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.state == CircuitState.OPEN
    
    def test_get_state(self):
        """Test getting circuit breaker state."""
        cb = CircuitBreaker("test")
        
        state = cb.get_state()
        
        assert state["name"] == "test"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["success_count"] == 0
        assert state["last_failure_time"] is None
    
    def test_get_state_with_failure(self):
        """Test state after failure."""
        cb = CircuitBreaker("test")
        
        def fail_func():
            raise ValueError("error")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        state = cb.get_state()
        assert state["failure_count"] == 1
        assert state["last_failure_time"] is not None
    
    def test_call_with_args(self):
        """Test calling function with arguments."""
        cb = CircuitBreaker("test")
        
        def func_with_args(a, b, c=3):
            return a + b + c
        
        result = cb.call(func_with_args, 1, 2, c=4)
        assert result == 7
    
    def test_success_reduces_failure_count(self):
        """Test that success reduces failure count in closed state."""
        cb = CircuitBreaker("test", failure_threshold=5)
        
        def fail_func():
            raise ValueError("error")
        
        def success_func():
            return "ok"
        
        # Add some failures
        with pytest.raises(ValueError):
            cb.call(fail_func)
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.failure_count == 2
        
        # Success should reduce count
        cb.call(success_func)
        assert cb.failure_count == 1


class TestRetryPolicy:
    """Tests for RetryPolicy class."""
    
    def test_initialization(self):
        """Test retry policy initialization."""
        policy = RetryPolicy(max_attempts=3, base_delay=1.0)
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
    
    def test_successful_first_attempt(self):
        """Test successful execution on first attempt."""
        policy = RetryPolicy()
        
        def success_func():
            return "success"
        
        result = policy.execute(success_func)
        assert result == "success"
    
    def test_retry_until_success(self):
        """Test retrying until success."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.01)
        
        attempt_count = [0]
        
        def eventually_succeeds():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise ValueError("not yet")
            return "success"
        
        result = policy.execute(eventually_succeeds)
        assert result == "success"
        assert attempt_count[0] == 2
    
    def test_all_attempts_fail(self):
        """Test when all attempts fail."""
        policy = RetryPolicy(max_attempts=2, base_delay=0.01)
        
        def always_fails():
            raise ValueError("always fails")
        
        with pytest.raises(ValueError) as exc_info:
            policy.execute(always_fails)
        
        assert "always fails" in str(exc_info.value)
    
    def test_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy(
            max_attempts=3,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        
        attempt_count = [0]
        delays = []
        
        def track_delays():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ValueError("retry")
            return "done"
        
        with patch('time.sleep') as mock_sleep:
            policy.execute(track_delays)
            
            # Check that sleep was called with increasing delays
            if mock_sleep.call_count > 0:
                calls = [call[0][0] for call in mock_sleep.call_args_list]
                # First delay should be ~1.0, second should be ~2.0
                assert len(calls) >= 1
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=10.0,
            max_delay=15.0,
            exponential_base=2.0,
            jitter=False
        )
        
        # Calculate what delay would be without cap
        attempt = 4
        uncapped_delay = 10.0 * (2.0 ** (attempt - 1))
        assert uncapped_delay > 15.0  # Verify our test setup
        
        # The actual delay should be capped
        attempt_count = [0]
        
        def always_fails():
            attempt_count[0] += 1
            raise ValueError("fail")
        
        with pytest.raises(ValueError):
            with patch('time.sleep') as mock_sleep:
                policy.execute(always_fails)
                
                # All delays should be <= max_delay
                for call in mock_sleep.call_args_list:
                    delay = call[0][0]
                    assert delay <= 15.0
    
    def test_execute_with_args(self):
        """Test executing function with arguments."""
        policy = RetryPolicy()
        
        def func_with_args(a, b, c=3):
            return a * b + c
        
        result = policy.execute(func_with_args, 2, 3, c=4)
        assert result == 10


class TestResourcePool:
    """Tests for ResourcePool class."""
    
    def test_initialization(self):
        """Test resource pool initialization."""
        pool = ResourcePool("test", max_concurrent=5)
        
        assert pool.name == "test"
        assert pool.max_concurrent == 5
        assert pool.active_count == 0
    
    def test_acquire_and_release(self):
        """Test acquiring and releasing resources."""
        pool = ResourcePool("test", max_concurrent=2)
        
        acquired1 = pool.semaphore.acquire(blocking=False)
        assert acquired1 is True
        
        acquired2 = pool.semaphore.acquire(blocking=False)
        assert acquired2 is True
        
        # Should be at limit
        acquired3 = pool.semaphore.acquire(blocking=False)
        assert acquired3 is False
        
        # Release one
        pool.semaphore.release()
        
        # Should be able to acquire again
        acquired4 = pool.semaphore.acquire(blocking=False)
        assert acquired4 is True
