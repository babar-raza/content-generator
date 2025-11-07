"""Unified Engine - Single entry point for CLI and Web with complete parity."""

import json
import re
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from src.engine.slug_service import slugify


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
                errors.append("auto_topic=True requires at least one context source")
        elif not self.topic:
            errors.append("Must provide topic when auto_topic=False")
        
        # Validate paths exist if provided
        for path_attr in ['kb_path', 'docs_path', 'blog_path', 'api_path', 'tutorial_path']:
            path_value = getattr(self, path_attr)
            if path_value and not Path(path_value).exists():
                errors.append(f"{path_attr} does not exist: {path_value}")
        
        return errors
    
    def generate_output_path(self, title: str) -> Path:
        """Generate output path with slug for blog template.
        
        Args:
            title: Title to use for generating path
            
        Returns:
            Path to output file
        """
        if self.template_name and self.template_name.startswith("blog"):
            slug = slugify(title)
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
        """Convert to dictionary."""
        return asdict(self)



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
        """Convert to dictionary with secret redaction."""
        data = asdict(self)
        
        # Redact secrets from input/output
        data['input_data'] = self._redact_secrets(data['input_data'])
        data['output_data'] = self._redact_secrets(data['output_data'])
        
        return data
    
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
        """Convert to dictionary."""
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
            'partial_results': self.partial_results,
            'sources_used': self.sources_used
        }
        return data


class UnifiedEngine:
    """Unified execution engine used by both CLI and Web."""
    
    def __init__(self):
        """Initialize engine with validated configs."""
        from config import load_validated_config
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
        
        print(f"✓ Engine initialized")
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
        # Validate run_spec
        validation_errors = run_spec.validate()
        if validation_errors:
            return JobResult(
                job_id=self._generate_job_id(run_spec),
                status=JobStatus.FAILED,
                run_spec=run_spec,
                error=f"Validation failed: {', '.join(validation_errors)}"
            )
        
        # Generate job ID
        job_id = self._generate_job_id(run_spec)
        
        # Create result
        result = JobResult(
            job_id=job_id,
            status=JobStatus.RUNNING,
            run_spec=run_spec,
            start_time=time.time()
        )
        
        try:
            # Execute pipeline
            self._execute_pipeline(result)
            
            # Write artifact (always, even on partial/failure)
            self._write_artifact(result)
            
            # Write manifest for reproducibility
            self._write_manifest(result)
            
            # Set final status
            if result.error:
                result.status = JobStatus.PARTIAL if result.partial_results else JobStatus.FAILED
            else:
                result.status = JobStatus.COMPLETED
            
        except Exception as e:
            result.error = str(e)
            result.status = JobStatus.FAILED
            
            # Still try to write partial artifact
            try:
                self._write_artifact(result)
            except:
                pass
        
        finally:
            result.end_time = time.time()
            result.duration = result.end_time - result.start_time
        
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
        
        # Get pipeline order from config
        workflows = self.agent_config.get('workflows', {})
        agents_def = self.agent_config.get('agents', {})
        
        # Determine which workflow to use (default or specified)
        workflow_name = 'default'  # Could be extended to use run_spec.workflow_name
        pipeline = workflows.get(workflow_name, {}).get('steps', [])
        
        if not pipeline:
            # Fallback: use all enabled agents
            pipeline = [name for name, cfg in agents_def.items() if cfg.get('enabled', True)]
        
        result.pipeline_order = pipeline
        
        # Execute each agent in order
        agent_context = {
            'topic': result.run_spec.topic,
            'template_name': result.run_spec.template_name,
            'tone': self.tone_config,
            'perf': self.perf_config
        }
        
        # Add context from paths (RAG ingestion would happen here)
        if result.run_spec.kb_path:
            agent_context['kb_content'] = self._ingest_path(result.run_spec.kb_path)
            result.sources_used.append(result.run_spec.kb_path)
        if result.run_spec.docs_path:
            agent_context['docs_content'] = self._ingest_path(result.run_spec.docs_path)
            result.sources_used.append(result.run_spec.docs_path)
        if result.run_spec.blog_path:
            agent_context['blog_content'] = self._ingest_path(result.run_spec.blog_path)
            result.sources_used.append(result.run_spec.blog_path)
        if result.run_spec.api_path:
            agent_context['api_content'] = self._ingest_path(result.run_spec.api_path)
            result.sources_used.append(result.run_spec.api_path)
        if result.run_spec.tutorial_path:
            agent_context['tutorial_content'] = self._ingest_path(result.run_spec.tutorial_path)
            result.sources_used.append(result.run_spec.tutorial_path)
        
        # Auto topic generation if needed
        if result.run_spec.auto_topic and not result.run_spec.topic:
            agent_context['topic'] = self._derive_topic_from_context(agent_context)
            result.run_spec.topic = agent_context['topic']
        
        # Execute pipeline
        for agent_name in pipeline:
            agent_def = agents_def.get(agent_name, {})
            
            # Skip if disabled
            if not agent_def.get('enabled', True):
                continue
            
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
                
            except Exception as e:
                step_log.errors.append(str(e))
                result.error = f"Agent '{agent_name}' failed: {e}"
                # Continue with partial results
            
            finally:
                step_log.end_time = time.time()
                step_log.duration = step_log.end_time - step_log.start_time
                result.agent_logs.append(step_log)
        
        # Store final context
        result.partial_results['final_context'] = agent_context
    
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
            Ingested content
        """
        # Placeholder - real implementation would:
        # 1. Read files from path
        # 2. Index for RAG
        # 3. Return structured content
        
        return {
            'path': path,
            'ingested': True,
            'file_count': 0
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
        
        # Get template
        template = get_template(result.run_spec.template_name)
        
        if not template:
            result.error = f"Template '{result.run_spec.template_name}' not found"
            return
        
        # Prepare output directory
        output_dir = result.run_spec.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get title for output path
        title = result.partial_results.get('title', result.run_spec.topic or 'untitled')
        
        # Use RunSpec.generate_output_path for proper slug handling and collision detection
        output_path = result.run_spec.generate_output_path(title)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result.output_path = output_path
        
        # Render template
        try:
            # Build context from partial results
            template_context = result.partial_results.get('final_context', {})
            
            # Render
            content = template.render(template_context)
            
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
