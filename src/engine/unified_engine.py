"""Unified Engine - Single entry point for CLI and Web with complete parity."""

import json
import re
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


def convert_paths_to_strings(data: Any) -> Any:
    """Recursively convert Path objects to strings in nested data structures.
    
    Args:
        data: Data to convert (dict, list, or any value)
        
    Returns:
        Data with all Path objects converted to strings
    """
    if isinstance(data, Path):
        return str(data)
    elif isinstance(data, dict):
        return {key: convert_paths_to_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_paths_to_strings(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(convert_paths_to_strings(item) for item in data)
    else:
        return data


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class RunSpec:
    """Specification for a job run - used by both CLI and Web."""
    
    # Core inputs
    topic: Optional[str] = None
    template_name: str = "default_blog"
    
    # Context paths
    kb_path: Optional[str] = None
    docs_path: Optional[str] = None
    blog_path: Optional[str] = None
    api_path: Optional[str] = None
    tutorial_path: Optional[str] = None
    
    # Switches
    auto_topic: bool = False
    
    # Batch mode
    batch_topics: Optional[List[str]] = None
    
    # Output control
    output_dir: Path = field(default_factory=lambda: Path('./output'))
    
    def validate(self) -> List[str]:
        """Validate run spec.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Template is required
        if not self.template_name or self.template_name == "":
            errors.append("template_name is required")
        
        # Auto-topic validation: MUST have context
        if self.auto_topic:
            has_context = (
                self.kb_path or 
                self.docs_path or 
                self.blog_path or 
                self.api_path or 
                self.tutorial_path
            )
            if not has_context:
                errors.append("auto_topic=True requires at least one context source path specified")
        elif not self.topic:
            errors.append("Must provide topic when auto_topic=False")
        
        # Note: We don't validate path existence here - paths are validated and 
        # handled gracefully during ingestion. Non-existent paths are just skipped.
        
        return errors
    
    def generate_output_path(self, title: str) -> Path:
        """Generate output path with slug for blog template.
        
        Args:
            title: Title to use for generating path
            
        Returns:
            Path to output file
        """
        if self.template_name and self.template_name.startswith("blog"):
            slug = urlify(title)
            # Handle collisions
            base_path = self.output_dir / slug / "index.md"
            if base_path.exists():
                counter = 2
                while True:
                    slug_with_counter = f"{slug}-{counter}"
                    new_path = self.output_dir / slug_with_counter / "index.md"
                    if not new_path.exists():
                        return new_path
                    counter += 1
            return base_path
        else:
            # For non-blog templates, use sanitized filename
            safe_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            return self.output_dir / f"{safe_name}.md"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with Path objects converted to strings."""
        data = asdict(self)
        # Convert all Path objects to strings for JSON serialization
        return convert_paths_to_strings(data)


def urlify(text: str) -> str:
    """Convert text to URL-safe slug.
    
    Args:
        text: Text to convert
        
    Returns:
        URL-safe slug
    """
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    return text


@dataclass
class AgentStepLog:
    """Log for a single agent step."""
    agent_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with secret redaction and Path conversion."""
        data = asdict(self)
        
        # Redact secrets from input/output
        data['input_data'] = self._redact_secrets(data['input_data'])
        data['output_data'] = self._redact_secrets(data['output_data'])
        
        # Convert any Path objects to strings
        return convert_paths_to_strings(data)
    
    @staticmethod
    def _redact_secrets(data: Any) -> Any:
        """Redact secrets from data."""
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                if any(secret_key in key.lower() for secret_key in ['key', 'token', 'secret', 'password']):
                    redacted[key] = '***REDACTED***'
                else:
                    redacted[key] = AgentStepLog._redact_secrets(value)
            return redacted
        elif isinstance(data, list):
            return [AgentStepLog._redact_secrets(item) for item in data]
        else:
            return data


@dataclass
class JobResult:
    """Result of a job execution."""
    
    job_id: str
    status: JobStatus
    run_spec: RunSpec
    
    # Output
    output_path: Optional[Path] = None
    artifact_content: Optional[str] = None
    manifest_path: Optional[Path] = None
    
    # Execution details
    agent_logs: List[AgentStepLog] = field(default_factory=list)
    pipeline_order: List[str] = field(default_factory=list)
    
    # Metrics
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    
    # Errors
    error: Optional[str] = None
    partial_results: Dict[str, Any] = field(default_factory=dict)
    
    # Sources used (for RAG)
    sources_used: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with Path objects converted to strings."""
        data = {
            'job_id': self.job_id,
            'status': self.status.value,
            'run_spec': self.run_spec.to_dict(),
            'output_path': str(self.output_path) if self.output_path else None,
            'manifest_path': str(self.manifest_path) if self.manifest_path else None,
            'agent_logs': [log.to_dict() for log in self.agent_logs],
            'pipeline_order': self.pipeline_order,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'error': self.error,
            'partial_results': convert_paths_to_strings(self.partial_results),
            'sources_used': self.sources_used
        }
        return data


class UnifiedEngine:
    """Unified execution engine used by both CLI and Web."""
    
    def __init__(self):
        """Initialize engine with validated configs."""
        from config.validator import load_validated_config
        from src.core.template_registry import get_template_registry
        
        # Load and validate all configs at startup (fail-fast)
        self.config_snapshot = load_validated_config()
        self.template_registry = get_template_registry()
        
        # Extract individual configs for convenience
        self.agent_config = self.config_snapshot.agent_config
        self.perf_config = self.config_snapshot.perf_config
        self.tone_config = self.config_snapshot.tone_config
        self.main_config = self.config_snapshot.main_config
        self.merged_config = self.config_snapshot.merged_config
        
        print(f"[OK] Engine initialized")
        print(f"  Config hash: {self.config_snapshot.config_hash}")
        print(f"  Templates: {len(self.template_registry.list_templates())}")
        print(f"  Engine version: {self.config_snapshot.engine_version}")
    
    def generate_job(self, run_spec: RunSpec) -> JobResult:
        """Generate a job - single entry point for both CLI and Web.
        
        This is THE function that both CLI and Web call.
        
        Args:
            run_spec: Job specification
            
        Returns:
            JobResult with execution details
        """
        logger.info("="*80)
        logger.info("Starting new job")
        logger.info(f"  Template: {run_spec.template_name}")
        logger.info(f"  Topic: {run_spec.topic or '(auto-generate)'}")
        logger.info(f"  Auto-topic: {run_spec.auto_topic}")
        
        # Log context paths
        context_paths = []
        if run_spec.kb_path:
            context_paths.append(f"KB: {run_spec.kb_path}")
        if run_spec.docs_path:
            context_paths.append(f"Docs: {run_spec.docs_path}")
        if run_spec.blog_path:
            context_paths.append(f"Blog: {run_spec.blog_path}")
        if run_spec.api_path:
            context_paths.append(f"API: {run_spec.api_path}")
        if run_spec.tutorial_path:
            context_paths.append(f"Tutorial: {run_spec.tutorial_path}")
        
        if context_paths:
            logger.info(f"  Context sources: {', '.join(context_paths)}")
        else:
            logger.info("  Context sources: None")
        
        logger.info(f"  Output dir: {run_spec.output_dir}")
        
        # Validate run_spec
        logger.info("Validating run specification...")
        validation_errors = run_spec.validate()
        if validation_errors:
            logger.error(f"Validation failed with {len(validation_errors)} error(s):")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return JobResult(
                job_id=self._generate_job_id(run_spec),
                status=JobStatus.FAILED,
                run_spec=run_spec,
                error=f"Validation failed: {', '.join(validation_errors)}"
            )
        logger.info("✓ Validation passed")
        
        # Generate job ID
        job_id = self._generate_job_id(run_spec)
        logger.info(f"Job ID: {job_id}")
        
        # Create result
        result = JobResult(
            job_id=job_id,
            status=JobStatus.RUNNING,
            run_spec=run_spec,
            start_time=time.time()
        )
        
        try:
            # Execute pipeline
            logger.info("Executing agent pipeline...")
            self._execute_pipeline(result)
            logger.info("✓ Pipeline execution completed")
            
            # Write artifact (always, even on partial/failure)
            logger.info("Writing output artifact...")
            self._write_artifact(result)
            if result.output_path:
                logger.info(f"✓ Artifact written to: {result.output_path}")
            
            # Write manifest for reproducibility
            logger.info("Writing job manifest...")
            self._write_manifest(result)
            if result.manifest_path:
                logger.info(f"✓ Manifest written to: {result.manifest_path}")
            
            # Set final status
            if result.error:
                result.status = JobStatus.PARTIAL if result.partial_results else JobStatus.FAILED
                logger.warning(f"Job completed with errors: {result.error}")
            else:
                result.status = JobStatus.COMPLETED
                logger.info("✓ Job completed successfully")
            
        except Exception as e:
            result.error = str(e)
            result.status = JobStatus.FAILED
            logger.error(f"Job failed with exception: {e}", exc_info=True)
            
            # Still try to write partial artifact
            try:
                logger.info("Attempting to write partial artifact...")
                self._write_artifact(result)
            except Exception as e2:
                logger.error(f"Failed to write partial artifact: {e2}")
        
        finally:
            result.end_time = time.time()
            result.duration = result.end_time - result.start_time
            logger.info(f"Job duration: {result.duration:.2f}s")
            logger.info(f"Final status: {result.status.value}")
            logger.info("="*80)
        
        return result
    
    def _generate_job_id(self, run_spec: RunSpec) -> str:
        """Generate unique job ID."""
        content = f"{run_spec.topic}_{run_spec.template_name}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _execute_pipeline(self, result: JobResult) -> None:
        """Execute agent pipeline according to config/main.yaml.
        
        Args:
            result: JobResult to populate
        """
        from src.core.template_registry import get_template
        
        logger.info("Loading pipeline configuration...")
        
        # Get pipeline order from config
        workflows = self.agent_config.get('workflows', {})
        agents_def = self.agent_config.get('agents', {})
        
        # Determine which workflow to use (default or specified)
        workflow_name = 'default'  # Could be extended to use run_spec.workflow_name
        pipeline = workflows.get(workflow_name, {}).get('steps', [])
        
        if not pipeline:
            # Fallback: use all enabled agents
            pipeline = [name for name, cfg in agents_def.items() if cfg.get('enabled', True)]
            logger.warning("No workflow found, using all enabled agents")
        
        result.pipeline_order = pipeline
        logger.info(f"Pipeline agents ({len(pipeline)}): {', '.join(pipeline)}")
        
        # Execute each agent in order
        agent_context = {
            'topic': result.run_spec.topic,
            'template_name': result.run_spec.template_name,
            'tone': self.tone_config,
            'perf': self.perf_config
        }
        
        # Add context from paths (RAG ingestion would happen here)
        logger.info("Ingesting context sources...")
        successful_ingestions = 0
        
        if result.run_spec.kb_path:
            logger.info(f"  Ingesting KB from: {result.run_spec.kb_path}")
            kb_content = self._ingest_path(result.run_spec.kb_path)
            if kb_content.get('ingested'):
                agent_context['kb_content'] = kb_content
                result.sources_used.append(result.run_spec.kb_path)
                logger.info(f"    ✓ Ingested {kb_content.get('file_count', 0)} files, {kb_content.get('total_size', 0)} chars")
                successful_ingestions += 1
            else:
                logger.warning(f"    ⚠ Failed to ingest KB: {kb_content.get('error', 'Unknown error')}")
            
        if result.run_spec.docs_path:
            logger.info(f"  Ingesting Docs from: {result.run_spec.docs_path}")
            docs_content = self._ingest_path(result.run_spec.docs_path)
            if docs_content.get('ingested'):
                agent_context['docs_content'] = docs_content
                result.sources_used.append(result.run_spec.docs_path)
                logger.info(f"    ✓ Ingested {docs_content.get('file_count', 0)} files, {docs_content.get('total_size', 0)} chars")
                successful_ingestions += 1
            else:
                logger.warning(f"    ⚠ Failed to ingest Docs: {docs_content.get('error', 'Unknown error')}")
            
        if result.run_spec.blog_path:
            logger.info(f"  Ingesting Blog from: {result.run_spec.blog_path}")
            blog_content = self._ingest_path(result.run_spec.blog_path)
            if blog_content.get('ingested'):
                agent_context['blog_content'] = blog_content
                result.sources_used.append(result.run_spec.blog_path)
                logger.info(f"    ✓ Ingested {blog_content.get('file_count', 0)} files, {blog_content.get('total_size', 0)} chars")
                successful_ingestions += 1
            else:
                logger.warning(f"    ⚠ Failed to ingest Blog: {blog_content.get('error', 'Unknown error')}")
            
        if result.run_spec.api_path:
            logger.info(f"  Ingesting API from: {result.run_spec.api_path}")
            api_content = self._ingest_path(result.run_spec.api_path)
            if api_content.get('ingested'):
                agent_context['api_content'] = api_content
                result.sources_used.append(result.run_spec.api_path)
                logger.info(f"    ✓ Ingested {api_content.get('file_count', 0)} files, {api_content.get('total_size', 0)} chars")
                successful_ingestions += 1
            else:
                logger.warning(f"    ⚠ Failed to ingest API: {api_content.get('error', 'Unknown error')}")
            
        if result.run_spec.tutorial_path:
            logger.info(f"  Ingesting Tutorial from: {result.run_spec.tutorial_path}")
            tutorial_content = self._ingest_path(result.run_spec.tutorial_path)
            if tutorial_content.get('ingested'):
                agent_context['tutorial_content'] = tutorial_content
                result.sources_used.append(result.run_spec.tutorial_path)
                logger.info(f"    ✓ Ingested {tutorial_content.get('file_count', 0)} files, {tutorial_content.get('total_size', 0)} chars")
                successful_ingestions += 1
            else:
                logger.warning(f"    ⚠ Failed to ingest Tutorial: {tutorial_content.get('error', 'Unknown error')}")
        
        # Check if we have at least some valid content
        if successful_ingestions == 0:
            if result.run_spec.auto_topic:
                error_msg = "auto_topic=True but no context sources could be ingested successfully"
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                logger.warning("No context sources were successfully ingested")
        else:
            logger.info(f"Successfully ingested {successful_ingestions} context source(s)")
        
        # Auto topic generation if needed
        if result.run_spec.auto_topic and not result.run_spec.topic:
            logger.info("Auto-generating topic from context...")
            agent_context['topic'] = self._derive_topic_from_context(agent_context)
            result.run_spec.topic = agent_context['topic']
            logger.info(f"  Generated topic: {agent_context['topic']}")
        
        # Execute pipeline
        logger.info(f"Executing {len(pipeline)} agents in sequence...")
        for i, agent_name in enumerate(pipeline, 1):
            agent_def = agents_def.get(agent_name, {})
            
            # Skip if disabled
            if not agent_def.get('enabled', True):
                logger.info(f"  [{i}/{len(pipeline)}] Skipping disabled agent: {agent_name}")
                continue
            
            logger.info(f"  [{i}/{len(pipeline)}] Executing agent: {agent_name}")
            
            # Create agent log
            step_log = AgentStepLog(
                agent_name=agent_name,
                input_data=agent_context.copy(),
                output_data={},
                start_time=time.time()
            )
            
            try:
                # Execute agent (simplified - real implementation would call actual agent)
                output = self._execute_agent(agent_name, agent_context, agent_def)
                
                # Update context with output
                agent_context[agent_name] = output
                step_log.output_data = output
                
                # Store partial result
                result.partial_results[agent_name] = output
                
                logger.info(f"    ✓ Agent completed in {step_log.duration:.2f}s")
                
            except Exception as e:
                step_log.errors.append(str(e))
                result.error = f"Agent '{agent_name}' failed: {e}"
                logger.error(f"    ✗ Agent failed: {e}", exc_info=True)
                # Continue with partial results
            
            finally:
                step_log.end_time = time.time()
                step_log.duration = step_log.end_time - step_log.start_time
                result.agent_logs.append(step_log)
        
        # Store final context
        result.partial_results['final_context'] = agent_context
        logger.info(f"Pipeline execution completed with {len(result.partial_results)} partial results")
    
    def _execute_agent(self, agent_name: str, context: Dict[str, Any], agent_def: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single agent (stub - real implementation would call actual agent).
        
        Args:
            agent_name: Agent name
            context: Execution context
            agent_def: Agent definition from config
            
        Returns:
            Agent output
        """
        # Placeholder implementation
        # Real implementation would:
        # 1. Import the actual agent class
        # 2. Initialize with config
        # 3. Call agent.execute(context)
        # 4. Return agent output
        
        return {
            'agent': agent_name,
            'status': 'executed',
            'mock_output': f"Output from {agent_name}"
        }
    
    def _ingest_path(self, path: str) -> Dict[str, Any]:
        """Ingest content from path for RAG.
        
        Args:
            path: Path to ingest
            
        Returns:
            Ingested content with files and chunks
        """
        from pathlib import Path
        
        path_obj = Path(path)
        
        if not path_obj.exists():
            logger.warning(f"Path does not exist: {path}")
            return {
                'path': path,
                'ingested': False,
                'error': 'Path not found',
                'file_count': 0,
                'files': [],
                'content': ''
            }
        
        # Collect files
        files = []
        if path_obj.is_file():
            files = [path_obj]
        elif path_obj.is_dir():
            # Recursively find markdown files
            files = list(path_obj.rglob("*.md"))
            # Also include txt files
            files.extend(list(path_obj.rglob("*.txt")))
        
        # Read file contents
        contents = []
        file_info = []
        for file_path in files:
            try:
                # Try to read with UTF-8, fallback to other encodings
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try latin-1 as fallback
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                
                if content.strip():
                    contents.append(content)
                    file_info.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': len(content)
                    })
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
                continue
        
        # Combine all content
        combined_content = "\n\n---\n\n".join(contents)
        
        return {
            'path': path,
            'ingested': True,
            'file_count': len(file_info),
            'files': file_info,
            'content': combined_content,
            'total_size': len(combined_content)
        }
    
    def _derive_topic_from_context(self, context: Dict[str, Any]) -> str:
        """Derive topic from provided context.
        
        Args:
            context: Agent context
            
        Returns:
            Derived topic
        """
        # Placeholder - real implementation would use an agent
        return "Auto-derived Topic"
    
    def _write_artifact(self, result: JobResult) -> None:
        """Write artifact (success or partial with errors).
        
        Args:
            result: JobResult with execution details
        """
        from src.core.template_registry import get_template
        
        logger.info("Preparing to write artifact...")
        
        # Get template
        template = get_template(result.run_spec.template_name)
        
        if not template:
            error_msg = f"Template '{result.run_spec.template_name}' not found"
            logger.error(error_msg)
            result.error = error_msg
            return
        
        logger.info(f"  Using template: {template.name} (type: {template.type.value})")
        
        # Prepare output directory
        output_dir = result.run_spec.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"  Output directory: {output_dir}")
        
        # Get title for output path
        title = result.partial_results.get('title', result.run_spec.topic or 'untitled')
        logger.info(f"  Content title: {title}")
        
        # Use RunSpec.generate_output_path for proper slug handling and collision detection
        output_path = result.run_spec.generate_output_path(title)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result.output_path = output_path
        logger.info(f"  Output file: {output_path}")
        
        # Render template
        try:
            logger.info("  Rendering template with context...")
            # Build context from partial results
            template_context = result.partial_results.get('final_context', {})
            
            # Render
            content = template.render(template_context, strict=False)
            
            logger.info(f"  Rendered content: {len(content)} characters")
            
            # Add run summary at top
            run_summary = self._generate_run_summary(result)
            content = f"{run_summary}\n\n{content}"
            
            # If partial/failed, add errors section
            if result.error:
                errors_section = self._generate_errors_section(result)
                content = f"{content}\n\n{errors_section}"
            
            # Write artifact
            with open(output_path, 'w') as f:
                f.write(content)
            
            result.artifact_content = content
            
        except Exception as e:
            # Even template rendering failed - write minimal artifact
            minimal_content = self._generate_minimal_artifact(result, str(e))
            
            with open(output_path, 'w') as f:
                f.write(minimal_content)
            
            result.artifact_content = minimal_content
    
    def _write_manifest(self, result: JobResult) -> None:
        """Write run manifest for reproducibility.
        
        Args:
            result: JobResult
        """
        if not result.output_path:
            return
        
        manifest_path = result.output_path.parent / f'{result.output_path.stem}_manifest.json'
        
        manifest = {
            'job_id': result.job_id,
            'timestamp': datetime.now().isoformat(),
            'run_spec': result.run_spec.to_dict(),
            'template_name': result.run_spec.template_name,
            'pipeline_order': result.pipeline_order,
            'sources_used': result.sources_used,
            'config_snapshot': {
                'hash': self.config_snapshot.config_hash,
                'timestamp': self.config_snapshot.timestamp,
                'engine_version': self.config_snapshot.engine_version
            },
            'status': result.status.value,
            'duration': result.duration
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        result.manifest_path = manifest_path
    
    def _generate_run_summary(self, result: JobResult) -> str:
        """Generate run summary for artifact header.
        
        Args:
            result: JobResult
            
        Returns:
            Run summary as markdown
        """
        summary = [
            "---",
            f"# Run Summary",
            f"- Job ID: {result.job_id}",
            f"- Status: {result.status.value}",
            f"- Template: {result.run_spec.template_name}",
            f"- Duration: {result.duration:.2f}s",
            f"- Pipeline: {' → '.join(result.pipeline_order)}",
        ]
        
        if result.sources_used:
            summary.append(f"- Sources: {', '.join(result.sources_used)}")
        
        summary.append("---\n")
        
        return '\n'.join(summary)
    
    def _generate_errors_section(self, result: JobResult) -> str:
        """Generate errors section for partial artifacts.
        
        Args:
            result: JobResult
            
        Returns:
            Errors section as markdown
        """
        lines = [
            "## ⚠️ Execution Errors",
            "",
            f"This artifact was partially generated due to errors:",
            "",
            f"**Error:** {result.error}",
            ""
        ]
        
        # Add agent-specific errors
        for log in result.agent_logs:
            if log.errors:
                lines.append(f"**{log.agent_name}:**")
                for error in log.errors:
                    lines.append(f"- {error}")
                lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_minimal_artifact(self, result: JobResult, error: str) -> str:
        """Generate minimal artifact when all else fails.
        
        Args:
            result: JobResult
            error: Error message
            
        Returns:
            Minimal artifact content
        """
        lines = [
            f"# Job {result.job_id} - Failed",
            "",
            "## Error",
            "",
            f"{error}",
            "",
            "## Partial Results",
            ""
        ]
        
        for agent_name, output in result.partial_results.items():
            lines.append(f"### {agent_name}")
            lines.append(f"```json")
            lines.append(json.dumps(output, indent=2))
            lines.append(f"```")
            lines.append("")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-friendly slug.
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified text
        """
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
    
    @staticmethod
    def _hash_config(config: Dict[str, Any]) -> str:
        """Generate hash of config for reproducibility.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Config hash
        """
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]


# Global engine instance (singleton)
_engine_instance: Optional[UnifiedEngine] = None


def get_engine() -> UnifiedEngine:
    """Get global engine instance.
    
    Returns:
        UnifiedEngine instance
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = UnifiedEngine()
    return _engine_instance
