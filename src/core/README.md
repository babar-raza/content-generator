# Core Module

## Overview

Core abstractions, base classes, and fundamental utilities used throughout UCOP.

## Components

### `agent_base.py`
Base class for all agents with standard interfaces.

```python
class Agent:
    """Base agent with validation and error handling"""
    def execute(self, input_data: Dict) -> Dict
    def validate_input(self, input_data: Dict) -> bool
    def validate_output(self, output: Dict) -> bool
```

### `config.py`
Configuration management and validation.

```python
class Config:
    """System-wide configuration"""
    llm: LLMConfig
    workflows: WorkflowConfig
    vectorstore: VectorstoreConfig
```

### `config_validator.py`
Validates configuration files against schemas.

```python
class ConfigValidator:
    """Validates YAML configs"""
    def validate(self, config_path: str) -> ValidationResult
```

### `template_registry.py`
Manages content templates for blog posts, docs, etc.

```python
class TemplateRegistry:
    """Central template management"""
    def get_template(self, name: str) -> Template
    def register_template(self, name: str, template: Template)
```

### `router.py`
Routes requests to appropriate agents/workflows.

```python
class Router:
    """Intelligent request routing"""
    def route(self, request: Request) -> Agent
```

## Design Principles

1. **Single Responsibility**: Each class has one clear purpose
2. **Interface Segregation**: Minimal, focused interfaces
3. **Dependency Injection**: Components receive dependencies
4. **Fail-Safe Defaults**: Safe default behaviors

## Usage

```python
from src.core.config import load_config
from src.core.template_registry import TemplateRegistry

# Load configuration
config = load_config('config/main.yaml')

# Get template
registry = TemplateRegistry()
template = registry.get_template('blog_post')
```

## Dependencies

- `pyyaml` - YAML parsing
- `pydantic` - Data validation
- `structlog` - Structured logging
