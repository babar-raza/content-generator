"""KB Ingestion Agent - Ingests Knowledge Base articles and creates embeddings."""

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


class KBIngestionAgent(SelfCorrectingAgent, Agent):

    """Ingests Knowledge Base article and creates embeddings."""

    def __init__(self, config: Config, event_bus: EventBus,

                 database_service: DatabaseService, embedding_service: EmbeddingService):

        self.database_service = database_service

        self.embedding_service = embedding_service

        self.state_manager = IngestionStateManager(config.ingestion_state_file)  # NEW

        Agent.__init__(self, "KBIngestionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="KBIngestionAgent",

            capabilities=["ingest_kb"],

            input_schema={"type": "object", "required": ["kb_path"]},

            output_schema={"type": "object", "required": ["kb_article_content", "kb_meta"]},

            publishes=["kb_article_loaded"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_ingest_kb", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        kb_path_str = event.data.get("kb_path")

        if not kb_path_str:

            raise ValueError("kb_path is required but was None or empty")

        kb_path = Path(kb_path_str)

        if not kb_path.exists():

            raise FileNotFoundError(f"KB path not found: {kb_path}")

        # Determine files to process

        if kb_path.is_file():

            kb_files = [kb_path]

        elif kb_path.is_dir():

            kb_files = [

                f for f in kb_path.rglob("*.md")

                if f.name.lower() != "_index.md"

            ]

            if not kb_files:

                raise FileNotFoundError(f"No markdown files found in: {kb_path}")

        else:

            raise ValueError(f"KB path must be a file or directory: {kb_path}")

        # NEW: Filter to only files that need ingestion

        files_to_ingest = [

            f for f in kb_files

            if self.state_manager.needs_ingestion(f, "kb")

        ]

        skipped_count = len(kb_files) - len(files_to_ingest)

        if skipped_count > 0:

            logger.info(f"Skipping {skipped_count} unchanged KB files")

        min_len = getattr(self.config, "min_kb_chars", 100)

        if not files_to_ingest:

            logger.info("All KB files already up-to-date, reading cached content")

            # READ actual content from cached files

            all_content = []

            for kb_file in kb_files:

                try:

                    content = read_file_with_fallback_encoding(kb_file)

                    if len(content.strip()) >= min_len:

                        all_content.append(content)

                except Exception as e:

                    logger.error(f"Error reading cached file {kb_file}: {e}")

                    continue

            if not all_content:

                raise ValueError(f"No valid content found in cached KB files at: {kb_path}")

            combined_content = "\n\n---\n\n".join(all_content)

            stats = self.state_manager.get_collection_stats("kb")

            return AgentEvent(

                event_type="kb_article_loaded",

                data={

                    "kb_article_content": combined_content,

                    "kb_meta": {

                        "filename": kb_path.name if kb_path.is_file() else kb_path.stem,

                        "path": str(kb_path),

                        "is_directory": kb_path.is_dir(),

                        "files_processed": 0,

                        "files_skipped": len(kb_files),

                        "total_cached_chunks": stats['total_chunks'],

                        "content_source": "cached_files_reread"

                    }

                },

                source_agent=self.agent_id,

                correlation_id=event.correlation_id

            )

        # KILO: ingestion accounting and explicit failure reason

        valid_count = 0

        for kb_file in files_to_ingest:

            try:

                content = read_file_with_fallback_encoding(kb_file)

                if len(content.strip()) < min_len:

                    logger.warning(f"Skipping short file: {kb_file} ({len(content)} < {min_len})")

                    continue

                valid_count += 1

                # Chunk content

                chunks = chunk_text(content, self.config.chunk_size, self.config.chunk_overlap)

                # Create metadata for each chunk

                metadatas = [

                    {

                        "source": "kb",

                        "file": str(kb_file),

                        "chunk_id": i

                    }

                    for i in range(len(chunks))

                ]

                # Add to database

                self.database_service.add_documents("kb", chunks, metadatas)

                # NEW: Mark as ingested

                self.state_manager.mark_ingested(kb_file, "kb", len(chunks))

            except Exception as e:

                logger.error(f"Error processing {kb_file}: {e}", exc_info=True)

                continue

        logger.info(

            f"Ingestion summary: total={len(kb_files)} to_ingest={len(files_to_ingest)} "

            f"valid={valid_count} skipped_short={len(files_to_ingest)-valid_count} "

            f"skipped_unchanged={skipped_count}"

        )

        # FIX: Build all_content from ALL kb_files (newly ingested + previously cached)

        all_content = []

        for kb_file in kb_files:

            try:

                content = read_file_with_fallback_encoding(kb_file)

                if len(content.strip()) >= min_len:

                    all_content.append(content)

            except Exception as e:

                logger.error(f"Error reading file {kb_file}: {e}")

                continue

        if valid_count == 0:

            # Fail fast with a precise reason so planner logs are meaningful

            if not kb_files:

                raise FileNotFoundError(f"No markdown files found in: {kb_path}")

            raise ValueError(

                f"No valid content found to ingest in: {kb_path} "

                f"(min_len={min_len}, files_to_ingest={len(files_to_ingest)})"

            )

        if not all_content:

            raise ValueError(f"No valid content could be read from KB files at: {kb_path}")

        # Combine all content for the article

        combined_content = "\n\n---\n\n".join(all_content)

        # Extract metadata

        kb_meta = {

            "filename": kb_path.name if kb_path.is_file() else kb_path.stem,

            "path": str(kb_path),

            "is_directory": kb_path.is_dir(),

            "files_processed": len(files_to_ingest),

            "files_skipped": skipped_count,

            "total_size": len(combined_content)

        }

        logger.info(f"Ingested {len(files_to_ingest)} KB files ({skipped_count} skipped)")

        return AgentEvent(

            event_type="kb_article_loaded",

            data={

                "kb_article_content": combined_content,

                "kb_meta": kb_meta

            },

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

