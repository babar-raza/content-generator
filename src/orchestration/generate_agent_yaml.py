"""
YAML Generator for UCOP Auto-Discovery System
Generates agents.yaml and workflows.yaml from discovered agents
"""

import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass


@dataclass
class WorkflowTemplate:
    """Template for generating workflows"""
    name: str
    description: str
    agents: List[str]
    trigger_type: str = "manual"
    schedule: Optional[str] = None
    approval_gates: List[str] = None


class YAMLGenerator:
    """Generates YAML configuration files from discovered agents"""
    
    def __init__(self, agents_metadata: Dict[str, Any], contracts: Dict[str, Dict[str, Any]]):
        self.agents_metadata = agents_metadata
        self.contracts = contracts
    
    def generate_agents_yaml(self, output_path: Path) -> Dict[str, Any]:
        """
        Generate agents.yaml registry file
        
        Args:
            output_path: Path to write agents.yaml
            
        Returns:
            Generated agents configuration
        """
        print(f"📝 Generating agents.yaml...")
        
        agents_config = {
            "version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat(),
            "agents": {}
        }
        
        for agent_name, contract in self.contracts.items():
            metadata = self.agents_metadata.get(agent_name)
            
            agent_entry = {
                "id": agent_name,
                "version": contract.get("version", "1.0.0"),
                "description": contract.get("description", ""),
                "entrypoint": {
                    "type": "python",
                    "module": "agents",
                    "function": agent_name,
                    "async": metadata.is_async if metadata else False
                },
                "contract": {
                    "inputs": contract.get("inputs", {}),
                    "outputs": contract.get("outputs", {}),
                    "checkpoints": contract.get("checkpoints", [])
                },
                "capabilities": contract.get("capabilities", {}),
                "resources": contract.get("resources", {}),
                "cache": self._generate_cache_config(agent_name, metadata)
            }
            
            # Add dependencies if any
            if metadata and metadata.dependencies:
                agent_entry["dependencies"] = metadata.dependencies
            
            agents_config["agents"][agent_name] = agent_entry
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            yaml.dump(
                agents_config, 
                f, 
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        
        print(f"✓ Generated {output_path} with {len(agents_config['agents'])} agents")
        return agents_config
    
    def _generate_cache_config(self, agent_name: str, metadata: Any) -> Dict[str, Any]:
        """Generate cache configuration for an agent"""
        if not metadata:
            return {"enabled": False}
        
        cacheable = metadata.inferred_capabilities.get("cacheable", False)
        
        if not cacheable:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "namespace": f"agent_{agent_name}",
            "key_template": "{agent_id}:{model_id}:{input_hash}",
            "ttl_seconds": 86400,  # 1 day default
            "stale_while_revalidate": True
        }
    
    def generate_workflows_yaml(
        self, 
        output_path: Path,
        templates: List[WorkflowTemplate] = None
    ) -> Dict[str, Any]:
        """
        Generate workflows.yaml with common blog generation workflows
        
        Args:
            output_path: Path to write workflows.yaml
            templates: Optional workflow templates to generate
            
        Returns:
            Generated workflows configuration
        """
        print(f"📝 Generating workflows.yaml...")
        
        if templates is None:
            templates = self._get_default_blog_workflows()
        
        workflows_config = {
            "version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat(),
            "workflows": {}
        }
        
        for template in templates:
            workflow = self._generate_workflow_from_template(template)
            workflows_config["workflows"][template.name] = workflow
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            yaml.dump(
                workflows_config,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        
        print(f"✓ Generated {output_path} with {len(workflows_config['workflows'])} workflows")
        return workflows_config
    
    def _get_default_blog_workflows(self) -> List[WorkflowTemplate]:
        """Get default blog generation workflow templates"""
        
        # Identify blog-related agents
        blog_agents = [
            name for name in self.agents_metadata.keys()
            if any(keyword in name.lower() for keyword in [
                'ingest', 'topic', 'outline', 'writer', 'section',
                'intro', 'content', 'seo', 'frontmatter', 'file'
            ])
        ]
        
        templates = [
            WorkflowTemplate(
                name="daily_blog_generation",
                description="Complete blog post generation pipeline",
                agents=self._order_blog_agents(blog_agents),
                trigger_type="schedule",
                schedule="0 2 * * *",  # 2 AM daily
                approval_gates=["outline_ready", "content_assembled"]
            ),
            WorkflowTemplate(
                name="single_blog_post",
                description="Generate a single blog post on demand",
                agents=self._order_blog_agents(blog_agents),
                trigger_type="manual",
                approval_gates=["content_assembled"]
            ),
            WorkflowTemplate(
                name="ingest_and_index",
                description="Ingest knowledge base and build index",
                agents=[a for a in blog_agents if 'ingest' in a.lower()],
                trigger_type="manual"
            )
        ]
        
        return templates
    
    def _order_blog_agents(self, agents: List[str]) -> List[str]:
        """
        Order blog agents in logical execution sequence
        Based on common blog generation pipeline
        """
        order_keywords = [
            'ingest_kb',
            'identify_topics',
            'topic_prep',
            'check_duplication',
            'create_outline',
            'introduction_writer',
            'section_writer',
            'content_assembly',
            'seo_metadata',
            'frontmatter',
            'write_file'
        ]
        
        ordered = []
        for keyword in order_keywords:
            matching = [a for a in agents if keyword in a.lower()]
            ordered.extend(matching)
        
        # Add any remaining agents
        for agent in agents:
            if agent not in ordered:
                ordered.append(agent)
        
        return ordered
    
    def _generate_workflow_from_template(self, template: WorkflowTemplate) -> Dict[str, Any]:
        """Generate workflow definition from template"""
        
        workflow = {
            "name": template.name,
            "version": "1.0.0",
            "description": template.description,
            "trigger": {
                "type": template.trigger_type
            },
            "steps": []
        }
        
        if template.schedule:
            workflow["trigger"]["schedule"] = template.schedule
        
        # Generate steps from agents
        for idx, agent_name in enumerate(template.agents):
            step = {
                "id": agent_name,
                "agent": agent_name,
                "params": self._get_default_params(agent_name),
                "inject": []
            }
            
            # Add approval gates at specific agents
            if template.approval_gates:
                checkpoint_name = self._get_checkpoint_after_agent(agent_name)
                if checkpoint_name in template.approval_gates:
                    step["inject"].append({
                        "use": "approval_gate",
                        "when": f"context.{checkpoint_name} == true",
                        "params": {
                            "message": f"Review required after {agent_name}"
                        }
                    })
            
            workflow["steps"].append(step)
        
        return workflow
    
    def _get_default_params(self, agent_name: str) -> Dict[str, Any]:
        """Get default parameters for an agent"""
        contract = self.contracts.get(agent_name, {})
        inputs = contract.get("inputs", {}).get("schema", {})
        properties = inputs.get("properties", {})
        
        params = {}
        for prop_name, prop_def in properties.items():
            if 'default' in prop_def:
                params[prop_name] = prop_def['default']
        
        return params
    
    def _get_checkpoint_after_agent(self, agent_name: str) -> str:
        """Get checkpoint name after agent execution"""
        # Common checkpoint patterns
        if 'outline' in agent_name.lower():
            return 'outline_ready'
        elif 'content' in agent_name.lower() or 'assembly' in agent_name.lower():
            return 'content_assembled'
        elif 'review' in agent_name.lower():
            return 'review_complete'
        else:
            return f"{agent_name}_complete"
    
    def generate_all(self, config_dir: Path) -> Dict[str, Path]:
        """
        Generate all YAML configuration files
        
        Args:
            config_dir: Directory to write all config files
            
        Returns:
            Dictionary of config_name -> file_path
        """
        print(f"\n🔧 Generating all configuration files in {config_dir}...")
        
        generated_files = {}
        
        # Generate agents.yaml
        agents_path = config_dir / "agents.yaml"
        self.generate_agents_yaml(agents_path)
        generated_files["agents"] = agents_path
        
        # Generate workflows.yaml
        workflows_path = config_dir / "workflows.yaml"
        self.generate_workflows_yaml(workflows_path)
        generated_files["workflows"] = workflows_path
        
        return generated_files


class WorkflowVisualizer:
    """Generates visual representations of workflows"""
    
    @staticmethod
    def generate_mermaid_diagram(workflow: Dict[str, Any]) -> str:
        """
        Generate Mermaid diagram for workflow visualization
        
        Args:
            workflow: Workflow definition
            
        Returns:
            Mermaid diagram as string
        """
        lines = ["```mermaid", "graph TD"]
        
        steps = workflow.get("steps", [])
        
        for idx, step in enumerate(steps):
            step_id = step["id"]
            agent_name = step["agent"]
            
            # Node definition
            lines.append(f"    {step_id}[{agent_name}]")
            
            # Connect to next step
            if idx < len(steps) - 1:
                next_step = steps[idx + 1]["id"]
                lines.append(f"    {step_id} --> {next_step}")
            
            # Add approval gates
            if step.get("inject"):
                for inject in step["inject"]:
                    if inject.get("use") == "approval_gate":
                        approval_id = f"{step_id}_approval"
                        lines.append(f"    {approval_id}{{Approval Required}}")
                        lines.append(f"    {step_id} --> {approval_id}")
                        if idx < len(steps) - 1:
                            next_step = steps[idx + 1]["id"]
                            lines.append(f"    {approval_id} --> {next_step}")
        
        lines.append("```")
        return "\n".join(lines)
    
    @staticmethod
    def generate_workflow_readme(
        workflow: Dict[str, Any],
        output_path: Path
    ):
        """
        Generate README documentation for a workflow
        
        Args:
            workflow: Workflow definition
            output_path: Path to write README.md
        """
        content = [
            f"# {workflow['name']}",
            "",
            f"**Description:** {workflow.get('description', 'No description')}",
            "",
            "## Trigger",
            f"- **Type:** {workflow['trigger']['type']}",
        ]
        
        if 'schedule' in workflow['trigger']:
            content.append(f"- **Schedule:** `{workflow['trigger']['schedule']}`")
        
        content.extend([
            "",
            "## Steps",
            ""
        ])
        
        for idx, step in enumerate(workflow.get("steps", []), 1):
            content.append(f"{idx}. **{step['agent']}**")
            
            if step.get("params"):
                content.append("   - Parameters:")
                for key, value in step["params"].items():
                    content.append(f"     - `{key}`: {value}")
            
            if step.get("inject"):
                content.append("   - Injection points:")
                for inject in step["inject"]:
                    content.append(f"     - {inject.get('use', 'unknown')}")
            
            content.append("")
        
        content.extend([
            "## Visualization",
            "",
            WorkflowVisualizer.generate_mermaid_diagram(workflow)
        ])
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write("\n".join(content))


# Example usage
if __name__ == "__main__":
    from pathlib import Path
    import json
    
    print("=" * 80)
    print("UCOP YAML Generator")
    print("=" * 80)
    
    # Load discovery report
    report_file = Path("discovery_report.json")
    if not report_file.exists():
        print("❌ discovery_report.json not found")
        print("   Run agent_scanner.py first!")
        exit(1)
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Extract agents and contracts
    agents_metadata = {}
    contracts = {}
    
    for agent_name, agent_data in report["agents"].items():
        from dataclasses import dataclass, field
        from typing import List, Dict, Any
        
        @dataclass
        class SimpleMeta:
            name: str
            is_async: bool
            parameters: List[Dict]
            inferred_capabilities: Dict[str, Any]
            inferred_checkpoints: List[Dict]
            dependencies: List[str]
        
        meta = SimpleMeta(
            name=agent_data["name"],
            is_async=agent_data["is_async"],
            parameters=agent_data["parameters"],
            inferred_capabilities=agent_data["capabilities"],
            inferred_checkpoints=agent_data["checkpoints"],
            dependencies=agent_data.get("dependencies", [])
        )
        agents_metadata[agent_name] = meta
        
        # Build contract
        contract = {
            "version": "1.0.0",
            "description": f"Agent: {agent_name}",
            "inputs": {
                "schema": {
                    "type": "object",
                    "properties": {p["name"]: {"type": "string"} for p in agent_data["parameters"]},
                    "required": [p["name"] for p in agent_data["parameters"] if p.get("required", False)]
                }
            },
            "outputs": {"schema": {"type": "object"}},
            "checkpoints": agent_data["checkpoints"],
            "capabilities": agent_data["capabilities"]
        }
        contracts[agent_name] = contract
    
    # Generate YAML files
    generator = YAMLGenerator(agents_metadata, contracts)
    config_dir = Path("config")
    
    generated = generator.generate_all(config_dir)
    
    print(f"\n✅ Generated {len(generated)} configuration files:")
    for name, path in generated.items():
        print(f"   - {name}: {path}")
    
    # Generate workflow documentation
    workflows_path = generated["workflows"]
    with open(workflows_path, 'r') as f:
        workflows_data = yaml.safe_load(f)
    
    docs_dir = Path("docs/workflows")
    for workflow_name, workflow_def in workflows_data["workflows"].items():
        readme_path = docs_dir / f"{workflow_name}.md"
        WorkflowVisualizer.generate_workflow_readme(workflow_def, readme_path)
        print(f"   - Documentation: {readme_path}")
    
    print("\n✅ All configuration files generated successfully!")