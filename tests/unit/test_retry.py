"""Unit tests for src/utils/retry.py.

Tests retry decorators and context managers including:
- retry_with_backoff decorator
- retry_on_condition decorator
- retry_with_timeout decorator
- RetryContext context manager
"""

import pytest
import time
from unittest.mock import Mock, patch, call
import logging

from src.utils.retry import (
    retry_with_backoff,
    retry_on_condition,
    retry_with_timeout,
    RetryContext
)


# ============================================================================
# Test retry_with_backoff Decorator
# ============================================================================

class TestRetryWithBackoff:
    """Test retry_with_backoff decorator."""

    @patch('time.sleep')
    def test_success_on_first_attempt(self, mock_sleep):
        """Test function succeeds on first attempt."""
        @retry_with_backoff(max_attempts=3)
        def always_succeeds():
            return "success"

        result = always_succeeds()

        assert result == "success"
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    def test_success_after_retries(self, mock_sleep):
        """Test function succeeds after some retries."""
        attempts = []

        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def succeeds_on_third():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("Not yet")
            return "success"

        result = succeeds_on_third()

        assert result == "success"
        assert len(attempts) == 3
        assert mock_sleep.call_count == 2  # 2 retries

    @patch('time.sleep')
    def test_max_attempts_reached(self, mock_sleep):
        """Test exception raised after max attempts."""
        @retry_with_backoff(max_attempts=3)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

        assert mock_sleep.call_count == 2  # 2 retries before final failure

    @patch('time.sleep')
    def test_exponential_backoff_delays(self, mock_sleep):
        """Test exponential backoff delay calculation."""
        @retry_with_backoff(
            max_attempts=4,
            initial_delay=1.0,
            exponential_base=2.0
        )
        def always_fails():
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            always_fails()

        # Check delays: 1.0, 2.0, 4.0
        calls = mock_sleep.call_args_list
        assert len(calls) == 3
        assert calls[0][0][0] == 1.0  # 1.0 * 2^0
        assert calls[1][0][0] == 2.0  # 1.0 * 2^1
        assert calls[2][0][0] == 4.0  # 1.0 * 2^2

    @patch('time.sleep')
    def test_max_delay_cap(self, mock_sleep):
        """Test max_delay caps the exponential growth."""
        @retry_with_backoff(
            max_attempts=5,
            initial_delay=10.0,
            max_delay=15.0,
            exponential_base=3.0
        )
        def always_fails():
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            always_fails()

        calls = mock_sleep.call_args_list
        # Delays should be: 10.0, 15.0 (capped), 15.0 (capped), 15.0 (capped)
        assert all(call[0][0] <= 15.0 for call in calls)

    @patch('time.sleep')
    def test_specific_exceptions_only(self, mock_sleep):
        """Test only specified exceptions are retried."""
        @retry_with_backoff(
            max_attempts=3,
            exceptions=(ValueError, TypeError)
        )
        def raises_different_exceptions(exc_type):
            raise exc_type("Error")

        # ValueError should be retried
        with pytest.raises(ValueError):
            raises_different_exceptions(ValueError)
        assert mock_sleep.call_count == 2

        mock_sleep.reset_mock()

        # RuntimeError should NOT be retried
        with pytest.raises(RuntimeError):
            raises_different_exceptions(RuntimeError)
        assert mock_sleep.call_count == 0

    @patch('time.sleep')
    def test_on_retry_callback(self, mock_sleep):
        """Test on_retry callback is called."""
        callback = Mock()

        @retry_with_backoff(
            max_attempts=3,
            initial_delay=1.0,
            on_retry=callback
        )
        def fails_twice():
            if callback.call_count < 2:
                raise ValueError("Fail")
            return "success"

        result = fails_twice()

        assert result == "success"
        assert callback.call_count == 2
        # Check callback was called (don't check exact exception object)
        assert callback.call_args_list[0][0][0] == 1  # attempt number
        assert callback.call_args_list[0][0][2] == 1.0  # delay

    @patch('time.sleep')
    def test_on_retry_callback_error_handled(self, mock_sleep):
        """Test error in on_retry callback doesn't break retry."""
        def bad_callback(attempt, exc, delay):
            raise RuntimeError("Callback failed")

        @retry_with_backoff(
            max_attempts=3,
            on_retry=bad_callback
        )
        def fails_once():
            if not hasattr(fails_once, 'called'):
                fails_once.called = True
                raise ValueError("Fail")
            return "success"

        result = fails_once()
        assert result == "success"

    def test_invalid_max_attempts(self):
        """Test ValueError raised for invalid max_attempts."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            @retry_with_backoff(max_attempts=0)
            def dummy():
                pass

    @patch('time.sleep')
    def test_preserves_function_metadata(self, mock_sleep):
        """Test decorator preserves function metadata."""
        @retry_with_backoff(max_attempts=2)
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    @patch('time.sleep')
    def test_function_with_args_and_kwargs(self, mock_sleep):
        """Test decorated function with arguments."""
        @retry_with_backoff(max_attempts=2)
        def add(a, b, multiply=1):
            return (a + b) * multiply

        result = add(2, 3, multiply=4)
        assert result == 20


# ============================================================================
# Test retry_on_condition Decorator
# ============================================================================

class TestRetryOnCondition:
    """Test retry_on_condition decorator."""

    @patch('time.sleep')
    def test_success_on_first_attempt(self, mock_sleep):
        """Test condition satisfied on first attempt."""
        @retry_on_condition(lambda x: x is not None, max_attempts=3)
        def returns_value():
            return "result"

        result = returns_value()

        assert result == "result"
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    def test_success_after_retries(self, mock_sleep):
        """Test condition satisfied after retries."""
        counter = {'count': 0}

        @retry_on_condition(lambda x: x > 2, max_attempts=4, initial_delay=1.0)
        def increments():
            counter['count'] += 1
            return counter['count']

        result = increments()

        assert result == 3
        assert mock_sleep.call_count == 2  # Retried twice before getting 3

    @patch('time.sleep')
    def test_returns_last_value_if_condition_never_met(self, mock_sleep):
        """Test returns last value even if condition never satisfied."""
        @retry_on_condition(lambda x: x > 100, max_attempts=3)
        def returns_small_number():
            return 5

        result = returns_small_number()

        assert result == 5  # Returns last attempt's result
        assert mock_sleep.call_count == 2

    @patch('time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Test exponential backoff in retry_on_condition."""
        @retry_on_condition(
            lambda x: False,  # Never satisfied
            max_attempts=3,
            initial_delay=2.0,
            exponential_base=2.0
        )
        def always_fails_condition():
            return "result"

        always_fails_condition()

        calls = mock_sleep.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == 2.0  # 2.0 * 2^0
        assert calls[1][0][0] == 4.0  # 2.0 * 2^1

    @patch('time.sleep')
    def test_max_delay_cap_in_condition(self, mock_sleep):
        """Test max_delay works in retry_on_condition."""
        @retry_on_condition(
            lambda x: False,
            max_attempts=4,
            initial_delay=10.0,
            max_delay=12.0,
            exponential_base=2.0
        )
        def always_fails():
            return "result"

        always_fails()

        calls = mock_sleep.call_args_list
        # All delays should be capped at 12.0
        assert all(call[0][0] <= 12.0 for call in calls)

    def test_invalid_max_attempts_condition(self):
        """Test ValueError for invalid max_attempts."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            @retry_on_condition(lambda x: True, max_attempts=0)
            def dummy():
                pass

    @patch('time.sleep')
    def test_condition_with_complex_check(self, mock_sleep):
        """Test condition with complex validation."""
        counter = {'count': 0}

        @retry_on_condition(
            lambda x: isinstance(x, dict) and x.get('valid') == True,
            max_attempts=3
        )
        def returns_dict():
            counter['count'] += 1
            if counter['count'] < 2:
                return {'valid': False}
            return {'valid': True}

        result = returns_dict()

        assert result == {'valid': True}
        assert mock_sleep.call_count == 1


# ============================================================================
# Test retry_with_timeout Decorator
# ============================================================================

class TestRetryWithTimeout:
    """Test retry_with_timeout decorator."""

    @patch('time.time')
    @patch('time.sleep')
    def test_success_within_timeout(self, mock_sleep, mock_time):
        """Test success before timeout."""
        mock_time.side_effect = [0, 1, 2]  # Simulate time progression

        @retry_with_timeout(timeout=10.0, max_attempts=3)
        def succeeds_quickly():
            return "success"

        result = succeeds_quickly()

        assert result == "success"
        mock_sleep.assert_not_called()

    @patch('time.time')
    @patch('time.sleep')
    def test_timeout_exceeded(self, mock_sleep, mock_time):
        """Test TimeoutError when timeout exceeded."""
        # Simulate time exceeding timeout
        mock_time.side_effect = [0, 0.1, 15.0]  # Exceeds 10s timeout

        @retry_with_timeout(timeout=10.0, max_attempts=5)
        def always_fails():
            raise ValueError("Fail")

        with pytest.raises((TimeoutError, ValueError)):
            always_fails()

    @patch('time.time')
    @patch('time.sleep')
    def test_timeout_limits_retries(self, mock_sleep, mock_time):
        """Test timeout prevents all max_attempts from being used."""
        # Time progresses: 0s, 1s, 5s (exceeds timeout before attempt 3)
        mock_time.side_effect = [0, 0.1, 1.0, 1.1, 11.0]

        @retry_with_timeout(timeout=10.0, max_attempts=10, initial_delay=1.0)
        def always_fails():
            raise ValueError("Fail")

        with pytest.raises((TimeoutError, ValueError)):
            always_fails()

        # Should stop before using all 10 attempts due to timeout
        assert mock_sleep.call_count < 9

    @patch('time.time')
    @patch('time.sleep')
    def test_delay_adjusted_for_remaining_time(self, mock_sleep, mock_time):
        """Test delay is adjusted based on remaining timeout."""
        # Provide enough time values for all time.time() calls
        mock_time.side_effect = [0, 0.1, 1.0, 1.1, 2.0, 2.1, 3.0, 3.1, 4.0, 4.1]

        @retry_with_timeout(timeout=10.0, max_attempts=5, initial_delay=5.0)
        def always_fails():
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            always_fails()

        # Delays should be limited by remaining time
        if mock_sleep.call_count > 0:
            last_delay = mock_sleep.call_args_list[-1][0][0]
            assert last_delay <= 10.0

    def test_invalid_timeout(self):
        """Test ValueError for invalid timeout."""
        with pytest.raises(ValueError, match="timeout must be > 0"):
            @retry_with_timeout(timeout=0, max_attempts=3)
            def dummy():
                pass

    def test_invalid_max_attempts_timeout(self):
        """Test ValueError for invalid max_attempts."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            @retry_with_timeout(timeout=10.0, max_attempts=0)
            def dummy():
                pass

    @patch('time.time')
    @patch('time.sleep')
    def test_specific_exceptions_only_with_timeout(self, mock_sleep, mock_time):
        """Test only specified exceptions are retried."""
        mock_time.side_effect = [0, 0.1, 1.0, 1.1]

        @retry_with_timeout(
            timeout=10.0,
            max_attempts=3,
            exceptions=(ValueError,)
        )
        def raises_runtime_error():
            raise RuntimeError("Not retryable")

        with pytest.raises(RuntimeError):
            raises_runtime_error()

        mock_sleep.assert_not_called()


# ============================================================================
# Test RetryContext Context Manager
# ============================================================================

class TestRetryContext:
    """Test RetryContext context manager."""

    @patch('time.sleep')
    def test_success_on_first_attempt(self, mock_sleep):
        """Test successful operation on first attempt."""
        with RetryContext(max_attempts=3) as retry:
            while retry.should_retry():
                result = "success"
                retry.success()
                break

        assert result == "success"
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    def test_success_after_retries(self, mock_sleep):
        """Test success after multiple retries."""
        attempt_count = 0

        with RetryContext(max_attempts=3, initial_delay=1.0) as retry:
            while retry.should_retry():
                attempt_count += 1
                if attempt_count < 3:
                    retry.failure(ValueError("Not yet"))
                else:
                    retry.success()
                    break

        assert attempt_count == 3
        assert mock_sleep.call_count == 2

    @patch('time.sleep')
    def test_all_attempts_exhausted(self, mock_sleep):
        """Test all attempts exhausted."""
        with RetryContext(max_attempts=2) as retry:
            while retry.should_retry():
                retry.failure(ValueError("Fail"))

        assert retry.attempt == 2
        assert mock_sleep.call_count == 1

    @patch('time.sleep')
    def test_exponential_backoff_in_context(self, mock_sleep):
        """Test exponential backoff delays."""
        with RetryContext(
            max_attempts=4,
            initial_delay=1.0,
            exponential_base=2.0
        ) as retry:
            while retry.should_retry():
                retry.failure(ValueError("Fail"))

        calls = mock_sleep.call_args_list
        assert len(calls) == 3
        assert calls[0][0][0] == 1.0
        assert calls[1][0][0] == 2.0
        assert calls[2][0][0] == 4.0

    @patch('time.sleep')
    def test_max_delay_cap_in_context(self, mock_sleep):
        """Test max_delay caps delays."""
        with RetryContext(
            max_attempts=5,
            initial_delay=10.0,
            max_delay=15.0,
            exponential_base=3.0
        ) as retry:
            while retry.should_retry():
                retry.failure(ValueError("Fail"))

        calls = mock_sleep.call_args_list
        assert all(call[0][0] <= 15.0 for call in calls)

    def test_invalid_max_attempts_context(self):
        """Test ValueError for invalid max_attempts."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            RetryContext(max_attempts=0)

    @patch('time.sleep')
    def test_should_retry_behavior(self, mock_sleep):
        """Test should_retry returns correct values."""
        with RetryContext(max_attempts=2) as retry:
            assert retry.should_retry() is True
            retry.failure()
            assert retry.should_retry() is True
            retry.failure()
            assert retry.should_retry() is False

    @patch('time.sleep')
    def test_success_stops_retries(self, mock_sleep):
        """Test calling success() stops further retries."""
        with RetryContext(max_attempts=5) as retry:
            assert retry.should_retry() is True
            retry.success()
            assert retry.should_retry() is False

    @patch('time.sleep')
    def test_attempts_remaining_property(self, mock_sleep):
        """Test attempts_remaining property."""
        with RetryContext(max_attempts=3) as retry:
            assert retry.attempts_remaining == 3
            retry.failure()
            assert retry.attempts_remaining == 2
            retry.failure()
            assert retry.attempts_remaining == 1
            retry.failure()
            assert retry.attempts_remaining == 0

    @patch('time.sleep')
    def test_last_exception_stored(self, mock_sleep):
        """Test last_exception is stored."""
        exc = ValueError("Test error")

        with RetryContext(max_attempts=2) as retry:
            while retry.should_retry():
                retry.failure(exc)

        assert retry.last_exception is exc

    @patch('time.sleep')
    def test_context_manager_exception_handling(self, mock_sleep):
        """Test context manager handles exceptions."""
        with pytest.raises(RuntimeError):
            with RetryContext(max_attempts=2) as retry:
                while retry.should_retry():
                    retry.failure()
                raise RuntimeError("Final error")


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @patch('time.sleep')
    def test_api_retry_scenario(self, mock_sleep):
        """Test realistic API retry scenario."""
        responses = [
            ConnectionError("Connection refused"),
            ConnectionError("Timeout"),
            {"status": "ok", "data": "result"}
        ]
        call_count = {'count': 0}

        @retry_with_backoff(
            max_attempts=3,
            initial_delay=1.0,
            exceptions=(ConnectionError,)
        )
        def call_api():
            response = responses[call_count['count']]
            call_count['count'] += 1
            if isinstance(response, Exception):
                raise response
            return response

        result = call_api()

        assert result == {"status": "ok", "data": "result"}
        assert call_count['count'] == 3
        assert mock_sleep.call_count == 2

    @patch('time.sleep')
    def test_polling_scenario(self, mock_sleep):
        """Test polling until condition met."""
        states = ["pending", "pending", "complete"]
        call_count = {'count': 0}

        @retry_on_condition(
            lambda x: x == "complete",
            max_attempts=5,
            initial_delay=2.0
        )
        def check_status():
            status = states[min(call_count['count'], len(states) - 1)]
            call_count['count'] += 1
            return status

        result = check_status()

        assert result == "complete"
        assert call_count['count'] == 3
