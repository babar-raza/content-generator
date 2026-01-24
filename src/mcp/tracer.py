"""MCP Tracer - Observability for MCP message flow.

This module provides the MCPTracer class for tracing MCP protocol messages,
recording request/response pairs with timing information, and supporting
event subscriptions for real-time monitoring.
"""

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import RLock
from typing import Callable, Optional

from .protocol import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


@dataclass
class MCPTrace:
    """A trace record for an MCP request/response pair.

    Attributes:
        trace_id: Unique identifier for this trace
        request: The MCPRequest that was received
        response: The MCPResponse that was sent (None if not yet received)
        request_time: When the request was received
        response_time: When the response was sent (None if not yet received)
        duration_ms: Duration in milliseconds (None if not yet completed)
        method: The method name from the request
        status: Status of the trace (pending, completed, error)
    """

    trace_id: str
    request: MCPRequest
    response: Optional[MCPResponse] = None
    request_time: datetime = field(default_factory=datetime.now)
    response_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    method: str = field(init=False)
    status: str = field(default="pending")

    def __post_init__(self):
        """Initialize computed fields."""
        self.method = self.request.method
        if self.response and self.response_time:
            self._calculate_duration()
            self._update_status()

    def _calculate_duration(self) -> None:
        """Calculate duration in milliseconds."""
        if self.response_time:
            delta = self.response_time - self.request_time
            self.duration_ms = delta.total_seconds() * 1000

    def _update_status(self) -> None:
        """Update status based on response."""
        if self.response is None:
            self.status = "pending"
        elif self.response.error:
            self.status = "error"
        else:
            self.status = "completed"

    def complete(self, response: MCPResponse) -> None:
        """Complete the trace with a response.

        Args:
            response: The MCPResponse to record
        """
        self.response = response
        self.response_time = datetime.now()
        self._calculate_duration()
        self._update_status()

    def to_dict(self) -> dict:
        """Convert trace to dictionary.

        Returns:
            Dictionary representation of the trace
        """
        return {
            "trace_id": self.trace_id,
            "request": self.request.to_dict(),
            "response": self.response.to_dict() if self.response else None,
            "request_time": self.request_time.isoformat(),
            "response_time": self.response_time.isoformat() if self.response_time else None,
            "duration_ms": self.duration_ms,
            "method": self.method,
            "status": self.status,
        }


class MCPTracer:
    """Tracer for MCP requests and responses.

    The MCPTracer provides observability for all MCP message flow by:
    - Recording all requests with unique trace IDs
    - Pairing responses with their requests
    - Calculating request/response durations
    - Supporting filtering and querying of traces
    - Providing event subscriptions for real-time monitoring

    Thread Safety:
        This class is thread-safe for concurrent access.

    Example:
        >>> tracer = MCPTracer(max_traces=1000, retention_hours=24)
        >>> request = MCPRequest(method="agent.invoke", params={"name": "test"})
        >>> trace_id = tracer.trace_request(request)
        >>> # ... process request ...
        >>> response = MCPResponse.success({"result": "ok"}, request.id)
        >>> tracer.trace_response(trace_id, response)
        >>> trace = tracer.get_trace(trace_id)
        >>> print(f"Duration: {trace.duration_ms}ms")
    """

    def __init__(
        self,
        max_traces: int = 10000,
        retention_hours: Optional[int] = None,
        persistence_hook: Optional[Callable[[MCPTrace], None]] = None,
    ):
        """Initialize the tracer.

        Args:
            max_traces: Maximum number of traces to store in memory (default: 10000)
            retention_hours: Optional retention period in hours (None = unlimited)
            persistence_hook: Optional callback for persisting completed traces
        """
        self._max_traces = max_traces
        self._retention_hours = retention_hours
        self._persistence_hook = persistence_hook
        self._traces: dict[str, MCPTrace] = {}
        self._trace_order: deque[str] = deque(maxlen=max_traces)
        self._subscriptions: dict[str, Callable[[MCPTrace], None]] = {}
        self._lock = RLock()
        logger.info(
            f"MCPTracer initialized (max_traces={max_traces}, "
            f"retention_hours={retention_hours})"
        )

    def trace_request(self, request: MCPRequest) -> str:
        """Record an incoming request and return a trace ID.

        Args:
            request: The MCPRequest to trace

        Returns:
            Unique trace ID for this request

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> tracer = MCPTracer()
            >>> request = MCPRequest(method="agent.invoke", params={"name": "test"})
            >>> trace_id = tracer.trace_request(request)
            >>> assert trace_id is not None
        """
        if request is None:
            logger.warning("Attempted to trace None request")
            return ""

        trace_id = str(uuid.uuid4())
        trace = MCPTrace(trace_id=trace_id, request=request)

        with self._lock:
            # Enforce max traces limit
            if len(self._traces) >= self._max_traces:
                self._evict_oldest_trace()

            self._traces[trace_id] = trace
            self._trace_order.append(trace_id)

        logger.debug(f"Traced request {trace_id}: {request.method}")
        return trace_id

    def trace_response(self, trace_id: str, response: MCPResponse) -> None:
        """Record a response for a traced request.

        Args:
            trace_id: The trace ID from trace_request()
            response: The MCPResponse to record

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> tracer = MCPTracer()
            >>> request = MCPRequest(method="test", params={})
            >>> trace_id = tracer.trace_request(request)
            >>> response = MCPResponse.success({"result": "ok"}, request.id)
            >>> tracer.trace_response(trace_id, response)
            >>> trace = tracer.get_trace(trace_id)
            >>> assert trace.response is not None
        """
        if response is None:
            logger.warning(f"Attempted to trace None response for {trace_id}")
            return

        with self._lock:
            trace = self._traces.get(trace_id)
            if not trace:
                logger.warning(f"Trace {trace_id} not found for response")
                return

            trace.complete(response)

        logger.debug(
            f"Traced response for {trace_id}: {trace.method} "
            f"({trace.duration_ms:.2f}ms, status={trace.status})"
        )

        # Notify subscribers
        self._notify_subscribers(trace)

        # Persist if hook provided
        if self._persistence_hook:
            try:
                self._persistence_hook(trace)
            except Exception as e:
                logger.error(f"Persistence hook failed for {trace_id}: {e}")

    def get_trace(self, trace_id: str) -> Optional[MCPTrace]:
        """Retrieve a trace by ID.

        Args:
            trace_id: The trace ID to retrieve

        Returns:
            MCPTrace if found, None otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> tracer = MCPTracer()
            >>> request = MCPRequest(method="test", params={})
            >>> trace_id = tracer.trace_request(request)
            >>> trace = tracer.get_trace(trace_id)
            >>> assert trace is not None
            >>> assert trace.trace_id == trace_id
        """
        with self._lock:
            return self._traces.get(trace_id)

    def list_traces(
        self,
        method: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[MCPTrace]:
        """List traces with optional filtering.

        Args:
            method: Optional method name filter
            since: Optional datetime filter (only traces after this time)
            limit: Maximum number of traces to return (default: 100)

        Returns:
            List of MCPTrace objects matching the filters, newest first

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> tracer = MCPTracer()
            >>> request1 = MCPRequest(method="agent.invoke", params={})
            >>> request2 = MCPRequest(method="tool.list", params={})
            >>> tracer.trace_request(request1)
            >>> tracer.trace_request(request2)
            >>> traces = tracer.list_traces(method="agent.invoke")
            >>> assert len(traces) == 1
            >>> assert traces[0].method == "agent.invoke"
        """
        with self._lock:
            # Clean up expired traces first
            if self._retention_hours:
                self._cleanup_expired_traces()

            # Get all traces in reverse order (newest first)
            traces = [
                self._traces[tid]
                for tid in reversed(self._trace_order)
                if tid in self._traces
            ]

            # Apply filters
            if method:
                traces = [t for t in traces if t.method == method]

            if since:
                traces = [t for t in traces if t.request_time >= since]

            # Apply limit
            return traces[:limit]

    def subscribe(self, callback: Callable[[MCPTrace], None]) -> str:
        """Subscribe to trace events.

        The callback will be invoked when a trace is completed (i.e., when
        trace_response() is called). This is used by Visual Orchestration
        for real-time execution visibility.

        Args:
            callback: Function to call with completed traces

        Returns:
            Subscription ID for unsubscribing

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> tracer = MCPTracer()
            >>> def on_trace(trace: MCPTrace):
            ...     print(f"Completed: {trace.method} in {trace.duration_ms}ms")
            >>> sub_id = tracer.subscribe(on_trace)
            >>> # ... traces will now be sent to callback ...
            >>> tracer.unsubscribe(sub_id)
        """
        if callback is None:
            logger.warning("Attempted to subscribe with None callback")
            return ""

        subscription_id = str(uuid.uuid4())

        with self._lock:
            self._subscriptions[subscription_id] = callback

        logger.info(f"Subscription {subscription_id} created")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a trace subscription.

        Args:
            subscription_id: The subscription ID from subscribe()

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> tracer = MCPTracer()
            >>> sub_id = tracer.subscribe(lambda t: None)
            >>> tracer.unsubscribe(sub_id)
        """
        with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                logger.info(f"Subscription {subscription_id} removed")
            else:
                logger.warning(f"Subscription {subscription_id} not found")

    def get_stats(self) -> dict:
        """Get tracer statistics.

        Returns:
            Dictionary with tracer statistics

        Example:
            >>> tracer = MCPTracer()
            >>> stats = tracer.get_stats()
            >>> assert "total_traces" in stats
            >>> assert "subscriptions" in stats
        """
        with self._lock:
            total = len(self._traces)
            pending = sum(1 for t in self._traces.values() if t.status == "pending")
            completed = sum(1 for t in self._traces.values() if t.status == "completed")
            errors = sum(1 for t in self._traces.values() if t.status == "error")

            return {
                "total_traces": total,
                "pending": pending,
                "completed": completed,
                "errors": errors,
                "subscriptions": len(self._subscriptions),
                "max_traces": self._max_traces,
                "retention_hours": self._retention_hours,
            }

    def clear_traces(self) -> None:
        """Clear all traces from memory.

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> tracer = MCPTracer()
            >>> request = MCPRequest(method="test", params={})
            >>> tracer.trace_request(request)
            >>> tracer.clear_traces()
            >>> assert len(tracer.list_traces()) == 0
        """
        with self._lock:
            self._traces.clear()
            self._trace_order.clear()
        logger.info("All traces cleared")

    def _notify_subscribers(self, trace: MCPTrace) -> None:
        """Notify all subscribers of a completed trace.

        Args:
            trace: The completed trace
        """
        with self._lock:
            subscribers = list(self._subscriptions.values())

        # Call subscribers outside the lock to avoid deadlocks
        for callback in subscribers:
            try:
                callback(trace)
            except Exception as e:
                logger.error(f"Subscriber callback failed: {e}")

    def _evict_oldest_trace(self) -> None:
        """Evict the oldest trace to make room for a new one.

        Must be called while holding self._lock.
        """
        if self._trace_order:
            oldest_id = self._trace_order.popleft()
            if oldest_id in self._traces:
                del self._traces[oldest_id]
                logger.debug(f"Evicted oldest trace {oldest_id}")

    def _cleanup_expired_traces(self) -> None:
        """Remove traces older than the retention period.

        Must be called while holding self._lock.
        """
        if not self._retention_hours:
            return

        cutoff_time = datetime.now() - timedelta(hours=self._retention_hours)
        expired_ids = [
            tid
            for tid, trace in self._traces.items()
            if trace.request_time < cutoff_time
        ]

        for tid in expired_ids:
            del self._traces[tid]
            # Note: We don't remove from _trace_order as it has maxlen and will
            # naturally drop old entries

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired traces")


# Global tracer instance (optional singleton pattern)
_global_tracer: Optional[MCPTracer] = None
_global_tracer_lock = RLock()


def get_global_tracer() -> MCPTracer:
    """Get the global tracer instance, creating it if needed.

    Returns:
        Global MCPTracer instance

    Thread Safety:
        This function is thread-safe.

    Example:
        >>> tracer1 = get_global_tracer()
        >>> tracer2 = get_global_tracer()
        >>> assert tracer1 is tracer2
    """
    global _global_tracer
    with _global_tracer_lock:
        if _global_tracer is None:
            _global_tracer = MCPTracer()
        return _global_tracer


def reset_global_tracer() -> None:
    """Reset the global tracer instance.

    Thread Safety:
        This function is thread-safe.

    Example:
        >>> tracer1 = get_global_tracer()
        >>> reset_global_tracer()
        >>> tracer2 = get_global_tracer()
        >>> assert tracer1 is not tracer2
    """
    global _global_tracer
    with _global_tracer_lock:
        _global_tracer = None


__all__ = [
    "MCPTrace",
    "MCPTracer",
    "get_global_tracer",
    "reset_global_tracer",
]
