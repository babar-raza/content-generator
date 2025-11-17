"""Multi-File Topic Discovery Agent - Discovers topics from multiple files in directories."""

from typing import Optional, Dict, List, Any
from pathlib import Path
import json
import logging

from ..base import (
    Agent, EventBus, AgentEvent, AgentContract, SelfCorrectingAgent,
    Config, LLMService, DatabaseService, EmbeddingService, GistService,
    LinkChecker, TrendsService, PROMPTS, SCHEMAS, CSHARP_LICENSE_HEADER,
    MarkdownDedup, read_file_with_fallback_encoding, chunk_text, 
    build_query, dedupe_context, insert_license, split_code_into_segments,
    validate_code_quality, validate_api_compliance, extract_keywords,
    inject_keywords_naturally, write_markdown_tree, create_frontmatter,
    create_gist_shortcode, create_code_block, extract_code_blocks,
    IngestionStateManager, build_section_prompt_enhancement,
    get_section_heading, is_section_enabled, logger
)


class MultiFileTopicDiscoveryAgent(SelfCorrectingAgent, Agent):
    """Discovers topics from multiple files in directories."""

    def __init__(self, config: Config, event_bus: EventBus, llm_service: LLMService):
        self.llm_service = llm_service
        Agent.__init__(self, "MultiFileTopicDiscoveryAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:
        return AgentContract(
            agent_id="MultiFileTopicDiscoveryAgent",
            capabilities=["discover_topics_multi_file"],
            input_schema={
                "type": "object",
                "properties": {
                    "kb_path": {"type": "string"},
                    "docs_path": {"type": "string"},
                    "max_topics": {"type": "integer"}
                }
            },
            output_schema={"type": "object", "required": ["topics"]},
            publishes=["topics_discovered"]
        )

    def _subscribe_to_events(self):
        self.event_bus.subscribe("execute_discover_topics", self.execute)

    def _identify_topics_from_content(self, content: str, source_file: Path) -> List[Dict[str, Any]]:
        """Identify topics from a single file's content."""
        if not content or len(content.strip()) < 100:
            return []

        try:
            prompt_template = PROMPTS.get("TOPIC_IDENTIFICATION", {
                "system": "You are a technical content specialist.",
                "user": "Identify topics from content: {kb_article_content}\n\nReturn JSON: {json_schema}"
            })

            user_prompt = prompt_template["user"].format(
                kb_article_content=content[:5000],  # Limit content length
                json_schema=json.dumps(SCHEMAS.get("topics_identified", {"type": "object"}), indent=2)
            )

            response = self.llm_service.generate(
                prompt=user_prompt,
                system_prompt=prompt_template["system"],
                json_mode=True,
                json_schema=SCHEMAS.get("topics_identified", {"type": "object"}),
                model=self.config.ollama_topic_model
            )

            topics_data = json.loads(response)
            
            # Add source file metadata to each topic
            topics = topics_data.get("topics", [])
            for topic in topics:
                if isinstance(topic, dict):
                    topic["source_file"] = str(source_file)
                    topic["source_type"] = "kb" if "kb" in str(source_file).lower() else "docs"
            
            return topics
        except Exception as e:
            logger.error(f"Error identifying topics from {source_file}: {e}")
            return []

    def _deduplicate(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate topics based on title similarity."""
        if not topics:
            return []

        unique_topics = []
        seen_titles = set()

        for topic in topics:
            if isinstance(topic, dict):
                title = topic.get("title", "").strip().lower()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    unique_topics.append(topic)
            elif isinstance(topic, str):
                title = topic.strip().lower()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    unique_topics.append({"title": topic, "description": ""})

        return unique_topics

    def _rank_topics(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank topics by estimated value/relevance."""
        # Simple ranking: prioritize topics with descriptions
        scored_topics = []
        
        for topic in topics:
            score = 0
            if isinstance(topic, dict):
                if topic.get("description"):
                    score += 2
                if topic.get("title"):
                    score += 1
                if topic.get("source_file"):
                    score += 1
                topic["_score"] = score
                scored_topics.append(topic)

        # Sort by score descending
        scored_topics.sort(key=lambda x: x.get("_score", 0), reverse=True)
        
        # Remove score field
        for topic in scored_topics:
            topic.pop("_score", None)

        return scored_topics

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        kb_path_str = event.data.get("kb_path")
        docs_path_str = event.data.get("docs_path")
        max_topics = event.data.get("max_topics", 50)

        all_topics = []
        files_processed = 0

        # Process KB directory
        if kb_path_str:
            kb_path = Path(kb_path_str)
            if kb_path.exists():
                if kb_path.is_file():
                    kb_files = [kb_path]
                elif kb_path.is_dir():
                    kb_files = list(kb_path.rglob("*.md"))
                else:
                    kb_files = []

                for kb_file in kb_files:
                    try:
                        content = read_file_with_fallback_encoding(kb_file)
                        topics = self._identify_topics_from_content(content, kb_file)
                        all_topics.extend(topics)
                        files_processed += 1
                    except Exception as e:
                        logger.error(f"Error processing KB file {kb_file}: {e}")
                        continue

        # Process docs directory
        if docs_path_str:
            docs_path = Path(docs_path_str)
            if docs_path.exists():
                if docs_path.is_file():
                    docs_files = [docs_path]
                elif docs_path.is_dir():
                    docs_files = list(docs_path.rglob("*.md"))
                else:
                    docs_files = []

                for docs_file in docs_files:
                    try:
                        content = read_file_with_fallback_encoding(docs_file)
                        topics = self._identify_topics_from_content(content, docs_file)
                        all_topics.extend(topics)
                        files_processed += 1
                    except Exception as e:
                        logger.error(f"Error processing docs file {docs_file}: {e}")
                        continue

        # Deduplicate topics
        unique_topics = self._deduplicate(all_topics)

        # Rank topics by value
        ranked_topics = self._rank_topics(unique_topics)

        # Limit to max_topics
        final_topics = ranked_topics[:max_topics]

        logger.info(
            f"Topic discovery complete: {files_processed} files processed, "
            f"{len(all_topics)} topics found, {len(unique_topics)} after dedup, "
            f"{len(final_topics)} returned"
        )

        return AgentEvent(
            event_type="topics_discovered",
            data={
                "topics": final_topics,
                "total_discovered": len(all_topics),
                "after_dedup": len(unique_topics),
                "files_processed": files_processed
            },
            source_agent=self.agent_id,
            correlation_id=event.correlation_id
        )
