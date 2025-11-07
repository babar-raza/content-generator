# resilience.py
"""Resilience patterns for services.

Implements CircuitBreaker, Retry with exponential backoff, ResourcePool, and Saga pattern."""

from typing import Callable, Any, Optional, Dict, List
from enum import Enum
from datetime import datetime, timezone, timedelta
import random
import logging
import threading
import time
from dataclasses import dataclass, field
from src.core.config import Config

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_attempts: int = 3
    ):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            timeout: Seconds before attempting half-open
            half_open_attempts: Attempts in half-open before closing"""
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails"""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if (self.last_failure_time and
                    datetime.now(timezone.utc) - self.last_failure_time > timedelta(seconds=self.timeout)):
                    logger.info(f"Circuit {self.name}: Transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise Exception(f"Circuit {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful execution."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_attempts:
                    logger.info(f"Circuit {self.name}: Transitioning to CLOSED")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)

    def _on_failure(self):
        """Handle failed execution."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit {self.name}: Transitioning to OPEN (half-open failed)")
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                logger.warning(f"Circuit {self.name}: Transitioning to OPEN")
                self.state = CircuitState.OPEN

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state.

        Returns:
            State dictionary"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }

class RetryPolicy:
    """Retry with exponential backoff and jitter."""

    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """Initialize retry policy.

        Args:
            max_attempts: Maximum number of attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter"""
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all attempts fail"""
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt == self.max_attempts:
                    logger.error(f"All {self.max_attempts} attempts failed")
                    raise

                delay = min(
                    self.base_delay * (self.exponential_base ** (attempt - 1)),
                    self.max_delay
                )

                if self.jitter:
                    delay = delay * (0.5 + random.random())

                logger.warning(
                    f"Attempt {attempt}/{self.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                time.sleep(delay)

        raise last_exception

class ResourcePool:
    """Resource pool with semaphore-based concurrency control."""

    def __init__(self, name: str, max_concurrent: int):
        """Initialize resource pool.

        Args:
            name: Pool name
            max_concurrent: Maximum concurrent operations"""
        self.name = name
        self.max_concurrent = max_concurrent
        self.semaphore = threading.Semaphore(max_concurrent)
        self.active_count = 0
        self._lock = threading.Lock()

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire resource from pool.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if acquired"""
        acquired = self.semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self.active_count += 1
        return acquired

    def release(self):
        """Release resource back to pool."""
        with self._lock:
            self.active_count = max(0, self.active_count - 1)
        self.semaphore.release()

    def __enter__(self):
        """Context manager entry."""
        if not self.acquire(timeout=30):
            raise TimeoutError(f"Failed to acquire resource from {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.

        Returns:
            Statistics dictionary"""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active_count": self.active_count,
            "available": self.max_concurrent - self.active_count
        }

@dataclass
class SagaStep:
    """A step in a saga."""
    name: str
    action: Callable
    compensation: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    result: Any = None

class Saga:
    """Saga pattern for distributed transactions."""

    def __init__(self, name: str):
        """Initialize saga.

        Args:
            name: Saga name"""
        self.name = name
        self.steps: List[SagaStep] = []
        self.completed_steps: List[SagaStep] = []

    def add_step(
        self,
        name: str,
        action: Callable,
        compensation: Optional[Callable] = None,
        *args,
        **kwargs
    ):
        """Add a step to the saga.

        Args:
            name: Step name
            action: Action function
            compensation: Compensation function (for rollback)
            *args: Action arguments
            **kwargs: Action keyword arguments"""
        step = SagaStep(
            name=name,
            action=action,
            compensation=compensation,
            args=args,
            kwargs=kwargs
        )
        self.steps.append(step)

    def execute(self) -> Dict[str, Any]:
        """Execute saga steps.

        Returns:
            Results from all steps

        Raises:
            Exception: If saga fails and compensation succeeds"""
        results = {}

        try:
            for step in self.steps:
                logger.info(f"Saga {self.name}: Executing step {step.name}")

                try:
                    result = step.action(*step.args, **step.kwargs)
                    step.result = result
                    results[step.name] = result
                    self.completed_steps.append(step)

                except Exception as e:
                    logger.error(f"Saga {self.name}: Step {step.name} failed: {e}")
                    self._compensate()
                    raise

            logger.info(f"Saga {self.name}: Completed successfully")
            return results

        except Exception as e:
            logger.error(f"Saga {self.name}: Failed with error: {e}")
            raise

    def _compensate(self):
        """Execute compensation actions for completed steps."""
        logger.warning(f"Saga {self.name}: Starting compensation")

        for step in reversed(self.completed_steps):
            if step.compensation:
                try:
                    logger.info(f"Saga {self.name}: Compensating step {step.name}")
                    step.compensation(step.result)
                except Exception as e:
                    logger.error(
                        f"Saga {self.name}: Compensation failed for step {step.name}: {e}"
                    )

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate_per_minute: int):
        """Initialize rate limiter.

        Args:
            rate_per_minute: Maximum requests per minute"""
        self.rate_per_minute = rate_per_minute
        self.tokens = rate_per_minute
        self.last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait for tokens

        Returns:
            True if tokens acquired"""
        start_time = time.time()

        while True:
            with self._lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            time.sleep(0.1)

    def _refill(self):
        """Refill token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        tokens_to_add = (elapsed / 60.0) * self.rate_per_minute
        self.tokens = min(self.rate_per_minute, self.tokens + tokens_to_add)
        self.last_update = now

class ResilienceManager:
    """Manager for all resilience patterns."""

    def __init__(self, config: Config):
        """Initialize resilience manager.

        Args:
            config: Configuration instance"""
        self.config = config

        self.circuit_breakers = {
            "llm": CircuitBreaker(
                "LLM",
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout=config.circuit_breaker_timeout
            ),
            "gemini": CircuitBreaker(
                "Gemini",
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout=config.circuit_breaker_timeout
            ),
            "vector_db": CircuitBreaker(
                "VectorDB",
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout=config.circuit_breaker_timeout
            ),
            "gist": CircuitBreaker(
                "Gist",
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout=config.circuit_breaker_timeout
            ),
            "trends": CircuitBreaker(
                "Trends",
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout=config.circuit_breaker_timeout
            ),
            "content_generation": CircuitBreaker(
                "ContentGeneration",
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout=config.circuit_breaker_timeout
            ),
            "supplementary_generation": CircuitBreaker(
                "SupplementaryGeneration",
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout=config.circuit_breaker_timeout
            ),
        }

        self.resource_pools = {
            "ollama": ResourcePool("Ollama", config.ollama_concurrency),
            "gemini": ResourcePool("Gemini", config.gemini_concurrency),
            "gist": ResourcePool("Gist", config.gist_concurrency),
            "trends": ResourcePool("Trends", config.trends_concurrency),
            "content_agents": ResourcePool("ContentAgents", 3),  # Allow 3 concurrent content generation tasks
        }

        self.rate_limiters = {
            "gemini": RateLimiter(config.gemini_rpm_limit),
            "trends": RateLimiter(config.trends_rpm_limit),
        }

        self.retry_policy = RetryPolicy(
            max_attempts=config.retry_max_attempts,
            base_delay=config.retry_base_delay,
            max_delay=config.retry_max_delay
        )

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get circuit breaker by name with auto-recovery check."""
        cb = self.circuit_breakers.get(name)

        if cb and cb.state == CircuitState.OPEN:
            if cb.last_failure_time:
                # CRITICAL: Ensure both datetimes are timezone-aware for comparison
                now = datetime.now(timezone.utc)
                last_failure = cb.last_failure_time

                # Make last_failure timezone-aware if it isn't
                if last_failure.tzinfo is None:
                    last_failure = last_failure.replace(tzinfo=timezone.utc)

                elapsed = (now - last_failure).total_seconds()

                # Force transition after 2x timeout
                if elapsed > (cb.timeout * 2):
                    logger.warning(f"Force-transitioning circuit {name} to HALF_OPEN after {elapsed:.0f}s")
                    cb.state = CircuitState.HALF_OPEN
                    cb.success_count = 0
                    cb.failure_count = 0  # RESET failures too

        return cb

    def get_resource_pool(self, name: str) -> ResourcePool:
        """Get resource pool by name."""
        return self.resource_pools.get(name)

    def get_rate_limiter(self, name: str) -> RateLimiter:
        """Get rate limiter by name."""
        return self.rate_limiters.get(name)

    def get_health_report(self) -> Dict[str, Any]:
        """Get health report for all resilience components."""
        return {
            "circuit_breakers": {
                name: cb.get_state()
                for name, cb in self.circuit_breakers.items()
            },
            "resource_pools": {
                name: pool.get_stats()
                for name, pool in self.resource_pools.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Unit tests
if __name__ == "__main__":
    import unittest

    class TestCircuitBreaker(unittest.TestCase):
        def setUp(self):
            self.cb = CircuitBreaker("test", failure_threshold=3, timeout=1.0)

        def test_circuit_opens_after_failures(self):
            def failing_func():
                raise Exception("Test failure")

            for _ in range(3):
                try:
                    self.cb.call(failing_func)
                except Exception:
                    pass

            self.assertEqual(self.cb.state, CircuitState.OPEN)

            with self.assertRaises(Exception):
                self.cb.call(lambda: "success")

    class TestRetryPolicy(unittest.TestCase):
        def setUp(self):
            self.policy = RetryPolicy(max_attempts=3, base_delay=0.1)

        def test_retry_succeeds_eventually(self):
            self.attempt = 0

            def flaky_func():
                self.attempt += 1
                if self.attempt < 3:
                    raise Exception("Not yet")
                return "success"

            result = self.policy.execute(flaky_func)
            self.assertEqual(result, "success")
            self.assertEqual(self.attempt, 3)

    class TestSaga(unittest.TestCase):
        def test_saga_compensation(self):
            saga = Saga("test_saga")

            self.compensated = []

            def step1():
                return "step1_result"

            def compensate1(result):
                self.compensated.append("step1")

            def step2():
                raise Exception("Step 2 failed")

            saga.add_step("step1", step1, compensate1)
            saga.add_step("step2", step2)

            with self.assertRaises(Exception):
                saga.execute()

            self.assertIn("step1", self.compensated)

    unittest.main()
