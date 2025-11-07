"""
Agent Scanner & Contract Extractor for UCOP Auto-Discovery System
Introspects agents.py to extract agent definitions and MCP contracts
"""

import ast
import inspect
import importlib.util
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
from datetime import datetime
import re


@dataclass
class AgentMetadata:
    """Metadata extracted from agent analysis"""
    name: str
    function_name: str
    is_async: bool
    parameters: List[Dict[str, Any]]
    return_type: Optional[str]
    docstring: Optional[str]
    decorators: List[str]
    has_contract: bool
    contract_method: Optional[str]
    imports_required: List[str]
    line_number: int
    source_code: str
    inferred_checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    inferred_capabilities: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


class AgentScanner:
    """
    Scans Python files to discover and extract agent definitions
    Uses AST parsing for static analysis without code execution
    """
    
    def __init__(self, agents_file: Path):
        self.agents_file = agents_file
        self.discovered_agents: Dict[str, AgentMetadata] = {}
        self.imports: Set[str] = set()
        self.contracts: Dict[str, Dict[str, Any]] = {}
        
    def scan(self) -> Dict[str, AgentMetadata]:
        """
        Main scanning method - orchestrates the discovery process
        
        Returns:
            Dictionary of agent_name -> AgentMetadata
        """
        print(f"🔍 Scanning {self.agents_file}...")
        
        # Step 1: Parse AST for static analysis
        with open(self.agents_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        tree = ast.parse(source_code)
        self._extract_imports(tree)
        self._extract_functions(tree, source_code)
        
        # Step 2: Dynamic introspection for contracts
        self._extract_contracts()
        
        # Step 3: Infer additional metadata
        self._infer_checkpoints()
        self._infer_capabilities()
        self._detect_dependencies()
        
        print(f"✓ Discovered {len(self.discovered_agents)} agents")
        return self.discovered_agents
    
    def _extract_imports(self, tree: ast.AST):
        """Extract all imports from the file"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    self.imports.add(f"{module}.{alias.name}")
    
    def _extract_functions(self, tree: ast.AST, source_code: str):
        """Extract function definitions that look like agents"""
        source_lines = source_code.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if this looks like an agent function
                if self._is_agent_function(node):
                    metadata = self._analyze_function(node, source_lines)
                    self.discovered_agents[metadata.name] = metadata
    
    def _is_agent_function(self, node: ast.FunctionDef) -> bool:
        """
        Determine if a function is an agent based on:
        - Naming convention (ends with _node, _agent, etc.)
        - Has specific decorators
        - Has contract method
        """
        name = node.name
        
        # Check naming patterns
        agent_patterns = ['_node', '_agent', '_writer', '_generator', '_checker']
        if any(name.endswith(pattern) for pattern in agent_patterns):
            return True
        
        # Check for agent decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id in ['agent', 'task', 'step']:
                    return True
        
        # Check docstring for agent indicators
        docstring = ast.get_docstring(node)
        if docstring:
            agent_keywords = ['agent', 'checkpoint', 'approval', 'MCP']
            if any(keyword in docstring for keyword in agent_keywords):
                return True
        
        return False
    
    def _analyze_function(
        self, 
        node: ast.FunctionDef, 
        source_lines: List[str]
    ) -> AgentMetadata:
        """Analyze a function node to extract metadata"""
        
        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param_info = {
                'name': arg.arg,
                'annotation': self._get_annotation(arg.annotation),
                'required': True
            }
            parameters.append(param_info)
        
        # Check for defaults
        defaults = node.args.defaults
        if defaults:
            num_defaults = len(defaults)
            for i in range(num_defaults):
                param_idx = len(parameters) - num_defaults + i
                parameters[param_idx]['required'] = False
                parameters[param_idx]['default'] = self._get_default_value(defaults[i])
        
        # Extract return type
        return_type = None
        if node.returns:
            return_type = self._get_annotation(node.returns)
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        # Check for decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
        
        # Check if it has a contract method
        has_contract = self._has_contract_method(node)
        
        # Extract source code
        start_line = node.lineno - 1
        end_line = node.end_lineno
        source_code = '\n'.join(source_lines[start_line:end_line])
        
        return AgentMetadata(
            name=node.name,
            function_name=node.name,
            is_async=isinstance(node, ast.AsyncFunctionDef) or 'async' in decorators,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            decorators=decorators,
            has_contract=has_contract,
            contract_method='_create_contract' if has_contract else None,
            imports_required=list(self.imports),
            line_number=node.lineno,
            source_code=source_code
        )
    
    def _get_annotation(self, node: Optional[ast.AST]) -> Optional[str]:
        """Extract type annotation as string"""
        if node is None:
            return None
        
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Subscript):
            # Handle Dict[str, Any], List[str], etc.
            return ast.unparse(node)
        elif isinstance(node, ast.Constant):
            return str(node.value)
        
        return ast.unparse(node) if hasattr(ast, 'unparse') else None
    
    def _get_default_value(self, node: ast.AST) -> Any:
        """Extract default parameter value"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return []
        elif isinstance(node, ast.Dict):
            return {}
        return None
    
    def _has_contract_method(self, node: ast.FunctionDef) -> bool:
        """Check if function has a _create_contract method"""
        # Look for _create_contract calls in the function body
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id == '_create_contract':
                        return True
                elif isinstance(child.func, ast.Attribute):
                    if child.func.attr == '_create_contract':
                        return True
        return False
    
    def _extract_contracts(self):
        """
        Dynamically load the module to extract contract information
        This requires executing the code
        """
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location("agents", self.agents_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract contracts from functions that have them
            for agent_name, metadata in self.discovered_agents.items():
                if metadata.has_contract:
                    func = getattr(module, agent_name, None)
                    if func and hasattr(func, '_create_contract'):
                        try:
                            contract = func._create_contract()
                            self.contracts[agent_name] = contract
                        except Exception as e:
                            print(f"⚠ Could not extract contract for {agent_name}: {e}")
        
        except Exception as e:
            print(f"⚠ Could not load module for contract extraction: {e}")
            print("  Contracts will be inferred from signatures")
    
    def _infer_checkpoints(self):
        """Infer checkpoints from agent analysis"""
        for agent_name, metadata in self.discovered_agents.items():
            checkpoints = [
                {
                    "name": "before_execution",
                    "description": f"Before {agent_name} starts",
                    "mutable_params": [p['name'] for p in metadata.parameters if not p['required']]
                }
            ]
            
            # Check docstring for checkpoint indicators
            if metadata.docstring:
                if 'approval' in metadata.docstring.lower():
                    checkpoints.append({
                        "name": "approval_gate",
                        "description": "Manual approval required",
                        "mutable_params": []
                    })
                
                if 'review' in metadata.docstring.lower():
                    checkpoints.append({
                        "name": "review_checkpoint",
                        "description": "Review required",
                        "mutable_params": []
                    })
            
            checkpoints.append({
                "name": "after_execution",
                "description": f"After {agent_name} completes",
                "mutable_params": []
            })
            
            metadata.inferred_checkpoints = checkpoints
    
    def _infer_capabilities(self):
        """Infer agent capabilities from code analysis"""
        for agent_name, metadata in self.discovered_agents.items():
            capabilities = {
                "stateful": self._is_stateful(metadata),
                "async": metadata.is_async,
                "model_switchable": self._supports_model_switch(metadata),
                "side_effects": self._detect_side_effects(metadata),
                "cacheable": self._is_cacheable(metadata)
            }
            
            metadata.inferred_capabilities = capabilities
    
    def _is_stateful(self, metadata: AgentMetadata) -> bool:
        """Check if agent maintains state"""
        # Check for 'state' parameter
        return any(p['name'] in ['state', 'context', 'session'] for p in metadata.parameters)
    
    def _supports_model_switch(self, metadata: AgentMetadata) -> bool:
        """Check if agent supports model switching"""
        return any(
            'model' in p['name'].lower() 
            for p in metadata.parameters
        )
    
    def _detect_side_effects(self, metadata: AgentMetadata) -> str:
        """Detect side effects from code analysis"""
        source = metadata.source_code.lower()
        
        if any(keyword in source for keyword in ['write', 'save', 'create', 'update', 'delete']):
            if 'file' in source or 'path' in source:
                return "fs"
            return "write"
        
        if any(keyword in source for keyword in ['http', 'request', 'fetch', 'api']):
            return "network"
        
        if any(keyword in source for keyword in ['read', 'load', 'get', 'fetch']):
            return "read"
        
        return "none"
    
    def _is_cacheable(self, metadata: AgentMetadata) -> bool:
        """Check if agent results can be cached"""
        # Agents with no side effects are cacheable
        if metadata.inferred_capabilities.get('side_effects') == 'none':
            return True
        
        # Agents with only read side effects are cacheable
        if metadata.inferred_capabilities.get('side_effects') == 'read':
            return True
        
        return False
    
    def _detect_dependencies(self):
        """Detect dependencies between agents"""
        # Analyze function calls within each agent
        for agent_name, metadata in self.discovered_agents.items():
            dependencies = []
            
            # Parse the source code to find function calls
            try:
                tree = ast.parse(metadata.source_code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            # Check if called function is another agent
                            called_name = node.func.id
                            if called_name in self.discovered_agents:
                                dependencies.append(called_name)
            except:
                pass
            
            metadata.dependencies = dependencies
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a discovery report"""
        return {
            "scan_time": datetime.utcnow().isoformat(),
            "source_file": str(self.agents_file),
            "total_agents": len(self.discovered_agents),
            "total_imports": len(self.imports),
            "agents": {
                name: {
                    "name": meta.name,
                    "is_async": meta.is_async,
                    "parameters": meta.parameters,
                    "return_type": meta.return_type,
                    "has_contract": meta.has_contract,
                    "checkpoints": meta.inferred_checkpoints,
                    "capabilities": meta.inferred_capabilities,
                    "dependencies": meta.dependencies,
                    "line": meta.line_number
                }
                for name, meta in self.discovered_agents.items()
            },
            "contracts_found": len(self.contracts),
            "imports": sorted(list(self.imports))
        }


class ContractExtractor:
    """Extracts and normalizes agent contracts to MCP format"""
    
    def __init__(self, scanner: AgentScanner):
        self.scanner = scanner
    
    def extract_mcp_contracts(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract or infer MCP-compliant contracts for all agents
        
        Returns:
            Dictionary of agent_name -> MCP contract
        """
        mcp_contracts = {}
        
        for agent_name, metadata in self.scanner.discovered_agents.items():
            # Use extracted contract if available
            if agent_name in self.scanner.contracts:
                contract = self._normalize_contract(
                    self.scanner.contracts[agent_name],
                    metadata
                )
            else:
                # Infer contract from metadata
                contract = self._infer_contract(metadata)
            
            mcp_contracts[agent_name] = contract
        
        return mcp_contracts
    
    def _normalize_contract(
        self, 
        contract: Dict[str, Any], 
        metadata: AgentMetadata
    ) -> Dict[str, Any]:
        """Normalize existing contract to full MCP format"""
        
        return {
            "id": metadata.name,
            "version": contract.get("version", "1.0.0"),
            "type": "agent",
            "description": metadata.docstring or f"Agent: {metadata.name}",
            "inputs": contract.get("inputs", self._infer_input_schema(metadata)),
            "outputs": contract.get("outputs", self._infer_output_schema(metadata)),
            "checkpoints": contract.get("checkpoints", metadata.inferred_checkpoints),
            "capabilities": {
                **metadata.inferred_capabilities,
                **contract.get("capabilities", {})
            },
            "resources": contract.get("resources", {
                "max_runtime_s": 300,
                "max_tokens": 4096,
                "max_memory_mb": 1024
            })
        }
    
    def _infer_contract(self, metadata: AgentMetadata) -> Dict[str, Any]:
        """Infer complete contract from metadata"""
        
        return {
            "id": metadata.name,
            "version": "1.0.0",
            "type": "agent",
            "description": metadata.docstring or f"Agent: {metadata.name}",
            "inputs": self._infer_input_schema(metadata),
            "outputs": self._infer_output_schema(metadata),
            "checkpoints": metadata.inferred_checkpoints,
            "capabilities": metadata.inferred_capabilities,
            "resources": {
                "max_runtime_s": 300,
                "max_tokens": 4096,
                "max_memory_mb": 1024
            }
        }
    
    def _infer_input_schema(self, metadata: AgentMetadata) -> Dict[str, Any]:
        """Infer JSON Schema for inputs from parameters"""
        properties = {}
        required = []
        
        for param in metadata.parameters:
            param_name = param['name']
            
            # Skip special parameters
            if param_name in ['self', 'cls', 'state', 'context']:
                continue
            
            prop = {
                "type": self._python_type_to_json_type(param.get('annotation', 'any')),
                "description": f"Parameter {param_name}"
            }
            
            if 'default' in param:
                prop['default'] = param['default']
            
            properties[param_name] = prop
            
            if param.get('required', False):
                required.append(param_name)
        
        return {
            "schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    
    def _infer_output_schema(self, metadata: AgentMetadata) -> Dict[str, Any]:
        """Infer JSON Schema for outputs from return type"""
        return_type = metadata.return_type or "dict"
        
        return {
            "schema": {
                "type": self._python_type_to_json_type(return_type),
                "description": f"Output from {metadata.name}"
            }
        }
    
    def _python_type_to_json_type(self, python_type: str) -> str:
        """Convert Python type annotation to JSON Schema type"""
        type_map = {
            'str': 'string',
            'int': 'integer',
            'float': 'number',
            'bool': 'boolean',
            'list': 'array',
            'dict': 'object',
            'Dict': 'object',
            'List': 'array',
            'Optional': 'object',
            'Any': 'object'
        }
        
        # Extract base type from complex annotations
        base_type = python_type.split('[')[0] if '[' in python_type else python_type
        
        return type_map.get(base_type, 'object')


# Example usage
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Scan the agents.py file
    agents_file = Path("agents.py")
    
    if not agents_file.exists():
        print(f"❌ {agents_file} not found")
        sys.exit(1)
    
    print("=" * 80)
    print("UCOP Agent Scanner & Contract Extractor")
    print("=" * 80)
    
    # Step 1: Scan agents
    scanner = AgentScanner(agents_file)
    agents = scanner.scan()
    
    print(f"\n📊 Discovery Summary:")
    print(f"  Total agents found: {len(agents)}")
    print(f"  Async agents: {sum(1 for a in agents.values() if a.is_async)}")
    print(f"  With contracts: {sum(1 for a in agents.values() if a.has_contract)}")
    print(f"  Total imports: {len(scanner.imports)}")
    
    # Step 2: Extract contracts
    extractor = ContractExtractor(scanner)
    contracts = extractor.extract_mcp_contracts()
    
    print(f"\n✓ Extracted {len(contracts)} MCP contracts")
    
    # Step 3: Generate report
    report = scanner.generate_report()
    
    # Save report
    report_file = Path("discovery_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✓ Report saved to {report_file}")
    
    # Print sample agents
    print(f"\n📝 Sample Discovered Agents:")
    for i, (name, meta) in enumerate(list(agents.items())[:5]):
        print(f"\n  {i+1}. {name}")
        print(f"     Async: {meta.is_async}")
        print(f"     Params: {len(meta.parameters)}")
        print(f"     Checkpoints: {len(meta.inferred_checkpoints)}")
        print(f"     Side effects: {meta.inferred_capabilities.get('side_effects', 'unknown')}")