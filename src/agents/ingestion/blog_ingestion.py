"""Blog Ingestion Agent - Ingests existing blog posts for context and duplication checking."""

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


class BlogIngestionAgent(SelfCorrectingAgent, Agent):

    """Ingests existing blog posts for context and duplication checking."""

    def __init__(self, config: Config, event_bus: EventBus, database_service: DatabaseService):

        self.database_service = database_service

        self.state_manager = IngestionStateManager(config.ingestion_state_file)  # NEW

        Agent.__init__(self, "BlogIngestionAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="BlogIngestionAgent",

            capabilities=["ingest_blog"],

            input_schema={"type": "object"},

            output_schema={"type": "object"},

            publishes=["blog_ingestion_complete"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("kb_article_loaded", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        blog_dir = self.config.blog_dir
        
        # Detect family from path
        detected_family = Config.detect_family_from_path(blog_dir)
        logger.info(f"Detected family from blog path: {detected_family} (path: {blog_dir})")

        logger.info(f"BlogIngestionAgent: Checking blog directory: {blog_dir}")
        logger.info(f"BlogIngestionAgent: Directory exists: {blog_dir.exists()}")
        logger.info(f"BlogIngestionAgent: Current working directory: {Path.cwd()}")
        logger.info(f"BlogIngestionAgent: Absolute blog path: {blog_dir.absolute()}")
        logger.info(f"BlogIngestionAgent: Blog path resolved: {blog_dir.resolve()}")

        # Additional diagnostic checks
        try:
            logger.info(f"BlogIngestionAgent: Blog path is_absolute: {blog_dir.is_absolute()}")
            logger.info(f"BlogIngestionAgent: Blog path parts: {blog_dir.parts}")
            if blog_dir.is_absolute():
                logger.info(f"BlogIngestionAgent: Blog drive: {blog_dir.drive}")
        except Exception as e:
            logger.warning(f"BlogIngestionAgent: Error during path diagnostics: {e}")
        if blog_dir.exists():
            logger.info(f"BlogIngestionAgent: Directory is readable: {blog_dir.is_dir()}")
            try:
                contents = list(blog_dir.iterdir())
                logger.info(f"BlogIngestionAgent: Directory contents count: {len(contents)}")
                md_files = list(blog_dir.rglob("*.md"))
                logger.info(f"BlogIngestionAgent: Found {len(md_files)} .md files total")
                index_files = [f for f in md_files if f.name.lower() == "index.md"]
                logger.info(f"BlogIngestionAgent: Found {len(index_files)} index.md files")
            except Exception as e:
                logger.error(f"BlogIngestionAgent: Error accessing directory: {e}")

        if not blog_dir.exists():
            logger.warning(f"Blog directory not found: {blog_dir}")
            return AgentEvent(
                event_type="blog_ingestion_complete",
                data={"status": "skipped", "reason": "directory_not_found"},
                source_agent=self.agent_id,
                correlation_id=event.correlation_id
            )

        # Find all markdown files

        all_md_files = list(blog_dir.rglob("*.md"))

        blog_files = [

            f for f in all_md_files

            if f.name.lower() == "index.md"  # Only English versions

        ]

        logger.info(f"Found {len(all_md_files)} total .md files, filtered to {len(blog_files)} index.md files")

        # NEW: Filter to only files that need ingestion

        files_to_ingest = [

            f for f in blog_files

            if self.state_manager.needs_ingestion(f, "blog")

        ]

        skipped_count = len(blog_files) - len(files_to_ingest)

        if skipped_count > 0:

            logger.info(f"Skipping {skipped_count} unchanged blog files")

        # Process only new/changed files

        total_chunks = 0

        for blog_file in files_to_ingest:

            try:

                content = read_file_with_fallback_encoding(blog_file)

                chunks = chunk_text(content, self.config.chunk_size, self.config.chunk_overlap)

                if chunks:

                    metadatas = [

                        {"source": "blog", "file": str(blog_file), "chunk_id": i}

                        for i in range(len(chunks))

                    ]

                    self.database_service.add_documents("blog", chunks, metadatas, family=detected_family)

                    self.state_manager.mark_ingested(blog_file, "blog", len(chunks))

                    total_chunks += len(chunks)

            except Exception as e:

                logger.error(f"Error ingesting {blog_file}: {e}")

                continue

        if files_to_ingest:

            logger.info(f"Ingested {len(files_to_ingest)} blog posts ({total_chunks} chunks, {skipped_count} skipped)")

        return AgentEvent(

            event_type="blog_ingestion_complete",

            data={

                "status": "complete",

                "files_count": len(files_to_ingest),

                "files_skipped": skipped_count,

                "chunks_count": total_chunks

            },

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

