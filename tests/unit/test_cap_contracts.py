"""
Minimal contract tests for capability verification.

These tests verify that the capability features exist and are properly exposed
without requiring complex setup or external dependencies.
"""

def test_code_generation_capability_contract():
    """Verify code generation capability contract exists."""
    # Verify that task type constants for code generation are defined
    from src.utils.model_helper import TaskType

    assert hasattr(TaskType, 'CODE_GENERATION'), "TaskType.CODE_GENERATION constant must exist"
    assert isinstance(TaskType.CODE_GENERATION, str), "TaskType.CODE_GENERATION must be a string"
    assert len(TaskType.CODE_GENERATION) > 0, "TaskType.CODE_GENERATION must not be empty"


def test_model_selection_capability_contract():
    """Verify model selection capability contract exists."""
    # Verify that model selection agent can be imported and has required interface
    from src.agents.support.model_selection import ModelSelectionAgent

    assert ModelSelectionAgent is not None, "ModelSelectionAgent class must be importable"
    # Verify it has the required execute method
    assert hasattr(ModelSelectionAgent, 'execute'), "ModelSelectionAgent must have execute method"
