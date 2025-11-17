# Initialization Module

## Overview

System initialization and bootstrapping logic.

## Components

### `integrated_init.py`
Integrated system initialization for all components.

```python
def initialize_system():
    """Initialize all system components"""
    load_config()
    initialize_llm_providers()
    initialize_vector_store()
    discover_agents()
    setup_logging()
    validate_environment()
```

## Initialization Sequence

1. **Load Configuration**
   - Read config files
   - Validate schemas
   - Apply environment overrides

2. **Initialize LLM Providers**
   - Check Ollama availability
   - Validate API keys
   - Test connections

3. **Initialize Storage**
   - Connect to vector store
   - Load embeddings model
   - Migrate database if needed

4. **Discover Agents**
   - Scan agent directories
   - Register agents
   - Build dependency graph

5. **Setup Logging**
   - Configure structured logging
   - Set log levels
   - Initialize log handlers

6. **Validate Environment**
   - Check dependencies
   - Verify file permissions
   - Test system resources

## Usage

### Automatic Initialization

Called automatically on system start:

```python
from src.initialization.integrated_init import initialize_system

initialize_system()
```

### Manual Initialization

For testing or custom setups:

```python
from src.initialization.integrated_init import (
    load_config,
    initialize_llm_providers,
    discover_agents
)

# Load config only
config = load_config('custom_config.yaml')

# Initialize specific components
initialize_llm_providers(config)
discover_agents(config)
```

## Environment Validation

Checks performed during initialization:

- ✓ Python version >= 3.8
- ✓ Required packages installed
- ✓ Config files present and valid
- ✓ At least one LLM provider available
- ✓ Write permissions in output directories
- ✓ Network connectivity (if needed)

## Error Handling

Initialization errors are handled gracefully:

```python
try:
    initialize_system()
except ConfigError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
except ConnectionError as e:
    print(f"Connection failed: {e}")
    print("Continuing with limited functionality...")
```

## Dependencies

- `src.core.config` - Configuration
- `src.orchestration` - Agent discovery
- `src.services` - Service initialization
- `structlog` - Logging
