"""Retry decorators with exponential backoff.

This module provides decorators and utilities for retrying failed operations
with configurable backoff strategies. Uses only Python standard library.

Example:
    >>> from retry import retry_with_backoff, RetryContext
    >>> @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    ... def fetch_data():
    ...     return api.get("/data")
"""

import time
import logging
import functools
from typing import Callable, Tuple, Type, Optional, Any


logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    log_level: int = logging.WARNING
):
    """Decorator to retry a function with exponential backoff.
    
    Implements exponential backoff with configurable parameters.
    Delay formula: min(initial_delay * (exponential_base ** attempt), max_delay)
    
    Args:
        max_attempts: Maximum number of attempts (including initial attempt)
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential backoff (default: 2.0)
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called before each retry
                 Signature: on_retry(attempt: int, exception: Exception, delay: float)
        log_level: Logging level for retry messages (default: WARNING)
        
    Returns:
        Decorated function that retries on failure
        
    Example:
        >>> @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        ... def fetch_data(url):
        ...     # This will retry up to 3 times with delays: 0s, 1s, 2s
        ...     return requests.get(url)
        
        >>> @retry_with_backoff(
        ...     max_attempts=5,
        ...     initial_delay=0.5,
        ...     max_delay=10.0,
        ...     exceptions=(ConnectionError, TimeoutError)
        ... )
        ... def connect_to_database():
        ...     # Only retries on ConnectionError or TimeoutError
        ...     return db.connect()
        
    Backoff Schedule Examples:
        initial_delay=1.0, exponential_base=2.0:
        - Attempt 1: immediate
        - Attempt 2: wait 1.0s (1.0 * 2^0)
        - Attempt 3: wait 2.0s (1.0 * 2^1)
        - Attempt 4: wait 4.0s (1.0 * 2^2)
        - Attempt 5: wait 8.0s (1.0 * 2^3)
        
        initial_delay=0.5, exponential_base=3.0, max_delay=5.0:
        - Attempt 1: immediate
        - Attempt 2: wait 0.5s (0.5 * 3^0)
        - Attempt 3: wait 1.5s (0.5 * 3^1)
        - Attempt 4: wait 4.5s (0.5 * 3^2)
        - Attempt 5: wait 5.0s (capped at max_delay)
    """
    # Validate max_attempts
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    # Attempt the function
                    result = func(*args, **kwargs)
                    
                    # Log success if we had previous failures
                    if attempt > 0:
                        logger.log(
                            log_level,
                            f"✓ {func.__name__} succeeded on attempt {attempt + 1}/{max_attempts}"
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # If this was the last attempt, re-raise
                    if attempt == max_attempts - 1:
                        logger.log(
                            log_level,
                            f"✗ {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay for next attempt
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Log the retry
                    logger.log(
                        log_level,
                        f"⚠ {func.__name__} failed on attempt {attempt + 1}/{max_attempts}, "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e, delay)
                        except Exception as callback_error:
                            logger.warning(f"on_retry callback failed: {callback_error}")
                    
                    # Wait before retry
                    time.sleep(delay)
            
            # Should never reach here due to raise in last attempt, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} exhausted all retry attempts")
        
        return wrapper
    return decorator


def retry_on_condition(
    condition: Callable[[Any], bool],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
):
    """Decorator to retry a function based on return value condition.
    
    Unlike retry_with_backoff which retries on exceptions, this retries
    when the return value doesn't meet a condition.
    
    Args:
        condition: Function that takes the return value and returns True if acceptable
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exponential_base: Base for exponential backoff
        
    Returns:
        Decorated function that retries based on condition
        
    Example:
        >>> @retry_on_condition(lambda x: x is not None, max_attempts=3)
        ... def get_value():
        ...     # Retries until non-None value returned
        ...     return fetch_from_cache()
        
        >>> @retry_on_condition(lambda x: len(x) > 0, max_attempts=5)
        ... def get_results():
        ...     # Retries until non-empty list returned
        ...     return query_database()
    """
    # Validate max_attempts
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = None
            
            for attempt in range(max_attempts):
                result = func(*args, **kwargs)
                
                # Check condition
                if condition(result):
                    if attempt > 0:
                        logger.debug(
                            f"✓ {func.__name__} satisfied condition on attempt {attempt + 1}"
                        )
                    return result
                
                # If last attempt, return anyway
                if attempt == max_attempts - 1:
                    logger.warning(
                        f"⚠ {func.__name__} failed condition after {max_attempts} attempts"
                    )
                    return result
                
                # Calculate delay
                delay = min(
                    initial_delay * (exponential_base ** attempt),
                    max_delay
                )
                
                logger.debug(
                    f"⚠ {func.__name__} failed condition on attempt {attempt + 1}, "
                    f"retrying in {delay:.2f}s"
                )
                
                time.sleep(delay)
            
            return result
        
        return wrapper
    return decorator


def retry_with_timeout(
    timeout: float,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator to retry a function with a total timeout.
    
    Combines retry logic with an overall timeout. Stops retrying if total
    elapsed time exceeds timeout, even if attempts remain.
    
    Args:
        timeout: Total timeout in seconds
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries
        exceptions: Exceptions to catch and retry
        
    Returns:
        Decorated function with timeout and retry
        
    Example:
        >>> @retry_with_timeout(timeout=10.0, max_attempts=5)
        ... def slow_operation():
        ...     # Will retry for at most 10 seconds total
        ...     return expensive_call()
    """
    # Validate parameters
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    if timeout <= 0:
        raise ValueError(f"timeout must be > 0, got {timeout}")
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            last_exception = None
            
            for attempt in range(max_attempts):
                # Check if we've exceeded timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(
                        f"⏱ {func.__name__} exceeded timeout ({timeout}s) "
                        f"after {attempt} attempts"
                    )
                    if last_exception:
                        raise last_exception
                    raise TimeoutError(
                        f"{func.__name__} exceeded timeout of {timeout}s"
                    )
                
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        raise
                    
                    # Calculate remaining time and delay
                    remaining = timeout - (time.time() - start_time)
                    delay = min(initial_delay * (2 ** attempt), remaining)
                    
                    if delay <= 0:
                        raise
                    
                    logger.debug(
                        f"⚠ {func.__name__} failed, retrying in {delay:.2f}s "
                        f"(timeout remaining: {remaining:.2f}s)"
                    )
                    
                    time.sleep(delay)
            
            # Should never reach here due to raise in last attempt
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} exhausted all retry attempts")
        
        return wrapper
    return decorator


class RetryContext:
    """Context manager for retry logic with manual control.
    
    Useful when you need more control over retry logic than decorators provide.
    
    Example:
        >>> with RetryContext(max_attempts=3, initial_delay=1.0) as retry:
        ...     while retry.should_retry():
        ...         try:
        ...             result = risky_operation()
        ...             retry.success()
        ...             break
        ...         except Exception as e:
        ...             retry.failure(e)
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        """Initialize retry context.
        
        Args:
            max_attempts: Maximum retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay cap
            exponential_base: Backoff multiplier
            
        Raises:
            ValueError: If max_attempts < 1
        """
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        
        self.attempt = 0
        self.last_exception = None
        self._succeeded = False
    
    def __enter__(self):
        """Enter context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context, re-raise exception if all attempts exhausted."""
        if exc_val and not self._succeeded:
            return False  # Re-raise exception
        return True  # Suppress exception
    
    def should_retry(self) -> bool:
        """Check if another retry attempt should be made.
        
        Returns:
            True if more attempts remain, False otherwise
        """
        return self.attempt < self.max_attempts and not self._succeeded
    
    def failure(self, exception: Exception = None):
        """Record a failed attempt.
        
        Args:
            exception: Exception that caused the failure
        """
        self.last_exception = exception
        self.attempt += 1
        
        if self.attempt < self.max_attempts:
            delay = min(
                self.initial_delay * (self.exponential_base ** (self.attempt - 1)),
                self.max_delay
            )
            logger.debug(
                f"Retry attempt {self.attempt}/{self.max_attempts} failed, "
                f"waiting {delay:.2f}s"
            )
            time.sleep(delay)
    
    def success(self):
        """Record a successful attempt."""
        self._succeeded = True
    
    @property
    def attempts_remaining(self) -> int:
        """Get number of attempts remaining.
        
        Returns:
            Number of remaining attempts
        """
        return max(0, self.max_attempts - self.attempt)
