"""Custom exceptions for engine."""

class EngineError(Exception):
    """Base exception for engine errors."""
    pass

class IncompleteOutputError(EngineError):
    """Output failed completeness validation."""
    pass

class EmptyOutputError(EngineError):
    """Output is empty or trivial."""
    pass

class InputResolutionError(EngineError):
    """Failed to resolve input."""
    pass

class APIValidationError(EngineError):
    """API signature validation failed."""
    pass

class ContextMergeError(EngineError):
    """Context merging failed."""
    pass
# DOCGEN:LLM-FIRST@v4