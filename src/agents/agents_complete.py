"""Complete agents module - aggregates all agents for testing."""

# Research agents
from src.agents.research.topic_identification import TopicIdentificationAgent
from src.agents.research.kb_search import KBSearchAgent
from src.agents.research.blog_search import BlogSearchAgent
from src.agents.research.api_search import APISearchAgent
from src.agents.research.duplication_check import DuplicationCheckAgent

# Code agents
from src.agents.code.code_validation import CodeValidationAgent
from src.agents.code.code_splitting import CodeSplittingAgent
from src.agents.code.license_injection import LicenseInjectionAgent
from src.agents.code.code_generation import CodeGenerationAgent
from src.agents.code.code_extraction import CodeExtractionAgent

# Ingestion agents
from src.agents.ingestion.blog_ingestion import BlogIngestionAgent
from src.agents.ingestion.kb_ingestion import KBIngestionAgent
from src.agents.ingestion.api_ingestion import APIIngestionAgent

# Content agents
from src.agents.content.supplementary_content import SupplementaryContentAgent
from src.agents.content.introduction_writer import IntroductionWriterAgent
from src.agents.content.section_writer import SectionWriterAgent
from src.agents.content.outline_creation import OutlineCreationAgent
from src.agents.content.content_assembly import ContentAssemblyAgent
from src.agents.content.conclusion_writer import ConclusionWriterAgent

# Publishing agents
from src.agents.publishing.link_validation import LinkValidationAgent
from src.agents.publishing.gist_upload import GistUploadAgent
from src.agents.publishing.gist_readme import GistReadmeAgent
from src.agents.publishing.file_writer import FileWriterAgent
from src.agents.publishing.frontmatter_enhanced import FrontmatterAgent

# Support agents
from src.agents.support.model_selection import ModelSelectionAgent
from src.agents.support.error_recovery import ErrorRecoveryAgent

# SEO agents
from src.agents.seo.keyword_extraction import KeywordExtractionAgent
from src.agents.seo.keyword_injection import KeywordInjectionAgent
from src.agents.seo.seo_metadata import SEOMetadataAgent

__all__ = [
    # Research
    'TopicIdentificationAgent',
    'KBSearchAgent',
    'BlogSearchAgent',
    'APISearchAgent',
    'DuplicationCheckAgent',
    # Code
    'CodeValidationAgent',
    'CodeSplittingAgent',
    'LicenseInjectionAgent',
    'CodeGenerationAgent',
    'CodeExtractionAgent',
    # Ingestion
    'BlogIngestionAgent',
    'KBIngestionAgent',
    'APIIngestionAgent',
    # Content
    'SupplementaryContentAgent',
    'IntroductionWriterAgent',
    'SectionWriterAgent',
    'OutlineCreationAgent',
    'ContentAssemblyAgent',
    'ConclusionWriterAgent',
    # Publishing
    'LinkValidationAgent',
    'GistUploadAgent',
    'GistReadmeAgent',
    'FileWriterAgent',
    'FrontmatterAgent',
    # Support
    'ModelSelectionAgent',
    'ErrorRecoveryAgent',
    # SEO
    'KeywordExtractionAgent',
    'KeywordInjectionAgent',
    'SEOMetadataAgent',
]
# DOCGEN:LLM-FIRST@v4