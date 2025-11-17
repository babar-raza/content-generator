"""Execution Plan Data Structures for Workflow Compilation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class StepStatus(Enum):
    """Status of an execution step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionStep:
    """Represents a single step in the execution plan."""
    
    agent_id: str
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[Dict[str, Any]] = None
    timeout: int = 300
    retry: int = 3
    parallel_group: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        """Make step hashable for use in sets."""
        return hash(self.agent_id)
    
    def __eq__(self, other: object) -> bool:
        """Check equality based on agent_id."""
        if not isinstance(other, ExecutionStep):
            return False
        return self.agent_id == other.agent_id
    
    def has_dependencies(self) -> bool:
        """Check if step has any dependencies."""
        return len(self.dependencies) > 0
    
    def can_run_parallel_with(self, other: 'ExecutionStep') -> bool:
        """Check if this step can run in parallel with another."""
        # Can run in parallel if neither depends on the other
        return (
            self.agent_id not in other.dependencies and
            other.agent_id not in self.dependencies
        )
    
    def evaluate_condition(self, context: Dict[str, Any]) -> bool:
        """Evaluate if this step should run based on condition.
        
        Args:
            context: Execution context with state and outputs
            
        Returns:
            True if step should run, False otherwise
        """
        if not self.condition:
            return True
        
        condition_type = self.condition.get('type')
        
        if condition_type == 'if':
            # Run if specified key exists and is truthy
            key = self.condition.get('key')
            return bool(context.get(key))
        
        elif condition_type == 'unless':
            # Run unless specified key exists and is truthy
            key = self.condition.get('key')
            return not bool(context.get(key))
        
        elif condition_type == 'requires':
            # Run if all required keys exist
            required = self.condition.get('keys', [])
            return all(key in context for key in required)
        
        # Default: run the step
        return True


@dataclass
class ExecutionPlan:
    """Complete execution plan for a workflow."""
    
    workflow_id: str
    steps: List[ExecutionStep] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_step(self, agent_id: str) -> Optional[ExecutionStep]:
        """Get a step by agent ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            ExecutionStep if found, None otherwise
        """
        for step in self.steps:
            if step.agent_id == agent_id:
                return step
        return None
    
    def get_dependencies(self, agent_id: str) -> List[str]:
        """Get dependencies for a specific step.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            List of agent IDs this step depends on
        """
        step = self.get_step(agent_id)
        return step.dependencies if step else []
    
    def get_execution_order(self) -> List[str]:
        """Get steps in execution order (topologically sorted).
        
        Returns:
            List of agent IDs in execution order
        """
        return [step.agent_id for step in self.steps]
    
    def get_parallel_group(self, group_index: int) -> List[str]:
        """Get agents in a specific parallel group.
        
        Args:
            group_index: Index of the parallel group
            
        Returns:
            List of agent IDs in the group
        """
        if 0 <= group_index < len(self.parallel_groups):
            return self.parallel_groups[group_index]
        return []
    
    def get_initial_steps(self) -> List[str]:
        """Get steps that can run immediately (no dependencies).
        
        Returns:
            List of agent IDs with no dependencies
        """
        return [step.agent_id for step in self.steps if not step.dependencies]
    
    def get_next_steps(self, completed: List[str]) -> List[str]:
        """Get steps that can run after completed steps.
        
        Args:
            completed: List of completed agent IDs
            
        Returns:
            List of agent IDs ready to run
        """
        completed_set = set(completed)
        next_steps = []
        
        for step in self.steps:
            if step.agent_id in completed_set:
                continue
            
            # Check if all dependencies are completed
            if all(dep in completed_set for dep in step.dependencies):
                next_steps.append(step.agent_id)
        
        return next_steps
    
    def validate(self) -> List[str]:
        """Validate the execution plan.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check for duplicate steps
        agent_ids = [step.agent_id for step in self.steps]
        if len(agent_ids) != len(set(agent_ids)):
            errors.append("Duplicate agent IDs found in execution plan")
        
        # Check that all dependencies exist
        valid_ids = set(agent_ids)
        for step in self.steps:
            for dep in step.dependencies:
                if dep not in valid_ids:
                    errors.append(
                        f"Step {step.agent_id} depends on non-existent step {dep}"
                    )
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution plan to dictionary.
        
        Returns:
            Dictionary representation of the plan
        """
        return {
            'workflow_id': self.workflow_id,
            'steps': [
                {
                    'agent_id': step.agent_id,
                    'dependencies': step.dependencies,
                    'condition': step.condition,
                    'timeout': step.timeout,
                    'retry': step.retry,
                    'parallel_group': step.parallel_group,
                    'metadata': step.metadata
                }
                for step in self.steps
            ],
            'parallel_groups': self.parallel_groups,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionPlan':
        """Create execution plan from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ExecutionPlan instance
        """
        steps = [
            ExecutionStep(
                agent_id=step_data['agent_id'],
                dependencies=step_data.get('dependencies', []),
                condition=step_data.get('condition'),
                timeout=step_data.get('timeout', 300),
                retry=step_data.get('retry', 3),
                parallel_group=step_data.get('parallel_group'),
                metadata=step_data.get('metadata', {})
            )
            for step_data in data.get('steps', [])
        ]
        
        return cls(
            workflow_id=data['workflow_id'],
            steps=steps,
            parallel_groups=data.get('parallel_groups', []),
            metadata=data.get('metadata', {})
        )
# DOCGEN:LLM-FIRST@v4