"""Supplementary Content Agent - Generates supplementary content."""

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


class SupplementaryContentAgent(SelfCorrectingAgent, Agent):

    """Generates supplementary sections using templates."""

    def __init__(self, config: Config, event_bus: EventBus,

                 llm_service: LLMService, trends_service: TrendsService):

        self.llm_service = llm_service

        self.trends_service = trends_service

        Agent.__init__(self, "SupplementaryContentAgent", config, event_bus)

    def _create_contract(self) -> AgentContract:

        return AgentContract(

            agent_id="SupplementaryContentAgent",

            capabilities=["generate_supplementary"],

            input_schema={"type": "object", "required": ["content", "topic"]},

            output_schema={"type": "object", "required": ["supplementary"]},

            publishes=["supplementary_generated"]

        )

    def _subscribe_to_events(self):

        self.event_bus.subscribe("execute_generate_supplementary", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:

        content = event.data.get("content", "")

        topic = event.data.get("topic", {})

        if not content:

            raise ValueError("content is required but was missing or empty")

        topic_title = topic.get("title", "the topic")

        content_summary = content[:1500]

        supplementary = {}

        # Generate Prerequisites (like sample)

        try:

            prerequisites = self._generate_prerequisites(topic_title)

            supplementary["prerequisites"] = prerequisites

        except Exception as e:

            logger.error(f"Prerequisites generation failed: {e}")

        # Generate FAQ (improved)

        try:

            faq = self._generate_faq(topic_title, content_summary)

            supplementary["faq"] = faq

        except Exception as e:

            logger.error(f"FAQ generation failed: {e}")

            supplementary["faq"] = self._generate_default_faq(topic_title)

        # Generate Troubleshooting (improved)

        try:

            troubleshooting = self._generate_troubleshooting(topic_title, content_summary)

            supplementary["troubleshooting"] = troubleshooting

        except Exception as e:

            logger.error(f"Troubleshooting generation failed: {e}")

            supplementary["troubleshooting"] = self._generate_default_troubleshooting()

        # Generate Use Cases

        try:

            use_cases = self._generate_use_cases(topic_title, content_summary)

            supplementary["use_cases"] = use_cases

        except Exception as e:

            logger.error(f"Use cases generation failed: {e}")

        # Generate Best Practices (table format like sample)

        try:

            best_practices = self._generate_best_practices_table(topic_title, content_summary)

            supplementary["best_practices"] = best_practices

        except Exception as e:

            logger.error(f"Best practices generation failed: {e}")

        logger.info(f"Generated {len(supplementary)} supplementary sections")

        return AgentEvent(

            event_type="supplementary_generated",

            data={"supplementary": supplementary},

            source_agent=self.agent_id,

            correlation_id=event.correlation_id

        )

    def _generate_prerequisites(self, topic_title: str) -> str:

        """Generate prerequisites section with dynamic product family."""

        # Get the correct product name based on detected family

        family_name = self.config.FAMILY_NAME_MAP.get(

            self.config.family,

            f'Aspose.{self.config.family.title()}'

        )

        # Extract package name (e.g., "Words" from "Aspose.Words")

        package_name = family_name.replace('Aspose.', '')

        # Use template if available, otherwise use hardcoded format

        if hasattr(self.config, 'PREREQUISITES_TEMPLATE'):

            return self.config.PREREQUISITES_TEMPLATE.format(

                family_name=family_name,

                package_name=package_name

            )

        else:

            return f"""Before you start, ensure that your development environment is set up correctly:

    * Visual Studio 2019 or later

    * .NET 6.0+ or .NET Framework 4.6.2+

    * {family_name} for .NET installed (NuGet)

    ```shell

    PM> Install-Package Aspose.{package_name}

    ```"""

    def _generate_faq(self, topic_title: str, content_summary: str) -> str:

        """Generate FAQ section matching sample format."""

        prompt = f"""Generate 3-4 FAQ entries for {topic_title}. Use this exact format:

**Q: [Question]**

A: [Answer]

Focus on practical developer questions about {topic_title}. Keep answers concise and helpful.

Context: {content_summary[:500]}"""

        # Enhance with tone configuration

        if self.config.tone_config:

            prompt = build_section_prompt_enhancement(

                self.config.tone_config,

                'faq',

                prompt

            )

        try:

            faq = self.llm_service.generate(

                prompt=prompt,

                system_prompt="You are a technical documentation specialist. Generate practical FAQs.",

                json_mode=False,

                model=self.config.ollama_content_model

            )

            return faq.strip()

        except Exception:

            return self._generate_default_faq(topic_title)

    def _generate_best_practices_table(self, topic_title: str, content_summary: str) -> str:

        """Generate best practices table matching sample format."""

        prompt = f"""Generate a best practices table for {topic_title}. Use this EXACT format:

| Tip           | Do                           | Don't                    |

| ------------- | ---------------------------- | ------------------------ |

| [Category]    | [Positive recommendation]    | [What to avoid]          |

Generate 4-5 rows with practical, actionable advice. Keep entries concise.

Context: {content_summary[:500]}"""

        try:

            table = self.llm_service.generate(

                prompt=prompt,

                system_prompt="You are a technical documentation specialist. Create practical reference tables.",

                json_mode=False,

                model=self.config.ollama_content_model

            )

            return table.strip()

        except Exception:

            return self._generate_default_best_practices()

    def _generate_default_best_practices(self) -> str:

        """Generate default best practices table."""

        return """| Tip | Do | Don't |

| --- | --- | --- |

| Resource Management | Dispose objects properly using `using` statements | Leave resources open after use |

| Error Handling | Implement try-catch blocks for file operations | Ignore exceptions silently |

| Performance | Process files in batches when possible | Load all files into memory at once |

| Configuration | Store settings in configuration files | Hardcode values in source code |

| Testing | Test with various file types and sizes | Only test with sample files |"""

    def _generate_default_faq(self, topic_title: str) -> str:

        """Generate default FAQ when LLM fails."""

        return f"""**Q: What is {topic_title}?**

    A: {topic_title} is a feature that allows developers to efficiently process documents in .NET applications.

    **Q: What are the system requirements?**

    A: You need .NET 6.0+ or .NET Framework 4.6.2+ and the appropriate Aspose library installed via NuGet.

    **Q: Is this feature cross-platform?**

    A: Yes, it works on Windows, Linux, and macOS with .NET Core/.NET 5+.

    **Q: Where can I get more help?**

    A: Visit the official documentation or community forums for detailed guidance and support."""

    def _generate_default_troubleshooting(self) -> str:

        """Generate default troubleshooting section when LLM fails."""

        return """* **File Not Found Exception**: Ensure the file path is correct and the file exists.

    * Check file permissions

    * Use absolute paths when possible

    * **Out of Memory Error**: For large files, process in batches.

    * Increase heap size if needed

    * Consider streaming APIs for large documents

    * **License Validation Failed**: Verify your license is valid and properly loaded.

    * Check license file path

    * Ensure license is not expired

    * **Encoding Issues**: Specify the correct encoding when reading files.

    * Use UTF-8 encoding by default

    * Handle BOM (Byte Order Mark) appropriately"""

    def _generate_troubleshooting(self, topic_title: str, content_summary: str) -> str:

        """Generate troubleshooting section matching sample format."""

        prompt = f"""Generate a troubleshooting section for {topic_title}. Format as bullet points with sub-bullets:

    * **Issue Name**: Description

    * Solution 1

    * Solution 2

    Focus on common errors developers encounter. Generate 3-4 issues.

    Context: {content_summary[:500]}"""

        try:

            troubleshooting = self.llm_service.generate(

                prompt=prompt,

                system_prompt="You are a technical support specialist. Generate practical troubleshooting guidance.",

                json_mode=False,

                model=self.config.ollama_content_model

            )

            return troubleshooting.strip()

        except Exception as e:

            logger.error(f"Troubleshooting generation failed: {e}")

            return self._generate_default_troubleshooting()

    def _generate_use_cases(self, topic_title: str, content_summary: str) -> str:

        """Generate use cases section."""

        prompt = f"""Generate 3-5 real-world use cases for {topic_title}. Format as bullet points:

    * **Use Case Name**: Brief description of the scenario and benefits

    Focus on practical business applications.

    Context: {content_summary[:500]}"""

        try:

            use_cases = self.llm_service.generate(

                prompt=prompt,

                system_prompt="You are a solutions architect. Generate practical business use cases.",

                json_mode=False,

                model=self.config.ollama_content_model

            )

            return use_cases.strip()

        except Exception:

            return f"""* **Document Automation**: Streamline document processing workflows

    * **Report Generation**: Automatically create formatted reports from data

    * **Batch Processing**: Process multiple documents efficiently

    * **Format Conversion**: Convert between different file formats

    * **Data Extraction**: Extract structured data from documents"""

