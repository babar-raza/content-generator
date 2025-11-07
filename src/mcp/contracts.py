"""MCP Contract System - Agent contracts for discovery and validation."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json


class SideEffect(str, Enum):
    """Agent side effects."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    NETWORK = "network"
    FILESYSTEM = "fs"


@dataclass
class MCPContract:
    """MCP-compliant agent contract."""
    id: str
    version: str
    inputs: Dict[str, Any]  # JSON Schema
    outputs: Dict[str, Any]  # JSON Schema
    checkpoints: List[str]
    max_runtime_s: int
    confidence: float  # 0.0 to 1.0
    side_effects: List[str]
    description: Optional[str] = None
    mutable_params: Optional[List[str]] = None  # Runtime-changeable
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def validate(self) -> List[str]:
        """Validate contract, return list of errors."""
        errors = []
        
        if not self.id:
            errors.append("id is required")
        if not self.version:
            errors.append("version is required")
        if not 0 <= self.confidence <= 1:
            errors.append("confidence must be between 0 and 1")
        if self.max_runtime_s <= 0:
            errors.append("max_runtime_s must be positive")
        if not self.checkpoints:
            errors.append("at least one checkpoint required")
            
        return errors


class AgentRegistry:
    """Registry of all agents and their contracts."""
    
    def __init__(self):
        self.agents: Dict[str, MCPContract] = {}
        
    def register(self, contract: MCPContract) -> bool:
        """Register an agent contract."""
        errors = contract.validate()
        if errors:
            raise ValueError(f"Invalid contract: {', '.join(errors)}")
        
        self.agents[contract.id] = contract
        return True
    
    def get(self, agent_id: str) -> Optional[MCPContract]:
        """Get contract for an agent."""
        return self.agents.get(agent_id)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [c.to_dict() for c in self.agents.values()]
    
    def search(self, capability: str = None, side_effect: str = None) -> List[MCPContract]:
        """Search agents by capability or side effect."""
        results = list(self.agents.values())
        
        if capability:
            # Search in description
            results = [c for c in results if capability.lower() in (c.description or '').lower()]
        
        if side_effect:
            results = [c for c in results if side_effect in c.side_effects]
        
        return results


# Global registry instance
_registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Get the global agent registry."""
    return _registry


# Common contract templates
def create_ingestion_contract(agent_id: str, subdomain: str) -> MCPContract:
    """Template for ingestion agents."""
    return MCPContract(
        id=agent_id,
        version="1.0.0",
        inputs={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to ingest"},
                "subdomain": {"type": "string", "default": subdomain}
            },
            "required": ["path"]
        },
        outputs={
            "type": "object",
            "properties": {
                "docs_ingested": {"type": "integer"},
                "chunks_created": {"type": "integer"},
                "embeddings_generated": {"type": "integer"}
            }
        },
        checkpoints=["initialized", "parsed", "embedded", "stored", "completed"],
        max_runtime_s=600,
        confidence=0.95,
        side_effects=[SideEffect.READ, SideEffect.WRITE],
        description=f"Ingest content from {subdomain}"
    )


def create_writer_contract(agent_id: str, component: str) -> MCPContract:
    """Template for content writer agents."""
    return MCPContract(
        id=agent_id,
        version="1.0.0",
        inputs={
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "context": {"type": "object"},
                "tone": {"type": "string", "enum": ["professional", "casual", "technical"]},
                "max_words": {"type": "integer", "minimum": 100}
            },
            "required": ["topic"]
        },
        outputs={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "word_count": {"type": "integer"},
                "sections": {"type": "array", "items": {"type": "string"}}
            }
        },
        checkpoints=["initialized", "researched", "drafted", "reviewed", "completed"],
        max_runtime_s=300,
        confidence=0.85,
        side_effects=[SideEffect.NETWORK],  # May call LLM
        description=f"Generate {component} content",
        mutable_params=["tone", "max_words"]  # Can change at runtime
    )


def create_code_contract(agent_id: str) -> MCPContract:
    """Template for code generation agents."""
    return MCPContract(
        id=agent_id,
        version="1.0.0",
        inputs={
            "type": "object",
            "properties": {
                "language": {"type": "string"},
                "description": {"type": "string"},
                "style": {"type": "string"},
                "validate": {"type": "boolean", "default": True}
            },
            "required": ["language", "description"]
        },
        outputs={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"},
                "is_valid": {"type": "boolean"},
                "errors": {"type": "array", "items": {"type": "string"}}
            }
        },
        checkpoints=["initialized", "generated", "validated", "completed"],
        max_runtime_s=180,
        confidence=0.80,
        side_effects=[SideEffect.NETWORK],
        description=f"Generate {agent_id} code examples"
    )
