# workflow.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import yaml

@dataclass
class WorkflowProfile:
    name: str
    order: List[str]
    skip: List[str] = field(default_factory=list)
    only: Optional[List[str]] = None
    disabled_agents: List[str] = field(default_factory=list)
    agent_overrides: Dict[str, str] = field(default_factory=dict)
    deterministic: Optional[bool] = None
    warnings_as_errors: Optional[bool] = None
    llm: Dict[str, float] = field(default_factory=dict)
    max_retries: Optional[int] = None

    def allowed_capabilities(self) -> List[str]:
        allowed = list(self.order)
        if self.only:
            only_set = set(self.only)
            allowed = [c for c in allowed if c in only_set]
        skip_set = set(self.skip)
        return [c for c in allowed if c not in skip_set]

@dataclass
class Workflow:
    profiles: Dict[str, WorkflowProfile]
    dependencies: Dict[str, List[str]]

    @classmethod
    def load(cls, path: Path) -> "Workflow":
        with open(path, 'r', encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        deps = data.get("dependencies", {})
        profiles = {}
        for name, p in (data.get("profiles") or {}).items():
            profiles[name] = WorkflowProfile(
                name=name,
                order=p.get("order", []),
                skip=p.get("skip", []) or [],
                only=p.get("only"),
                disabled_agents=p.get("disabled_agents", []) or [],
                agent_overrides=p.get("agent_overrides", {}) or {},
                deterministic=p.get("deterministic"),
                warnings_as_errors=p.get("warnings_as_errors"),
                llm=p.get("llm", {}) or {},
                max_retries=p.get("max_retries"),
            )
        return cls(profiles=profiles, dependencies=deps)

    def profile(self, name: str) -> WorkflowProfile:
        if name not in self.profiles:
            raise KeyError(f"Profile '{name}' not found in workflow.yaml")
        return self.profiles[name]
