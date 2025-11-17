# Extensibility Guide

## Creating Custom Agents

### 1. Create Agent File
```python
# src/agents/custom/my_agent.py
from src.agents.base import Agent

class MyCustomAgent(Agent):
    def execute(self, input_data):
        # Your logic here
        return {"output": "result"}
    
    @property
    def contract(self):
        return {
            "inputs": {
                "type": "object",
                "properties": {"input": {"type": "string"}}
            },
            "outputs": {
                "type": "object", 
                "properties": {"output": {"type": "string"}}
            }
        }
```

### 2. Register in Config
```yaml
# config/agents.yaml
agents:
  my_custom_agent:
    id: "my_custom_agent"
    entrypoint:
      type: "python"
      module: "agents.custom"
      function: "my_agent"
```

### 3. Use in Workflow
```yaml
# templates/workflows.yaml
my_workflow:
  steps:
    - my_custom_agent
```

## Creating Custom Workflows
See `templates/workflows.yaml` for examples.

## Adding New Templates
Add to `templates/` directory and update registry.
