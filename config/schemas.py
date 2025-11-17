"""DOCGEN:LLM-FIRST@v2

Module overview
- Purpose: Defines JSON schemas for validating configuration files in the application, ensuring structured and type-safe configuration data for agents, performance settings, tone controls, and main pipeline definitions.
- Lifecycle: Imported by config.validator and other modules during configuration loading and validation processes.
- Collaborators: config.validator.ConfigValidator, config.validator.load_validated_config
- Key inputs: None (static schema definitions)
- Key outputs: Dictionary representations of JSON schemas for validation

Public API Catalog
| Symbol | Kind | Defined in | Purpose | Inputs | Outputs | Raises | Notes |
|-------:|:-----|:-----------|:--------|:-------|:--------|:-------|:------|
| AGENT_SCHEMA | Constant | config.schemas | JSON schema for agent configuration validation | None | Dict[str, Any] | None | Validates agent metadata, capabilities, and resources |
| PERF_SCHEMA | Constant | config.schemas | JSON schema for performance configuration validation | None | Dict[str, Any] | None | Defines validation rules for timeouts, limits, and batch settings |
| TONE_SCHEMA | Constant | config.schemas | JSON schema for tone and voice configuration validation | None | Dict[str, Any] | None | Validates POV, formality, and personality settings |
| MAIN_SCHEMA | Constant | config.schemas | JSON schema for main pipeline configuration validation | None | Dict[str, Any] | None | Validates pipeline steps, workflows, and dependencies |

Design notes
- Contracts & invariants: Schemas enforce required fields and type constraints as defined; no runtime invariants beyond JSON schema validation.
- Error surface: No exceptions raised; validation errors occur in consuming modules.
- Concurrency: No concurrency mechanisms; schemas are immutable constants.
- I/O & performance: No I/O operations; schemas are in-memory dictionaries with negligible performance impact.
- Configuration map: Maps configuration sections to structured validation rules (agents, performance, tone, main).
- External deps: None (pure Python dictionaries)
"""

AGENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["version", "agents"],
    "properties": {
        "version": {"type": "string"},
        "generated_at": {"type": "string"},
        "source": {"type": "string"},
        "agents": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "required": ["id", "version"],
                    "properties": {
                        "id": {"type": "string"},
                        "version": {"type": "string"},
                        "description": {"type": "string"},
                        "entrypoint": {"type": "object"},
                        "contract": {"type": "object"},
                        "capabilities": {"type": "object"},
                        "resources": {"type": "object"}
                    }
                }
            }
        }
    }
}

PERF_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["timeouts", "limits"],
    "properties": {
        "timeouts": {
            "type": "object",
            "required": ["agent_execution", "total_job"],
            "properties": {
                "agent_execution": {"type": "number", "minimum": 1},
                "total_job": {"type": "number", "minimum": 1},
                "rag_query": {"type": "number", "minimum": 1},
                "template_render": {"type": "number", "minimum": 1}
            }
        },
        "limits": {
            "type": "object",
            "required": ["max_tokens_per_agent", "max_retries"],
            "properties": {
                "max_tokens_per_agent": {"type": "integer", "minimum": 1},
                "max_steps": {"type": "integer", "minimum": 1},
                "max_retries": {"type": "integer", "minimum": 0},
                "max_context_size": {"type": "integer", "minimum": 1}
            }
        },
        "batch": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "batch_size": {"type": "integer", "minimum": 1},
                "max_parallel": {"type": "integer", "minimum": 1}
            }
        }
    }
}

TONE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["global_voice"],
    "properties": {
        "global_voice": {
            "type": "object",
            "required": ["pov", "formality"],
            "properties": {
                "pov": {"type": "string", "enum": ["first_person", "second_person", "third_person"]},
                "formality": {"type": "string", "enum": ["casual", "professional_conversational", "formal", "academic"]},
                "technical_depth": {"type": "string"},
                "personality": {"type": "string"}
            }
        },
        "section_controls": {"type": "object"}
    }
}

MAIN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["version", "pipeline"],
    "properties": {
        "version": {"type": "string"},
        "pipeline": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        },
        "workflows": {"type": "object"},
        "dependencies": {"type": "object"}
    }
}
# DOCGEN:LLM-FIRST@v4