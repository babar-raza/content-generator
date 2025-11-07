"""Core Infrastructure

Unified core components combining v5_1, v5_2, and v-ucop features.
"""

from .contracts import (
    AgentEvent, AgentContract, DataContract,
    CapabilitySpec, Bid, WorkSpec, BidResult,
    CapacityInfo, FlowControlEvent,
    CapabilityStatus, FlowControlStatus, CapacityLevel,
)
from .event_bus import EventBus
from .agent_base import Agent, SelfCorrectingAgent
from .config import Config, LLMConfig, DatabaseConfig, MeshConfig, OrchestrationConfig, SCHEMAS, load_schemas

__all__ = [
    # Contracts
    'AgentEvent', 'AgentContract', 'DataContract',
    'CapabilitySpec', 'Bid', 'WorkSpec', 'BidResult',
    'CapacityInfo', 'FlowControlEvent',
    'CapabilityStatus', 'FlowControlStatus', 'CapacityLevel',

    # Event Bus
    'EventBus',

    # Agent Base
    'Agent', 'SelfCorrectingAgent',

    # Config
    'Config', 'LLMConfig', 'DatabaseConfig', 'MeshConfig', 'OrchestrationConfig', 'SCHEMAS', 'load_schemas',
]
