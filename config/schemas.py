"""Configuration Schemas - Authoritative validation rules"""

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
