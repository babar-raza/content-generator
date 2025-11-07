"""Base agent functionality and common imports."""

from typing import Dict, List, Optional, Any, Tuple
import logging
import json
import subprocess
from pathlib import Path
import re
from contextlib import nullcontext

from src.core import Agent, EventBus
from src.core.contracts import AgentEvent, AgentContract
from src.utils.content_utils import MarkdownDedup
from src.utils.learning import SelfCorrectingAgent
from src.services.services import (
    LLMService, DatabaseService, EmbeddingService,
    GistService, LinkChecker, TrendsService
)
from src.core.config import Config, PROMPTS, SCHEMAS, CSHARP_LICENSE_HEADER
from src.utils.content_utils import (
    read_file_with_fallback_encoding, chunk_text, 
    build_query, dedupe_context, insert_license, split_code_into_segments,
    validate_code_quality, validate_api_compliance, extract_keywords,
    inject_keywords_naturally, write_markdown_tree, create_frontmatter,
    create_gist_shortcode, create_code_block, extract_code_blocks
)
from src.utils.tone_utils import (
    build_section_prompt_enhancement, get_section_heading, is_section_enabled
)

logger = logging.getLogger(__name__)

# Import IngestionStateManager if needed
try:
    from src.utils.content_utils import IngestionStateManager
except ImportError:
    IngestionStateManager = None

__all__ = [
    'Agent',
    'EventBus',
    'AgentEvent',
    'AgentContract',
    'SelfCorrectingAgent',
    'LLMService',
    'DatabaseService',
    'EmbeddingService',
    'GistService',
    'LinkChecker',
    'TrendsService',
    'Config',
    'PROMPTS',
    'SCHEMAS',
    'CSHARP_LICENSE_HEADER',
    'MarkdownDedup',
    'read_file_with_fallback_encoding',
    'chunk_text',
    'build_query',
    'dedupe_context',
    'insert_license',
    'split_code_into_segments',
    'validate_code_quality',
    'validate_api_compliance',
    'extract_keywords',
    'inject_keywords_naturally',
    'write_markdown_tree',
    'create_frontmatter',
    'create_gist_shortcode',
    'create_code_block',
    'extract_code_blocks',
    'IngestionStateManager',
    'build_section_prompt_enhancement',
    'get_section_heading',
    'is_section_enabled',
    'logger'
]
