"""Tutorial Ingestion Agent - Ingests tutorial content and creates embeddings."""

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


class TutorialIngestionAgent(SelfCorrectingAgent, Agent):

    """Ingests tutorial content and creates embeddings."""

    def __init__(self, config: Config, event_bus: EventBus,

                 database_service: DatabaseService, embedding_service: EmbeddingService):

        self.database_service = database_service

        self.embedding_service = embedding_service

        self.state_manager = IngestionStateManager(config.ingestion_state_file)

        Agent.__init__(self, "TutorialIngestionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="TutorialIngestionAgent",

            capabilities=["ingest_tutorial"],

            input_schema={"type": "object", "required": ["tutorial_path"]},

            output_schema={"type": "object", "required": ["tutorial_content", "tutorial_meta"]},

            publishes=["tutorial_loaded"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_ingest_tutorial", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        tutorial_path_str = event.data.get("tutorial_path")

        if not tutorial_path_str:

            raise ValueError("tutorial_path is required but was None or empty")

        tutorial_path = Path(tutorial_path_str)

        if not tutorial_path.exists():

            raise FileNotFoundError(f"Tutorial path not found: {tutorial_path}")

        # Determine files to process
        if tutorial_path.is_file():

            tutorial_files = [tutorial_path]

        elif tutorial_path.is_dir():

            tutorial_files = [
                f for f in tutorial_path.rglob("*.md")
                if f.name.lower() not in ["_index.md", "readme.md"]
            ]

            if not tutorial_files:

                raise FileNotFoundError(f"No markdown files found in: {tutorial_path}")

        else:

            raise ValueError(f"Tutorial path must be a file or directory: {tutorial_path}")

        # Filter to only files that need ingestion
        files_to_ingest = [
            f for f in tutorial_files
            if self.state_manager.needs_ingestion(f, "tutorial")
        ]

        skipped_count = len(tutorial_files) - len(files_to_ingest)

        if skipped_count > 0:

            logger.info(f"Skipping {skipped_count} unchanged tutorial files")

        min_len = getattr(self.config, "min_tutorial_chars", 100)

        if not files_to_ingest:

            logger.info("All tutorial files already up-to-date, reading cached content")

            # Read actual content from cached files
            all_content = []

            for tutorial_file in tutorial_files:

                try:

                    content = read_file_with_fallback_encoding(tutorial_file)

                    if len(content.strip()) >= min_len:

                        all_content.append(content)

                except Exception as e:

                    logger.error(f"Error reading cached file {tutorial_file}: {e}")

                    continue

            if not all_content:

                raise ValueError(f"No valid content found in cached tutorial files at: {tutorial_path}")

            combined_content = "\n\n---\n\n".join(all_content)

            stats = self.state_manager.get_collection_stats("tutorial")

            return AgentEvent(

                event_type="tutorial_loaded",

                data={

                    "tutorial_content": combined_content,

                    "tutorial_meta": {

                        "filename": tutorial_path.name if tutorial_path.is_file() else tutorial_path.stem,

                        "path": str(tutorial_path),

                        "is_directory": tutorial_path.is_dir(),

                        "files_processed": 0,

                        "files_skipped": len(tutorial_files),

                        "total_cached_chunks": stats['total_chunks'],

                        "content_source": "cached_files_reread"

                    }

                },

                source_agent=self.agent_id,

                correlation_id=event.correlation_id

            )

        # Process files for ingestion
        valid_count = 0

        for tutorial_file in files_to_ingest:

            try:

                content = read_file_with_fallback_encoding(tutorial_file)

                if len(content.strip()) < min_len:

                    logger.warning(f"Skipping short file: {tutorial_file} ({len(content)} < {min_len})")

                    continue

                valid_count += 1

                # Chunk content
                chunks = chunk_text(content, self.config.chunk_size, self.config.chunk_overlap)

                # Create metadata for each chunk
                metadatas = [
                    {
                        "source": "tutorial",
                        "file": str(tutorial_file),
                        "chunk_id": i
                    }
                    for i in range(len(chunks))
                ]

                # Add to database
                self.database_service.add_documents("tutorial", chunks, metadatas)

                # Mark as ingested
                self.state_manager.mark_ingested(tutorial_file, "tutorial", len(chunks))

            except Exception as e:

                logger.error(f"Error processing {tutorial_file}: {e}", exc_info=True)

                continue

        logger.info(
            f"Ingestion summary: total={len(tutorial_files)} to_ingest={len(files_to_ingest)} "
            f"valid={valid_count} skipped_short={len(files_to_ingest)-valid_count} "
            f"skipped_unchanged={skipped_count}"
        )

        # Build all_content from ALL tutorial_files
        all_content = []

        for tutorial_file in tutorial_files:

            try:

                content = read_file_with_fallback_encoding(tutorial_file)

                if len(content.strip()) >= min_len:

                    all_content.append(content)

            except Exception as e:

                logger.error(f"Error reading file {tutorial_file}: {e}")

                continue

        if valid_count == 0:

            if not tutorial_files:

                raise FileNotFoundError(f"No markdown files found in: {tutorial_path}")

            raise ValueError(
                f"No valid content found to ingest in: {tutorial_path} "
                f"(min_len={min_len}, files_to_ingest={len(files_to_ingest)})"
            )

        if not all_content:

            raise ValueError(f"No valid content could be read from tutorial files at: {tutorial_path}")

        # Combine all content
        combined_content = "\n\n---\n\n".join(all_content)

        # Extract metadata
        tutorial_meta = {
            "filename": tutorial_path.name if tutorial_path.is_file() else tutorial_path.stem,
            "path": str(tutorial_path),
            "is_directory": tutorial_path.is_dir(),
            "files_processed": len(files_to_ingest),
            "files_skipped": skipped_count,
            "total_size": len(combined_content)
        }

        logger.info(f"Ingested {len(files_to_ingest)} tutorial files ({skipped_count} skipped)")

        return AgentEvent(

            event_type="tutorial_loaded",

            data={

                "tutorial_content": combined_content,

                "tutorial_meta": tutorial_meta

            },

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )
