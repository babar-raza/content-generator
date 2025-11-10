"""MCP (Model Context Protocol) package for agent contracts and compliance."""

from .contracts import (
    MCPContract,
    SideEffect,
    AgentRegistry,
    get_registry,
    create_ingestion_contract,
    create_writer_contract,
    create_code_contract
)
from .adapter import MCPComplianceAdapter
from .config_aware_executor import ConfigAwareMCPExecutor

__all__ = [
    'MCPContract',
    'SideEffect',
    'AgentRegistry',
    'get_registry',
    'create_ingestion_contract',
    'create_writer_contract',
    'create_code_contract',
    'MCPComplianceAdapter',
    'ConfigAwareMCPExecutor'
]
