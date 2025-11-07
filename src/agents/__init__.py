"""Agents package - Structured agent implementations.

This package contains all agent implementations organized by functional category:
- ingestion: Data ingestion agents (KB, Blog, API)
- research: Research and search agents  
- content: Content creation agents
- code: Code generation and processing agents
- seo: SEO optimization agents
- publishing: Publishing and file management agents
- support: Support and utility agents

All agents can be imported directly from this package or from their respective sub-packages.
"""

# Import all agents from sub-packages
from .ingestion import (
    KBIngestionAgent,
    BlogIngestionAgent,
    APIIngestionAgent,
)

from .research import (
    TopicIdentificationAgent,
    DuplicationCheckAgent,
    KBSearchAgent,
    BlogSearchAgent,
    APISearchAgent,
)

from .content import (
    OutlineCreationAgent,
    IntroductionWriterAgent,
    SectionWriterAgent,
    ConclusionWriterAgent,
    SupplementaryContentAgent,
    ContentAssemblyAgent,
)

from .code import (
    CodeGenerationAgent,
    CodeExtractionAgent,
    LicenseInjectionAgent,
    CodeValidationAgent,
    CodeSplittingAgent,
)

from .seo import (
    SEOMetadataAgent,
    KeywordExtractionAgent,
    KeywordInjectionAgent,
)

from .publishing import (
    GistREADMEAgent,
    LinkValidationAgent,
    GistUploadAgent,
    FrontmatterAgent,
    FileWriterAgent,
)

from .support import (
    ModelSelectionAgent,
    ErrorRecoveryAgent,
)

# Export all agents
__all__ = [
    # Ingestion (3)
    'KBIngestionAgent',
    'BlogIngestionAgent',
    'APIIngestionAgent',
    
    # Research (5)
    'TopicIdentificationAgent',
    'DuplicationCheckAgent',
    'KBSearchAgent',
    'BlogSearchAgent',
    'APISearchAgent',
    
    # Content (6)
    'OutlineCreationAgent',
    'IntroductionWriterAgent',
    'SectionWriterAgent',
    'ConclusionWriterAgent',
    'SupplementaryContentAgent',
    'ContentAssemblyAgent',
    
    # Code (5)
    'CodeGenerationAgent',
    'CodeExtractionAgent',
    'LicenseInjectionAgent',
    'CodeValidationAgent',
    'CodeSplittingAgent',
    
    # SEO (3)
    'SEOMetadataAgent',
    'KeywordExtractionAgent',
    'KeywordInjectionAgent',
    
    # Publishing (5)
    'GistREADMEAgent',
    'LinkValidationAgent',
    'GistUploadAgent',
    'FrontmatterAgent',
    'FileWriterAgent',
    
    # Support (2)
    'ModelSelectionAgent',
    'ErrorRecoveryAgent',
]

# Total: 29 agents
