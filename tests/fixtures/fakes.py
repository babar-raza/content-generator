from __future__ import annotations
from typing import Any, Dict, Optional
from types import SimpleNamespace

class FakeLLMService:
    """
    Test double for LLMService that returns deterministic JSON or text.
    The return type mimics LLMService.generate: a string (JSON when json_mode=True).
    """
    def __init__(self, mapping: Optional[Dict[str, Dict[str, Any]]] = None):
        self.mapping = mapping or {}

    def generate(self, prompt: str, system_prompt: str = "", json_mode: bool = False,
                 json_schema: Optional[Dict[str, Any]] = None, temperature: float = 0.1,
                 model: Optional[str] = None, provider: Optional[str] = "OLLAMA",
                 timeout: int = 30, task_context: Optional[Dict[str, Any]] = None,
                 agent_name: Optional[str] = None) -> str:
        # If an agent_name mapping exists, return that JSON; else return generic valid JSON or text.
        if json_mode:
            payload: Dict[str, Any] = {}
            # Try agent-specific mapping first
            if agent_name and agent_name in self.mapping:
                payload.update(self.mapping[agent_name])
            # Then satisfy schema 'required' if provided
            if json_schema and isinstance(json_schema, dict):
                req = json_schema.get("required") or []
                for key in req:
                    payload.setdefault(key, f"<mock-{key}>")
            return __import__("json").dumps(payload)
        # Non-JSON mode: return a simple string
        return "<mock-text>"

class DummyService(SimpleNamespace):
    """Generic placeholder for other services (db, embedding, gist, link checker, trends)."""
    pass
