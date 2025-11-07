"""Code agents package.

Contains agents responsible for code generation and processing:
- Code generation
- Code extraction
- License injection
- Code validation
- Code splitting
"""

from .code_generation import CodeGenerationAgent
from .code_extraction import CodeExtractionAgent
from .license_injection import LicenseInjectionAgent
from .code_validation import CodeValidationAgent
from .code_splitting import CodeSplittingAgent

__all__ = [
    'CodeGenerationAgent',
    'CodeExtractionAgent',
    'LicenseInjectionAgent',
    'CodeValidationAgent',
    'CodeSplittingAgent',
]
