"""
Adjusted Agent Scanner for Blog Generator
Handles your specific patterns: _node suffix, separate contracts, LangGraph integration
"""

import ast
import json
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentMetadata:
    """Metadata extracted from agent analysis"""
    name: str
    function_name: str
    is_async: bool
    parameters: List[Dict[str, Any]]
    return_type: Optional[str]
    docstring: Optional[str]
    line_number: int
    has_contract_in_schemas: bool = False
    contract_schema: Optional[Dict[str, Any]] = None
    prompt_template: Optional[str] = None
    inferred_checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    side_effects: str = "none"


class BlogGeneratorScanner:
    """Scanner adjusted for your blog generator patterns"""
    
    def __init__(self, agents_file: Path, contracts_file: Path, config_file: Path):
        self.agents_file = agents_file
        self.contracts_file = contracts_file
        self.config_file = config_file
        self.discovered_agents: Dict[str, AgentMetadata] = {}
        self.agent_schemas: Dict[str, Dict[str, Any]] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.config_values: Dict[str, Any] = {}
        
    def scan_all(self) -> Dict[str, Any]:
        """Scan all files and build complete picture"""
        print("🔍 Scanning blog generator...")
        
        # Step 1: Load contracts from contracts.py
        print("  📄 Loading contracts from contracts.py...")
        self._load_contracts()
        
        # Step 2: Load prompts and config from config.py
        print("  📄 Loading prompts and config from config.py...")
        self._load_config()
        
        # Step 3: Scan agents from agents.py
        print("  📄 Scanning agents from agents.py...")
        self._scan_agents()
        
        # Step 4: Match agents with contracts and prompts
        print("  🔗 Matching agents with contracts and prompts...")
        self._match_metadata()
        
        print(f"✓ Discovered {len(self.discovered_agents)} agents")
        return self.generate_report()
    
    def _load_contracts(self):
        """Load AGENT_SCHEMAS from contracts.py"""
        try:
            with open(self.contracts_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find AGENT_SCHEMAS
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "AGENT_SCHEMAS":
                            # Found AGENT_SCHEMAS - evaluate it
                            # This is safe because we control the input
                            schemas_str = ast.get_source_segment(content, node.value)
                            if schemas_str:
                                # Execute in isolated namespace
                                namespace = {}
                                # Import SCHEMAS from config for references
                                exec("from config import SCHEMAS", namespace)
                                exec(f"AGENT_SCHEMAS = {schemas_str}", namespace)
                                self.agent_schemas = namespace.get("AGENT_SCHEMAS", {})
                                print(f"    ✓ Loaded {len(self.agent_schemas)} contract schemas")
                                return
        except Exception as e:
            print(f"    ⚠ Could not load contracts: {e}")
    
    def _load_config(self):
        """Load PROMPTS and config values from config.py"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Find PROMPTS dictionary
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if target.id == "PROMPTS":
                                prompts_str = ast.get_source_segment(content, node.value)
                                if prompts_str:
                                    namespace = {}
                                    exec(f"PROMPTS = {prompts_str}", namespace)
                                    self.prompts = namespace.get("PROMPTS", {})
                                    print(f"    ✓ Loaded {len(self.prompts)} prompt templates")
            
            # Extract Config dataclass fields for policies
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "Config":
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            field_name = item.target.id
                            # Try to extract default value
                            if item.value:
                                try:
                                    value_str = ast.get_source_segment(content, item.value)
                                    self.config_values[field_name] = value_str
                                except:
                                    pass
                    print(f"    ✓ Found {len(self.config_values)} config fields")
        
        except Exception as e:
            print(f"    ⚠ Could not load config: {e}")
    
    def _scan_agents(self):
        """Scan agents.py for functional nodes"""
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            source_lines = content.split('\n')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if this is an agent node
                    if node.name.endswith('_node'):
                        metadata = self._analyze_agent_function(node, source_lines)
                        self.discovered_agents[metadata.name] = metadata
        
        except Exception as e:
            print(f"    ⚠ Could not scan agents: {e}")
    
    def _analyze_agent_function(self, node: ast.FunctionDef, source_lines: List[str]) -> AgentMetadata:
        """Analyze a single agent function"""
        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param_info = {
                'name': arg.arg,
                'annotation': self._get_annotation(arg.annotation),
                'required': True
            }
            parameters.append(param_info)
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        # Detect side effects from code
        side_effects = self._detect_side_effects_from_source(node, source_lines)
        
        return AgentMetadata(
            name=node.name,
            function_name=node.name,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            parameters=parameters,
            return_type=self._get_annotation(node.returns),
            docstring=docstring,
            line_number=node.lineno,
            side_effects=side_effects
        )
    
    def _get_annotation(self, node: Optional[ast.AST]) -> Optional[str]:
        """Extract type annotation as string"""
        if node is None:
            return None
        
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Subscript):
            return ast.unparse(node)
        elif isinstance(node, ast.Constant):
            return str(node.value)
        
        return ast.unparse(node) if hasattr(ast, 'unparse') else None
    
    def _detect_side_effects_from_source(self, node: ast.FunctionDef, source_lines: List[str]) -> str:
        """Detect side effects from function body"""
        # Get function source
        start = node.lineno - 1
        end = node.end_lineno
        func_source = '\n'.join(source_lines[start:end]).lower()
        
        if 'write' in func_source or 'save' in func_source:
            if 'file' in func_source or 'path' in func_source:
                return "fs"
            return "write"
        
        if 'http' in func_source or 'api' in func_source or 'request' in func_source:
            return "network"
        
        if 'read' in func_source or 'load' in func_source:
            return "read"
        
        return "none"
    
    def _match_metadata(self):
        """Match agents with contracts and prompts"""
        for agent_name, metadata in self.discovered_agents.items():
            # Try to match with contract
            # Convert function name to Agent class name pattern
            # e.g., ingest_kb_node -> KBIngestionAgent
            possible_contract_names = [
                agent_name,  # exact match
                self._node_name_to_agent_class(agent_name)  # converted name
            ]
            
            for contract_name in possible_contract_names:
                if contract_name in self.agent_schemas:
                    metadata.has_contract_in_schemas = True
                    metadata.contract_schema = self.agent_schemas[contract_name]
                    break
            
            # Try to match with prompt template
            prompt_key = self._infer_prompt_key(agent_name)
            if prompt_key in self.prompts:
                metadata.prompt_template = prompt_key
            
            # Infer checkpoints
            metadata.inferred_checkpoints = self._infer_checkpoints(metadata)
    
    def _node_name_to_agent_class(self, node_name: str) -> str:
        """Convert node function name to Agent class name"""
        # Remove _node suffix
        base = node_name.replace('_node', '')
        
        # Convert snake_case to TitleCase and add Agent suffix
        parts = base.split('_')
        class_name = ''.join(p.capitalize() for p in parts) + 'Agent'
        
        return class_name
    
    def _infer_prompt_key(self, agent_name: str) -> str:
        """Infer prompt key from agent name"""
        # Map common patterns
        mappings = {
            'ingest_kb': None,  # No prompt needed
            'identify_topics': 'TOPIC_IDENTIFICATION',
            'topic_prep': None,
            'check_duplication': None,
            'create_outline': 'OUTLINE_CREATION',
            'introduction_writer': 'INTRODUCTION_WRITER',
            'section_writer': 'SECTION_WRITER',
            'content_assembly': None,
            'seo_metadata': 'SEO_METADATA',
            'frontmatter': None,
            'write_file': None
        }
        
        base_name = agent_name.replace('_node', '')
        return mappings.get(base_name)
    
    def _infer_checkpoints(self, metadata: AgentMetadata) -> List[Dict[str, Any]]:
        """Infer checkpoints for an agent"""
        checkpoints = [
            {
                "name": "before_execution",
                "description": f"Before {metadata.name} starts",
                "mutable_params": []
            }
        ]
        
        # Add specific checkpoints based on agent type
        if 'outline' in metadata.name:
            checkpoints.append({
                "name": "outline_ready",
                "description": "Outline created and ready for review",
                "mutable_params": []
            })
        
        if 'content_assembly' in metadata.name:
            checkpoints.append({
                "name": "content_assembled",
                "description": "Content assembled and ready for review",
                "mutable_params": []
            })
        
        checkpoints.append({
            "name": "after_execution",
            "description": f"After {metadata.name} completes",
            "mutable_params": []
        })
        
        return checkpoints
    
<<<<<<< Updated upstream
    def generate_report(self) -> Dict[str, Any]:
        """Generate discovery report"""
        return {
            "scan_time": datetime.utcnow().isoformat(),
            "files_scanned": {
                "agents": str(self.agents_file),
                "contracts": str(self.contracts_file),
                "config": str(self.config_file)
            },
            "discovered_agents": len(self.discovered_agents),
            "agents": {
                name: {
                    "name": meta.name,
                    "line": meta.line_number,
                    "is_async": meta.is_async,
                    "parameters": meta.parameters,
                    "has_contract": meta.has_contract_in_schemas,
                    "has_prompt": meta.prompt_template is not None,
                    "prompt_key": meta.prompt_template,
                    "side_effects": meta.side_effects,
                    "checkpoints": meta.inferred_checkpoints,
                    "docstring": meta.docstring
                }
                for name, meta in self.discovered_agents.items()
            },
            "contracts_available": len(self.agent_schemas),
            "prompts_available": len(self.prompts),
            "config_fields": len(self.config_values)
        }
    
    def generate_yaml_config(self) -> Dict[str, Any]:
        """Generate agents.yaml configuration"""
        agents_config = {
            "version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat(),
            "source": "blog-generator auto-discovery",
            "agents": {}
        }
        
        for agent_name, metadata in self.discovered_agents.items():
            agent_config = {
                "id": agent_name,
                "version": "1.0.0",
                "description": metadata.docstring or f"Agent: {agent_name}",
                "entrypoint": {
                    "type": "python",
                    "module": "agents",
                    "function": agent_name,
                    "async": metadata.is_async
                },
                "contract": {
                    "inputs": metadata.contract_schema.get("input", {}) if metadata.contract_schema else {},
                    "outputs": metadata.contract_schema.get("output", {}) if metadata.contract_schema else {},
                    "checkpoints": metadata.inferred_checkpoints
                },
                "capabilities": {
                    "stateful": any(p['name'] == 'state' for p in metadata.parameters),
                    "async": metadata.is_async,
                    "model_switchable": metadata.prompt_template is not None,
                    "side_effects": metadata.side_effects
                },
                "resources": {
                    "max_runtime_s": 300,
                    "max_tokens": 4096,
                    "max_memory_mb": 1024
                }
            }
            
            if metadata.prompt_template:
                agent_config["prompt_template"] = metadata.prompt_template
            
            agents_config["agents"][agent_name] = agent_config
        
        return agents_config


# Test it out
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    print("=" * 80)
    print("Blog Generator Auto-Discovery Scanner")
    print("=" * 80)
    
    # File paths
    agents_file = Path("agents.py")
    contracts_file = Path("contracts.py")
    config_file = Path("config.py")
    
    # Check files exist
    missing = []
    for f in [agents_file, contracts_file, config_file]:
        if not f.exists():
            missing.append(str(f))
    
    if missing:
        print(f"❌ Missing files: {', '.join(missing)}")
        sys.exit(1)
    
    # Run scanner
    scanner = BlogGeneratorScanner(agents_file, contracts_file, config_file)
    report = scanner.scan_all()
    
    # Save report
    report_file = Path("discovery_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n✓ Report saved to {report_file}")
    
    # Generate agents.yaml
    yaml_config = scanner.generate_yaml_config()
    yaml_file = Path("agents.yaml")
    
    import yaml
    with open(yaml_file, 'w') as f:
        yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)
    print(f"✓ Generated {yaml_file}")
    
    # Print summary
    print(f"\n📊 Discovery Summary:")
    print(f"  Agents discovered: {report['discovered_agents']}")
    print(f"  With contracts: {sum(1 for a in report['agents'].values() if a['has_contract'])}")
    print(f"  With prompts: {sum(1 for a in report['agents'].values() if a['has_prompt'])}")
    print(f"  Available contracts: {report['contracts_available']}")
    print(f"  Available prompts: {report['prompts_available']}")
    
    # Print agent list
    print(f"\n📝 Discovered Agents:")
    for i, (name, info) in enumerate(report['agents'].items(), 1):
        status = []
        if info['has_contract']:
            status.append("✓ contract")
        if info['has_prompt']:
            status.append(f"✓ prompt:{info['prompt_key']}")
        status_str = ", ".join(status) if status else "no contract/prompt"
        print(f"  {i}. {name} ({status_str})")
=======
    def invalidate_cache(self) -> None:
        """Invalidate the agent discovery cache."""
        self._cache_valid = False
    
    def trigger_reload(self) -> List[Type]:
        """Trigger a full agent reload.
        
        This method is called by hot reload monitor when agent configurations change.
        
        Returns:
            List of discovered Agent class types
        """
        logger.info("Triggering agent reload due to configuration change")
        return self.discover(force_rescan=True)
>>>>>>> Stashed changes
