"""Unified Contract System

Combines contracts from v5_1 (base), v5_2 (mesh enhancements), and v-ucop (full schemas).

Module overview
- Purpose: Defines unified contract system for agent communication, capabilities, and mesh interactions across the content generator system.
- Lifecycle: Imported during system startup to establish communication protocols.
- Collaborators: Used by src.core.event_bus, src.core.agent_base, src.mesh.negotiation, and orchestration modules.
- Key inputs: None (static definitions).
- Key outputs: Contract classes and enums for event handling, agent capabilities, bidding, and negotiation.

Public API Catalog
| Symbol | Kind | Defined in | Purpose | Inputs | Outputs | Raises | Notes |
|-------:|:-----|:-----------|:--------|:-------|:--------|:-------|:------|
| AgentEvent | class | contracts | Event for agent communication | event_type: str, data: Dict[str, Any], source_agent: str, correlation_id: str, timestamp: str, metadata: Dict[str, Any] | AgentEvent instance | None | Serializable via to_dict/from_dict |
| AgentContract | class | contracts | Contract defining agent capabilities and schemas | agent_id: str, capabilities: List[str], input_schema: Dict[str, Any], output_schema: Dict[str, Any], publishes: List[str], resource_profile: str, version: str | AgentContract instance | None | Defines agent interfaces |
| DataContract | class | contracts | Contract for data validation and extraction | input_schema: Dict[str, Any], output_schema: Dict[str, Any] | Dict[str, Any] | None | Thread-safe with threading.Lock |
| CapabilitySpec | class | contracts | Rich metadata for agent capabilities | name: str, input_requirements: List[str], output_guarantees: List[str], preconditions: Optional[Callable], cost_estimate: float, max_concurrency: int, confidence_threshold: float, retry_policy: Dict[str, Any] | CapabilitySpec instance | Exception | Evaluates preconditions; raises in evaluate_preconditions |
| Bid | class | contracts | Bid for capability execution | agent_id: str, capability: str, correlation_id: str, estimated_time: float, confidence: float, priority: int, current_load: int, max_capacity: int, health_score: float, success_rate: float, additional_info: Dict[str, Any], timestamp: datetime | Bid instance | None | Has score property (weighted calculation) |
| WorkSpec | class | contracts | Specification for work to be done | work_id: str, capability: str, correlation_id: str, input_data: Dict[str, Any], timeout: float, max_retries: int, priority: int, metadata: Dict[str, Any] | WorkSpec instance | None | Defines work requirements |
| BidResult | class | contracts | Result of bidding process | work_spec: WorkSpec, winning_bid: Optional[Bid], all_bids: List[Bid], selection_time: datetime, strategy_used: str | BidResult instance | None | Contains bidding outcomes |
| CapacityInfo | class | contracts | Information about agent capacity | agent_id: str, current_load: int, max_capacity: int, status: FlowControlStatus, capacity_level: CapacityLevel | CapacityInfo instance | None | Has utilization property (current_load/max_capacity) |
| FlowControlEvent | class | contracts | Event for flow control | event_type: str, agent_id: str, capacity_info: CapacityInfo, timestamp: datetime | FlowControlEvent instance | None | For overload/throttle management |
| CapabilityStatus | enum | contracts | Status of capability | None | CapabilityStatus | None | Values: AVAILABLE, BIDDING, EXECUTING, COMPLETED, FAILED |
| FlowControlStatus | enum | contracts | Status of flow control | None | FlowControlStatus | None | Values: AVAILABLE, OVERLOADED, THROTTLED, UNAVAILABLE |
| CapacityLevel | enum | contracts | Level of capacity | None | CapacityLevel | None | Values: LOW, MEDIUM, HIGH, CRITICAL |
| NegotiationStatus | enum | contracts | Status of negotiation | None | NegotiationStatus | None | Values: REQUESTED, BIDDING, CLAIMED, EXECUTING, COMPLETED, FAILED, CANCELLED |
| CapabilityRequest | class | contracts | Request for capability | request_id: str, requester_id: str, capability: str, correlation_id: str, input_data: Dict[str, Any], constraints: Dict[str, Any], urgency: str, deadline: Optional[datetime], dependencies: List[str], preferred_agents: List[str], excluded_agents: List[str], max_wait_time: float, timestamp: datetime | CapabilityRequest instance | None | For distributed work requests |
| NegotiationBid | class | contracts | Bid in negotiation | request_id: str, bid_id: str, agent_id: str, capability: str, correlation_id: str, estimated_time: float, confidence: float, priority: int, conditions: Dict[str, Any], dependencies_ready: bool, can_start_immediately: bool, alternative_capability: Optional[str], timestamp: datetime | NegotiationBid instance | None | Response to capability requests |
| CapabilityClaim | class | contracts | Claim for capability | request_id: str, claim_id: str, agent_id: str, capability: str, correlation_id: str, estimated_completion: datetime, conditions_accepted: Dict[str, Any], dependencies_tracking: List[str], timestamp: datetime | CapabilityClaim instance | None | Agent commitment to execute |
| DependencySpec | class | contracts | Specification of dependency | dependency_id: str, required_capability: str, required_output: str, correlation_id: str, timeout: float, is_critical: bool, fallback_strategy: Optional[str], timestamp: datetime | DependencySpec instance | None | For work dependencies |

Deeper dive
- Data flow: Static definitions loaded at import → classes instantiated by event_bus, agent_base modules → contracts used for validation.
- Invariants & contracts: All contract classes must be serializable; enums must be stable across versions; thread-safety in DataContract.
- Preconditions: None.
- Postconditions: All classes and enums available for import.
- Error surface: Validation failures in DataContract methods; precondition evaluation exceptions in CapabilitySpec.
- Concurrency & async: Thread-safe DataContract with Lock; no async.
- I/O & performance: Lightweight dataclasses with minimal computation; thread locks in DataContract for concurrent access.
- Configuration map: None.
- External dependencies: typing, datetime, dataclasses, enum, logging, threading.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# BASE EVENT MODEL (from v5_1)
# ============================================================================

@dataclass
class AgentEvent:
    """Event for agent communication."""
    event_type: str
    data: Dict[str, Any]
    source_agent: str
    correlation_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "source_agent": self.source_agent,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentEvent':
        """Create from dictionary."""
        return cls(**data)


# ============================================================================
# BASE CONTRACT MODELS (from v5_1)
# ============================================================================

@dataclass
class AgentContract:
    """Contract defining agent capabilities and schemas."""
    agent_id: str
    capabilities: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    publishes: List[str]
    resource_profile: str = "cpu_light"
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "publishes": self.publishes,
            "resource_profile": self.resource_profile,
            "version": self.version
        }


class DataContract:
    """Contract for data validation and extraction."""
    def __init__(self, input_schema: Dict[str, Any], output_schema: Dict[str, Any]):
        self.input_schema = input_schema
        self.output_schema = output_schema
        self._lock = threading.Lock()

    def extract_required_data(self, full_data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            required_fields = self.input_schema.get("required", [])
            minimal = {}
            for f in required_fields:
                if f in full_data:
                    minimal[f] = full_data[f]
            return minimal

    def validate_input(self, data: Dict[str, Any]) -> bool:
        required_fields = self.input_schema.get("required", [])
        return all(f in data for f in required_fields)

    def validate_output(self, data: Dict[str, Any]) -> bool:
        required_fields = self.output_schema.get("required", [])
        return all(f in data for f in required_fields)


# ============================================================================
# MESH ENHANCEMENTS (from v5_2)
# ============================================================================

class CapabilityStatus(Enum):
    AVAILABLE = "available"
    BIDDING = "bidding"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class FlowControlStatus(Enum):
    AVAILABLE = "available"
    OVERLOADED = "overloaded"
    THROTTLED = "throttled"
    UNAVAILABLE = "unavailable"


class CapacityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CapabilitySpec:
    """Rich metadata for agent capabilities."""
    name: str
    input_requirements: List[str]
    output_guarantees: List[str]
    preconditions: Optional[Callable] = None
    cost_estimate: float = 1.0
    max_concurrency: int = 3
    confidence_threshold: float = 0.7
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"max_retries": 3, "backoff": 2})

    def evaluate_preconditions(self, state: Dict[str, Any]) -> bool:
        if self.preconditions:
            try:
                return self.preconditions(state)
            except Exception:
                return False
        return True

    def check_inputs(self, state: Dict[str, Any]) -> bool:
        for requirement in self.input_requirements:
            if not self._evaluate_requirement(requirement, state):
                return False
        return True

    def _evaluate_requirement(self, requirement: str, state: Dict[str, Any]) -> bool:
        if " OR " in requirement:
            parts = requirement.strip("()").split(" OR ")
            return any(part.strip() in state for part in parts)
        if " AND " in requirement:
            parts = requirement.split(" AND ")
            return all(part.strip() in state for part in parts)
        return requirement in state


@dataclass
class Bid:
    agent_id: str
    capability: str
    correlation_id: str
    estimated_time: float
    confidence: float
    priority: int
    current_load: int
    max_capacity: int
    health_score: float
    success_rate: float
    additional_info: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def score(self) -> float:
        load_factor = 1 - (self.current_load / max(self.max_capacity, 1))
        return (self.confidence * 0.4 +
                (self.priority / 10) * 0.2 +
                load_factor * 0.2 +
                self.health_score * 0.1 +
                self.success_rate * 0.1)


@dataclass
class WorkSpec:
    work_id: str
    capability: str
    correlation_id: str
    input_data: Dict[str, Any]
    timeout: float = 30.0
    max_retries: int = 3
    priority: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BidResult:
    work_spec: WorkSpec
    winning_bid: Optional[Bid]
    all_bids: List[Bid]
    selection_time: datetime
    strategy_used: str


@dataclass
class CapacityInfo:
    agent_id: str
    current_load: int
    max_capacity: int
    status: FlowControlStatus
    capacity_level: CapacityLevel

    @property
    def utilization(self) -> float:
        return self.current_load / max(self.max_capacity, 1)


@dataclass
class FlowControlEvent:
    event_type: str  # "overload", "throttle", "resume"
    agent_id: str
    capacity_info: CapacityInfo
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# NEGOTIATION CONTRACTS (from v5_2)
# ============================================================================

class NegotiationStatus(Enum):
    """Status of capability negotiation."""
    REQUESTED = "requested"
    BIDDING = "bidding"
    CLAIMED = "claimed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CapabilityRequest:
    """Request for a capability from peer agents."""
    request_id: str
    requester_id: str
    capability: str
    correlation_id: str
    input_data: Dict[str, Any]
    constraints: Dict[str, Any] = field(default_factory=dict)
    urgency: str = "normal"
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    preferred_agents: List[str] = field(default_factory=list)
    excluded_agents: List[str] = field(default_factory=list)
    max_wait_time: float = 30.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class NegotiationBid:
    """Bid response to a capability request."""
    request_id: str
    bid_id: str
    agent_id: str
    capability: str
    correlation_id: str
    estimated_time: float
    confidence: float
    priority: int
    conditions: Dict[str, Any] = field(default_factory=dict)
    dependencies_ready: bool = False
    can_start_immediately: bool = True
    alternative_capability: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CapabilityClaim:
    """Claim that an agent will execute a capability."""
    request_id: str
    claim_id: str
    agent_id: str
    capability: str
    correlation_id: str
    estimated_completion: datetime
    conditions_accepted: Dict[str, Any] = field(default_factory=dict)
    dependencies_tracking: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DependencySpec:
    """Specification of what an agent depends on."""
    dependency_id: str
    required_capability: str
    required_output: str
    correlation_id: str
    timeout: float = 60.0
    is_critical: bool = True
    fallback_strategy: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


__all__ = [
    # Base
    'AgentEvent',
    'AgentContract',
    'DataContract',

    # Mesh Enhancements
    'CapabilityStatus',
    'FlowControlStatus',
    'CapacityLevel',
    'CapabilitySpec',
    'Bid',
    'WorkSpec',
    'BidResult',
    'CapacityInfo',
    'FlowControlEvent',
    
    # Negotiation
    'NegotiationStatus',
    'CapabilityRequest',
    'NegotiationBid',
    'CapabilityClaim',
    'DependencySpec',
]
# DOCGEN:LLM-FIRST@v4