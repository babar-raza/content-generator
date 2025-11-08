from __future__ import annotations
import json
import inspect
from pathlib import Path
import importlib
import types

import pytest

# Ensure src is importable
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from src.core.config import Config
from src.core.event_bus import EventBus
from src.core.contracts import AgentEvent

from tests.fixtures.fakes import FakeLLMService, DummyService

AGENTS = [
  {
    "module": "src.agents.research.topic_identification",
    "class": "TopicIdentificationAgent",
    "input_req": [
      "kb_article_content"
    ],
    "output_req": [],
    "publishes": [
      "topics_identified"
    ]
  },
  {
    "module": "src.agents.research.kb_search",
    "class": "KBSearchAgent",
    "input_req": [
      "query"
    ],
    "output_req": [
      "source",
      "context"
    ],
    "publishes": [
      "rag_complete"
    ]
  },
  {
    "module": "src.agents.research.blog_search",
    "class": "BlogSearchAgent",
    "input_req": [
      "query"
    ],
    "output_req": [
      "source",
      "context"
    ],
    "publishes": [
      "rag_complete"
    ]
  },
  {
    "module": "src.agents.research.api_search",
    "class": "APISearchAgent",
    "input_req": [
      "query"
    ],
    "output_req": [
      "source",
      "context"
    ],
    "publishes": [
      "rag_complete"
    ]
  },
  {
    "module": "src.agents.research.duplication_check",
    "class": "DuplicationCheckAgent",
    "input_req": [
      "topic_title",
      "topic_slug"
    ],
    "output_req": [],
    "publishes": [
      "topic_duplicate",
      "topic_approved"
    ]
  },
  {
    "module": "src.agents.code.code_validation",
    "class": "CodeValidationAgent",
    "input_req": [
      "code"
    ],
    "output_req": [],
    "publishes": [
      "code_validated",
      "code_invalid"
    ]
  },
  {
    "module": "src.agents.code.code_splitting",
    "class": "CodeSplittingAgent",
    "input_req": [
      "code"
    ],
    "output_req": [
      "segments"
    ],
    "publishes": [
      "code_split"
    ]
  },
  {
    "module": "src.agents.code.license_injection",
    "class": "LicenseInjectionAgent",
    "input_req": [
      "code"
    ],
    "output_req": [
      "code"
    ],
    "publishes": [
      "license_injected"
    ]
  },
  {
    "module": "src.agents.code.code_generation",
    "class": "CodeGenerationAgent",
    "input_req": [
      "topic",
      "context_api"
    ],
    "output_req": [
      "code_blocks"
    ],
    "publishes": [
      "code_generated"
    ]
  },
  {
    "module": "src.agents.code.code_extraction",
    "class": "CodeExtractionAgent",
    "input_req": [
      "content"
    ],
    "output_req": [],
    "publishes": [
      "code_extracted"
    ]
  },
  {
    "module": "src.agents.ingestion.blog_ingestion",
    "class": "BlogIngestionAgent",
    "input_req": [],
    "output_req": [],
    "publishes": [
      "blog_ingestion_complete"
    ]
  },
  {
    "module": "src.agents.ingestion.kb_ingestion",
    "class": "KBIngestionAgent",
    "input_req": [
      "kb_path"
    ],
    "output_req": [
      "kb_article_content",
      "kb_meta"
    ],
    "publishes": [
      "kb_article_loaded"
    ]
  },
  {
    "module": "src.agents.ingestion.api_ingestion",
    "class": "APIIngestionAgent",
    "input_req": [],
    "output_req": [],
    "publishes": [
      "api_ingestion_complete"
    ]
  },
  {
    "module": "src.agents.content.supplementary_content",
    "class": "SupplementaryContentAgent",
    "input_req": [
      "content",
      "topic"
    ],
    "output_req": [
      "supplementary"
    ],
    "publishes": [
      "supplementary_generated"
    ]
  },
  {
    "module": "src.agents.content.introduction_writer",
    "class": "IntroductionWriterAgent",
    "input_req": [
      "outline"
    ],
    "output_req": [
      "introduction"
    ],
    "publishes": [
      "introduction_written"
    ]
  },
  {
    "module": "src.agents.content.section_writer",
    "class": "SectionWriterAgent",
    "input_req": [
      "outline",
      "intro"
    ],
    "output_req": [
      "sections"
    ],
    "publishes": [
      "sections_written"
    ]
  },
  {
    "module": "src.agents.content.outline_creation",
    "class": "OutlineCreationAgent",
    "input_req": [
      "topic"
    ],
    "output_req": [],
    "publishes": [
      "outline_created"
    ]
  },
  {
    "module": "src.agents.content.content_assembly",
    "class": "ContentAssemblyAgent",
    "input_req": [
      "intro",
      "sections"
    ],
    "output_req": [
      "content"
    ],
    "publishes": [
      "content_generated"
    ]
  },
  {
    "module": "src.agents.content.conclusion_writer",
    "class": "ConclusionWriterAgent",
    "input_req": [
      "sections",
      "topic"
    ],
    "output_req": [
      "conclusion"
    ],
    "publishes": [
      "conclusion_written"
    ]
  },
  {
    "module": "src.agents.publishing.link_validation",
    "class": "LinkValidationAgent",
    "input_req": [
      "gist_urls"
    ],
    "output_req": [],
    "publishes": [
      "links_validated"
    ]
  },
  {
    "module": "src.agents.publishing.gist_upload",
    "class": "GistUploadAgent",
    "input_req": [
      "readme",
      "code",
      "topic_slug"
    ],
    "output_req": [],
    "publishes": [
      "gist_uploaded",
      "gist_failed"
    ]
  },
  {
    "module": "src.agents.publishing.gist_readme",
    "class": "GistREADMEAgent",
    "input_req": [
      "code",
      "metadata"
    ],
    "output_req": [
      "readme"
    ],
    "publishes": [
      "readme_generated"
    ]
  },
  {
    "module": "src.agents.publishing.file_writer",
    "class": "FileWriterAgent",
    "input_req": [
      "markdown",
      "slug"
    ],
    "output_req": [],
    "publishes": [
      "blog_post_complete"
    ]
  },
  {
    "module": "src.agents.publishing.frontmatter",
    "class": "FrontmatterAgent",
    "input_req": [
      "content",
      "seo_metadata"
    ],
    "output_req": [
      "markdown"
    ],
    "publishes": [
      "frontmatter_added"
    ]
  },
  {
    "module": "src.agents.support.model_selection",
    "class": "ModelSelectionAgent",
    "input_req": [
      "capability"
    ],
    "output_req": [],
    "publishes": [
      "model_selected"
    ]
  },
  {
    "module": "src.agents.support.error_recovery",
    "class": "ErrorRecoveryAgent",
    "input_req": [
      "agent_id",
      "required_capabilities"
    ],
    "output_req": [],
    "publishes": [
      "help_response"
    ]
  },
  {
    "module": "src.agents.seo.keyword_extraction",
    "class": "KeywordExtractionAgent",
    "input_req": [
      "content"
    ],
    "output_req": [],
    "publishes": [
      "keywords_extracted"
    ]
  },
  {
    "module": "src.agents.seo.keyword_injection",
    "class": "KeywordInjectionAgent",
    "input_req": [
      "content",
      "keywords"
    ],
    "output_req": [
      "content"
    ],
    "publishes": [
      "keywords_injected"
    ]
  },
  {
    "module": "src.agents.seo.seo_metadata",
    "class": "SEOMetadataAgent",
    "input_req": [
      "content"
    ],
    "output_req": [],
    "publishes": [
      "seo_generated"
    ]
  }
]

def instantiate_agent(agent_info):
    mod = importlib.import_module(agent_info["module"])
    AgentClass = getattr(mod, agent_info["class"])
    # Build default config
    cfg = Config()
    bus = EventBus()
    # Provide fakes for supported constructor params
    # Discover __init__ signature
    sig = inspect.signature(AgentClass.__init__)
    kwargs = {
        "config": cfg,
        "event_bus": bus,
        "llm_service": FakeLLMService(mapping={agent_info["class"]: {k: f"<mock-{k}>" for k in (agent_info.get("output_req") or [])}}),
        "trends_service": DummyService(get_trends=lambda *a, **k: {}),
        "db_service": DummyService(),
        "embedding_service": DummyService(),
        "gist_service": DummyService(),
        "link_checker": DummyService(),
    }
    # Filter kwargs to only those accepted
    filtered = {}
    for name, param in sig.parameters.items():
        if name == "self": continue
        if name in kwargs:
            filtered[name] = kwargs[name]
        elif param.default is inspect._empty:
            # If unknown required dependency, inject a DummyService
            filtered[name] = DummyService()
    agent = AgentClass(**filtered)
    return agent, cfg, bus

@pytest.mark.parametrize("agent_info", AGENTS, ids=[f'{a["class"]}' for a in AGENTS])
def test_contract_shapes(agent_info):
    agent, cfg, bus = instantiate_agent(agent_info)
    # Agents should expose a _create_contract method that returns an AgentContract
    assert hasattr(agent, "_create_contract"), "Agent must define _create_contract"
    contract = agent._create_contract()
    # Basic contract sanity
    assert contract.agent_id and isinstance(contract.agent_id, str)
    assert isinstance(contract.input_schema, dict)
    assert isinstance(contract.output_schema, dict)
    # Input/Output required keys as per source literal (if present in generated table)
    if agent_info.get("input_req"):
        for key in agent_info["input_req"]:
            assert key in contract.input_schema.get("required", [])
    if agent_info.get("output_req"):
        for key in agent_info["output_req"]:
            assert key in contract.output_schema.get("required", [])

@pytest.mark.parametrize("agent_info", AGENTS, ids=[f'{a["class"]}' for a in AGENTS])
def test_exec_returns_expected_event_on_ollama(agent_info):
    agent, cfg, bus = instantiate_agent(agent_info)
    contract = agent._create_contract()
    # Build minimal input data satisfying required fields
    input_req = contract.input_schema.get("required") or agent_info.get("input_req") or []
    data = {k: f"<mock-{k}-input>" for k in input_req}
    event = AgentEvent(event_type="test_input", data=data, source_agent="pytest", correlation_id="cid-123")
    # Execute; agents should handle missing optional data robustly
    result = agent.execute(event)
    assert isinstance(result, AgentEvent) or result is None
    if result is None:
        pytest.skip("Agent returned no event for minimal input (acceptable for preconditioned agents).")
    # If publishes list known, ensure event_type is consistent
    publishes = agent_info.get("publishes") or contract.publishes or []
    if publishes:
        assert result.event_type in publishes
    # Validate output keys if schema has required
    out_req = contract.output_schema.get("required") or agent_info.get("output_req") or []
    if out_req:
        for key in out_req:
            assert key in result.data, f"Missing required output key: {key}"
