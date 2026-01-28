"""API Ingestion Agent - Ingests API documentation and examples."""

from typing import Optional, Dict, List, Any
from pathlib import Path
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


class APIIngestionAgent(SelfCorrectingAgent, Agent):

    """Ingests API documentation for code generation context."""

    def __init__(self, config: Config, event_bus: EventBus, database_service: DatabaseService):

        self.database_service = database_service

        self.state_manager = IngestionStateManager(config.ingestion_state_file)  # NEW

        Agent.__init__(self, "APIIngestionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="APIIngestionAgent",

            capabilities=["ingest_api"],

            input_schema={"type": "object"},

            output_schema={"type": "object"},

            publishes=["api_ingestion_complete"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("blog_ingestion_complete", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        api_dir = self.config.api_dir

        logger.info(f"APIIngestionAgent: Checking API directory: {api_dir}")
        logger.info(f"APIIngestionAgent: Directory exists: {api_dir.exists()}")
        logger.info(f"APIIngestionAgent: Current working directory: {Path.cwd()}")
        logger.info(f"APIIngestionAgent: Absolute API path: {api_dir.absolute()}")
        logger.info(f"APIIngestionAgent: API path resolved: {api_dir.resolve()}")

        # Additional diagnostic checks
        try:
            logger.info(f"APIIngestionAgent: API path is_absolute: {api_dir.is_absolute()}")
            logger.info(f"APIIngestionAgent: API path parts: {api_dir.parts}")
            if api_dir.is_absolute():
                logger.info(f"APIIngestionAgent: API drive: {api_dir.drive}")
        except Exception as e:
            logger.warning(f"APIIngestionAgent: Error during path diagnostics: {e}")

        if api_dir.exists():
            logger.info(f"APIIngestionAgent: Directory is readable: {api_dir.is_dir()}")
            try:
                contents = list(api_dir.iterdir())
                logger.info(f"APIIngestionAgent: Directory contents count: {len(contents)}")
                md_files = list(api_dir.rglob("*.md"))
                logger.info(f"APIIngestionAgent: Found {len(md_files)} .md files total")
                txt_files = list(api_dir.rglob("*.txt"))
                logger.info(f"APIIngestionAgent: Found {len(txt_files)} .txt files total")
            except Exception as e:
                logger.error(f"APIIngestionAgent: Error accessing directory: {e}")

        if not api_dir.exists():

            logger.warning(f"API directory not found: {api_dir}")

            return AgentEvent(

                event_type="api_ingestion_complete",

                data={"status": "skipped", "reason": "directory_not_found"},

                source_agent=self.agent_id,

                correlation_id=event.correlation_id

            )

        # Find all API doc files

        api_files = list(api_dir.rglob("*.md")) + list(api_dir.rglob("*.txt"))

        # NEW: Filter to only files that need ingestion

        files_to_ingest = [

            f for f in api_files

            if self.state_manager.needs_ingestion(f, "api")

        ]

        skipped_count = len(api_files) - len(files_to_ingest)

        if skipped_count > 0:

            logger.info(f"Skipping {skipped_count} unchanged API files")

        total_chunks = 0

        processed_files = 0

        for api_file in files_to_ingest:

            try:

                content = read_file_with_fallback_encoding(api_file)

                chunks = chunk_text(content, self.config.chunk_size, self.config.chunk_overlap)

                if chunks:

                    metadatas = [

                        {"source": "api", "file": str(api_file), "chunk_id": i}

                        for i in range(len(chunks))

                    ]

                    self.database_service.add_documents(chunks, metadatas, collection_name="api_reference")

                    self.state_manager.mark_ingested(api_file, "api", len(chunks))

                    total_chunks += len(chunks)

                    processed_files += 1

            except Exception as e:

                logger.error(f"Error ingesting {api_file}: {e}")

                continue

        if files_to_ingest:

            logger.info(f"Ingested {processed_files} API docs ({total_chunks} chunks, {skipped_count} skipped)")

        return AgentEvent(

            event_type="api_ingestion_complete",

            data={

                "status": "complete",

                "files_count": len(files_to_ingest),

                "files_skipped": skipped_count,

                "chunks_count": total_chunks

            },

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

# ============================================================================

# TOPIC AGENTS (2)

# ============================================================================

