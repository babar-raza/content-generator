"""MCP Compliance Adapter - Helps agents comply with MCP standards."""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import logging

from .contracts import MCPContract, get_registry

logger = logging.getLogger(__name__)


class MCPComplianceAdapter:
    """Adapter to help agents comply with MCP contract standards."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the adapter.
        
        Args:
            config_dir: Directory containing agent configuration files
        """
        self.config_dir = config_dir or Path("./config")
        self.registry = get_registry()
        self._contract_cache: Dict[str, MCPContract] = {}
        
    def load_contracts(self) -> int:
        """Load contracts from configuration directory.
        
        Returns:
            Number of contracts loaded
        """
        if not self.config_dir.exists():
            logger.warning(f"Config directory {self.config_dir} does not exist")
            return 0
            
        loaded = 0
        contracts_file = self.config_dir / "agents.json"
        
        if contracts_file.exists():
            try:
                with open(contracts_file, 'r') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict) and 'agents' in data:
                    agents = data['agents']
                elif isinstance(data, list):
                    agents = data
                else:
                    agents = [data]
                    
                for agent_data in agents:
                    try:
                        contract = MCPContract(**agent_data)
                        self.registry.register(contract)
                        self._contract_cache[contract.id] = contract
                        loaded += 1
                    except Exception as e:
                        logger.error(f"Failed to load contract {agent_data.get('id', 'unknown')}: {e}")
                        
            except Exception as e:
                logger.error(f"Failed to load contracts from {contracts_file}: {e}")
                
        return loaded
    
    def validate_agent(self, agent_id: str, inputs: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate agent inputs against contract.
        
        Args:
            agent_id: ID of the agent
            inputs: Input data to validate
            
        Returns:
            Tuple of (is_valid, list of errors)
        """
        contract = self.registry.get(agent_id)
        if not contract:
            return False, [f"No contract found for agent {agent_id}"]
            
        errors = []
        input_schema = contract.inputs
        
        # Basic validation
        if 'required' in input_schema:
            for required_field in input_schema['required']:
                if required_field not in inputs:
                    errors.append(f"Missing required field: {required_field}")
        
        # Type validation (simplified)
        if 'properties' in input_schema:
            for field, schema in input_schema['properties'].items():
                if field in inputs:
                    value = inputs[field]
                    expected_type = schema.get('type')
                    
                    type_map = {
                        'string': str,
                        'integer': int,
                        'number': (int, float),
                        'boolean': bool,
                        'array': list,
                        'object': dict
                    }
                    
                    if expected_type in type_map:
                        expected_python_type = type_map[expected_type]
                        if not isinstance(value, expected_python_type):
                            errors.append(f"Field {field} should be {expected_type}, got {type(value).__name__}")
        
        return len(errors) == 0, errors
    
    def get_contract(self, agent_id: str) -> Optional[MCPContract]:
        """Get contract for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            MCPContract or None if not found
        """
        return self.registry.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents.
        
        Returns:
            List of agent contract dictionaries
        """
        return self.registry.list_all()
    
    def create_default_contract(
        self,
        agent_id: str,
        agent_type: str = "generic",
        **kwargs
    ) -> MCPContract:
        """Create a default contract for an agent.
        
        Args:
            agent_id: ID of the agent
            agent_type: Type of agent (generic, ingestion, writer, code, etc.)
            **kwargs: Additional contract parameters
            
        Returns:
            MCPContract instance
        """
        defaults = {
            "version": "1.0.0",
            "inputs": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "outputs": {
                "type": "object",
                "properties": {}
            },
            "checkpoints": ["initialized", "processing", "completed"],
            "max_runtime_s": 300,
            "confidence": 0.8,
            "side_effects": ["none"],
            "description": f"{agent_id} agent"
        }
        
        defaults.update(kwargs)
        defaults['id'] = agent_id
        
        contract = MCPContract(**defaults)
        self.registry.register(contract)
        return contract
    
    def export_contracts(self, output_path: Path) -> bool:
        """Export all contracts to a JSON file.
        
        Args:
            output_path: Path to output file
            
        Returns:
            True if successful
        """
        try:
            contracts = self.list_agents()
            with open(output_path, 'w') as f:
                json.dump({"agents": contracts}, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export contracts: {e}")
            return False
# DOCGEN:LLM-FIRST@v4