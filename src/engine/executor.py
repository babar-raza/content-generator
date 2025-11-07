"""Unified job executor for CLI and Web."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from datetime import datetime, timezone
import uuid
import logging
import json

from .input_resolver import InputResolver, ContextSet
from .aggregator import OutputAggregator, TemplateSchema
from .completeness_gate import CompletenessGate
from .context_merger import ContextMerger
from .agent_tracker import AgentExecutionTracker
from .exceptions import *

logger = logging.getLogger(__name__)


@dataclass
class JobConfig:
    """Job configuration."""
    workflow: str
    input: Union[str, Path, List[Union[str, Path]]]
    template: str = "blog"
    extra_context: List[Dict[str, Any]] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    job_id: Optional[str] = None
    enable_strict_mode: bool = False
    enable_citations: bool = True
    check_duplicates: bool = True
    blog_mode: bool = False  # Blog switch: ON→folder/index.md, OFF→file.md
    title: Optional[str] = None  # For slug generation


@dataclass
class JobResult:
    """Job execution result."""
    job_id: str
    status: str
    output_path: Optional[Path] = None
    report_path: Optional[Path] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "output_path": str(self.output_path) if self.output_path else None,
            "report_path": str(self.report_path) if self.report_path else None,
            "error": self.error,
            "metadata": self.metadata,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class UnifiedJobExecutor:
    """Unified execution engine for both CLI and Web."""
    
    def __init__(self, 
                 config_dir: Path = None,
                 data_dir: Path = None,
                 device: str = None):
        
        self.config_dir = config_dir or Path("./config")
        self.data_dir = data_dir or Path("./data")
        self.templates_dir = Path("./templates")
        
        # CUDA detection and device setup
        self.device = self._setup_device(device)
        logger.info(f"UnifiedJobExecutor initialized with device: {self.device}")
        
        # Initialize components
        self.input_resolver = InputResolver()
        self.context_merger = ContextMerger()
        self.completeness_gate = CompletenessGate()
        
        # Import workflow compiler
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from orchestration.workflow_compiler import WorkflowCompiler
        from orchestration.checkpoint_manager import CheckpointManager
        from orchestration.job_execution_engine import JobExecutionEngine
        
        self.workflow_compiler = WorkflowCompiler(self.config_dir)
        self.checkpoint_manager = CheckpointManager(self.data_dir / "checkpoints")
        self.job_engine = JobExecutionEngine(
            self.workflow_compiler,
            self.checkpoint_manager
        )
    
    def _setup_device(self, device: str = None) -> str:
        """Setup computation device with CUDA auto-detection."""
        from .device import get_gpu_manager
        
        gpu_manager = get_gpu_manager()
        return gpu_manager.choose_device(device or "auto")
    
    def run_job(self, config: JobConfig) -> JobResult:
        """Run a job synchronously (CLI mode)."""
        
        # Generate job ID
        job_id = config.job_id or str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Starting job {job_id}: workflow={config.workflow}")
        
        try:
            # Step 1: Resolve input
            context_set = self.input_resolver.resolve(config.input)
            logger.info(f"Input resolved: {context_set.metadata.get('input_mode')}")
            
            # Step 2: Load template schema
            template_schema = self._load_template_schema(config.template)
            
            # Step 3: Initialize tracking
            agent_tracker = AgentExecutionTracker(job_id)
            aggregator = OutputAggregator(template_schema)
            
            # Step 4: Merge contexts
            merged_context = self.context_merger.merge(
                extra_contexts=config.extra_context,
                docs_context=context_set.primary_content
            )
            
            # Step 5: Prepare job params
            job_params = {
                "topic": context_set.primary_content[:100],  # First 100 chars as topic
                "context": merged_context,
                "input_metadata": context_set.metadata,
                **config.params
            }
            
            # Step 6: Submit to job engine
            job_id = self.job_engine.submit_job(
                workflow_name=config.workflow,
                input_params=job_params,
                job_id=job_id
            )
            
            # Step 7: Start execution
            self.job_engine.start_job(job_id)
            
            # Step 8: Wait for completion
            job = self._wait_for_completion(job_id)
            
            # Step 9: Determine output path (before validation)
            output_path = self._get_output_path(job_id, config)
            
            # Step 10: Wait for job engine to write output
            # The job engine should write to the determined path
            # For now, check if output exists in the determined location
            # or in the default job output directory
            
            if output_path.exists():
                final_content = output_path.read_text(encoding='utf-8')
            else:
                # Fallback: check job directory
                job_output_dir = self.data_dir / "jobs" / job_id / "output"
                if job_output_dir.exists():
                    md_files = list(job_output_dir.glob("*.md"))
                    if md_files:
                        # Copy to determined output path
                        source_file = md_files[0]
                        final_content = source_file.read_text(encoding='utf-8')
                        output_path.write_text(final_content, encoding='utf-8')
                        logger.info(f"Copied output to {output_path}")
                    else:
                        final_content = ""
                else:
                    final_content = ""
            
            # Step 11: Validate output
            if final_content:
                # Run completeness gate with template spec
                template_spec = {
                    'required_sections': template_schema.required_sections if hasattr(template_schema, 'required_sections') else []
                }
                self.completeness_gate.fail_if_empty(final_content, template_spec=template_spec)
                
                # Run aggregator validation
                aggregator.fail_if_incomplete(final_content)
            
            # Step 12: Generate report
            report_path = self._generate_report(job_id, aggregator, agent_tracker)
            
            completed_at = datetime.now(timezone.utc).isoformat()
            
            return JobResult(
                job_id=job_id,
                status="completed",
                output_path=output_path,
                report_path=report_path,
                metadata={
                    "input_mode": context_set.metadata.get("input_mode"),
                    "template": config.template,
                    "workflow": config.workflow,
                    "device": self.device,
                    "blog_mode": config.blog_mode
                },
                started_at=started_at,
                completed_at=completed_at
            )
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            
            return JobResult(
                job_id=job_id,
                status="failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat()
            )
    
    async def run_job_async(self, config: JobConfig) -> JobResult:
        """Run a job asynchronously (Web mode)."""
        # For now, same as sync
        # TODO: Make truly async
        return self.run_job(config)
    
    def _load_template_schema(self, template_name: str) -> TemplateSchema:
        """Load template schema."""
        schema_path = self.templates_dir / "schema" / f"{template_name}_template.yaml"
        
        if not schema_path.exists():
            logger.warning(f"Template schema not found: {schema_path}, using default")
            # Return default schema
            from .aggregator import SectionRequirement
            return TemplateSchema(
                template_name=template_name,
                required_sections=[
                    SectionRequirement(name="introduction", agent="write_introduction"),
                    SectionRequirement(name="body", agent="write_sections"),
                    SectionRequirement(name="conclusion", agent="write_conclusion")
                ]
            )
        
        return TemplateSchema.from_yaml(schema_path)
    
    def _wait_for_completion(self, job_id: str, timeout: int = 3600) -> Dict:
        """Wait for job to complete."""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            job = self.job_engine.get_job_status(job_id)
            
            status = job.get('status')
            if status in ['completed', 'failed', 'cancelled']:
                return job
            
            time.sleep(2)
        
        raise TimeoutError(f"Job {job_id} timed out after {timeout}s")
    
    def _generate_slug(self, text: str) -> str:
        """Generate URL-safe slug from text.
        
        Args:
            text: Input text (title, topic, etc.)
            
        Returns:
            URL-safe slug string
        """
        from .slug_service import slugify
        return slugify(text) or "untitled"
    
    def _get_output_path(self, job_id: str, config: JobConfig = None) -> Path:
        """Get output file path with template-based blog detection.
        
        Args:
            job_id: Job identifier
            config: Job configuration (for template and title)
            
        Returns:
            Output file path based on template type:
            - Blog template:  ./output/{slug}/index.md
            - Non-blog template: ./output/{slug}.md
        """
        from .output_path_resolver import resolve_output_path, is_blog_template
        
        output_dir = Path("./output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate slug from title or topic
        if config and config.title:
            slug = self._generate_slug(config.title)
        elif config and isinstance(config.input, str):
            # Use input topic as slug
            slug = self._generate_slug(config.input)
        else:
            # Fallback to job_id
            slug = job_id[:12]  # First 12 chars of job_id
        
        # Get template ID - check blog_mode flag first for backward compat
        # then fall back to template-based detection
        if config and config.blog_mode:
            # Force blog template behavior
            template_id = "blog"
        else:
            template_id = config.template if config else "blog"
        
        # Resolve path based on template type
        output_path = resolve_output_path(template_id, slug, output_dir)
        
        is_blog = is_blog_template(template_id)
        logger.info(f"Template: {template_id} (blog={is_blog}), output path = {output_path}")
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return output_path
    
    def _generate_report(self,
                        job_id: str,
                        aggregator: OutputAggregator,
                        tracker: AgentExecutionTracker) -> Path:
        """Generate execution report."""
        
        job_dir = self.data_dir / "jobs" / job_id
        report_path = job_dir / "report.json"
        
        # Get aggregator report
        agg_report = aggregator.generate_report()
        
        # Get agent summary
        agent_summary = tracker.get_summary()
        
        # Combine reports
        full_report = {
            "job_id": job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "validation": agg_report.to_dict(),
            "agent_execution": agent_summary
        }
        
        report_path.write_text(
            json.dumps(full_report, indent=2),
            encoding='utf-8'
        )
        
        logger.info(f"Report generated: {report_path}")
        return report_path
