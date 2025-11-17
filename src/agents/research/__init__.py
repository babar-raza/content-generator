"""Research agents package.

Contains agents responsible for research and information gathering:
- Topic identification
- Duplication checking
- KB/Blog/API/Tutorial/Docs searching
- Trends research and keyword analysis
- Content intelligence and semantic analysis
- Competitor analysis and gap identification
"""

from .topic_identification import TopicIdentificationAgent
from .multi_file_topic_discovery import MultiFileTopicDiscoveryAgent
from .duplication_check import DuplicationCheckAgent
from .kb_search import KBSearchAgent
from .blog_search import BlogSearchAgent
from .api_search import APISearchAgent
from .tutorial_search import TutorialSearchAgent
from .docs_search import DocsSearchAgent
from .trends_research import TrendsResearchAgent
from .content_intelligence import ContentIntelligenceAgent
from .competitor_analysis import CompetitorAnalysisAgent

__all__ = [
    'TopicIdentificationAgent',
    'MultiFileTopicDiscoveryAgent',
    'DuplicationCheckAgent',
    'KBSearchAgent',
    'BlogSearchAgent',
    'APISearchAgent',
    'TutorialSearchAgent',
    'DocsSearchAgent',
    'TrendsResearchAgent',
    'ContentIntelligenceAgent',
    'CompetitorAnalysisAgent',
]
# DOCGEN:LLM-FIRST@v4