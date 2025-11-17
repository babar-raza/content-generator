#!/usr/bin/env python3
"""Simple CLI for testing Job Execution Engine."""

import sys
import argparse
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core import EventBus, Config
from src.orchestration.workflow_compiler import WorkflowCompiler
from src.orchestration.enhanced_registry import EnhancedAgentRegistry
from src.orchestration.job_execution_engine import JobExecutionEngine
from src.orchestration.job_state import JobStatus


def cmd_generate(args):
    """Generate blog post from KB article."""
    print(f"🚀 Starting blog generation...")
    print(f"   Input: {args.input}")
    print(f"   Output: {args.output}")
    print(f"   Workflow: {args.workflow}")
    
    # Initialize components
    print("\n📦 Initializing components...")
    
    try:
        compiler = WorkflowCompiler(workflows_path=Path("templates/workflows.yaml"))
        registry = EnhancedAgentRegistry()
        event_bus = EventBus()
        config = Config()
        
        # Create engine
        engine = JobExecutionEngine(
            compiler=compiler,
            registry=registry,
            event_bus=event_bus,
            config=config,
            max_concurrent_jobs=2
        )
        
        # Start engine
        engine.start()
        print("✓ Engine started")
        
        # Submit job
        print(f"\n📝 Submitting job...")
        job_id = engine.submit_job(
            workflow_id=args.workflow,
            inputs={
                'kb_article_path': args.input,
                'output_dir': args.output
            }
        )
        
        print(f"✓ Job submitted: {job_id}")
        
        # Monitor job
        print(f"\n⏳ Monitoring job execution...")
        
        last_status = None
        last_step = None
        
        while True:
            metadata = engine.get_job_status(job_id)
            
            if metadata.status != last_status or metadata.current_step != last_step:
                status_symbol = {
                    JobStatus.PENDING: "⏸️",
                    JobStatus.RUNNING: "▶️",
                    JobStatus.PAUSED: "⏸️",
                    JobStatus.COMPLETED: "✅",
                    JobStatus.FAILED: "❌",
                    JobStatus.CANCELLED: "🚫"
                }.get(metadata.status, "❓")
                
                print(f"{status_symbol} Status: {metadata.status.value}")
                if metadata.current_step:
                    print(f"   Step: {metadata.current_step}")
                print(f"   Progress: {metadata.progress * 100:.1f}%")
                print(f"   Completed steps: {metadata.completed_steps}/{metadata.total_steps}")
                
                if args.verbose:
                    job_state = engine.get_job_state(job_id)
                    if job_state:
                        print(f"   Failed steps: {metadata.failed_steps}")
                
                last_status = metadata.status
                last_step = metadata.current_step
            
            # Check if done
            if metadata.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                break
            
            time.sleep(0.5)
        
        # Final status
        print(f"\n{'='*60}")
        final_metadata = engine.get_job_status(job_id)
        
        if final_metadata.status == JobStatus.COMPLETED:
            print("✅ Job completed successfully!")
            print(f"   Duration: {(final_metadata.completed_at - final_metadata.started_at).total_seconds():.1f}s")
            print(f"   Completed steps: {final_metadata.completed_steps}/{final_metadata.total_steps}")
            
            if args.verbose:
                job_state = engine.get_job_state(job_id)
                print(f"\n📊 Job outputs:")
                for key, value in job_state.outputs.items():
                    print(f"   - {key}: {str(value)[:100]}...")
            
            return 0
        
        elif final_metadata.status == JobStatus.FAILED:
            print("❌ Job failed!")
            print(f"   Error: {final_metadata.error_message}")
            return 1
        
        else:
            print(f"⚠️  Job ended with status: {final_metadata.status.value}")
            return 1
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    finally:
        # Cleanup
        if 'engine' in locals():
            engine.stop()


def cmd_status(args):
    """Check job status."""
    try:
        from src.orchestration.job_storage import JobStorage
        
        storage = JobStorage()
        
        if args.job_id:
            # Get specific job
            job_state = storage.load_job(args.job_id)
            
            if not job_state:
                print(f"❌ Job not found: {args.job_id}")
                return 1
            
            print(f"\n📊 Job Status: {args.job_id}")
            print("="*60)
            print(f"Workflow: {job_state.metadata.workflow_id}")
            print(f"Status: {job_state.metadata.status.value}")
            print(f"Created: {job_state.metadata.created_at}")
            print(f"Started: {job_state.metadata.started_at}")
            print(f"Completed: {job_state.metadata.completed_at}")
            print(f"Progress: {job_state.metadata.progress * 100:.1f}%")
            print(f"Steps: {job_state.metadata.completed_steps}/{job_state.metadata.total_steps}")
            
            if job_state.metadata.error_message:
                print(f"Error: {job_state.metadata.error_message}")
            
            if args.verbose:
                print(f"\n📝 Steps:")
                for agent_id, step in job_state.steps.items():
                    print(f"   - {agent_id}: {step.status.value}")
                    if step.error:
                        print(f"     Error: {step.error}")
        
        else:
            # List all jobs
            jobs = storage.list_jobs(limit=args.limit)
            
            if not jobs:
                print("📭 No jobs found")
                return 0
            
            print(f"\n📋 Jobs ({len(jobs)}):")
            print("="*60)
            
            for metadata in jobs:
                status_symbol = {
                    JobStatus.PENDING: "⏸️",
                    JobStatus.RUNNING: "▶️",
                    JobStatus.PAUSED: "⏸️",
                    JobStatus.COMPLETED: "✅",
                    JobStatus.FAILED: "❌",
                    JobStatus.CANCELLED: "🚫"
                }.get(metadata.status, "❓")
                
                print(f"\n{status_symbol} {metadata.job_id}")
                print(f"   Workflow: {metadata.workflow_id}")
                print(f"   Status: {metadata.status.value}")
                print(f"   Created: {metadata.created_at}")
                print(f"   Progress: {metadata.progress * 100:.1f}%")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_cancel(args):
    """Cancel a running job."""
    try:
        # Create engine
        compiler = WorkflowCompiler()
        registry = EnhancedAgentRegistry()
        event_bus = EventBus()
        config = Config()
        
        engine = JobExecutionEngine(
            compiler=compiler,
            registry=registry,
            event_bus=event_bus,
            config=config
        )
        
        # Cancel job
        result = engine.cancel_job(args.job_id)
        
        if result:
            print(f"✓ Job cancellation requested: {args.job_id}")
            return 0
        else:
            print(f"❌ Could not cancel job: {args.job_id}")
            return 1
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_delete(args):
    """Delete a job."""
    try:
        from src.orchestration.job_storage import JobStorage
        
        storage = JobStorage()
        
        result = storage.delete_job(args.job_id)
        
        if result:
            print(f"✓ Job deleted: {args.job_id}")
            return 0
        else:
            print(f"❌ Job not found: {args.job_id}")
            return 1
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Job Execution Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate blog post
  python ucop_cli.py generate --input tests/fixtures/sample_kb.md --output output/
  
  # Check job status
  python ucop_cli.py status --job-id <job-id>
  
  # List all jobs
  python ucop_cli.py status
  
  # Cancel job
  python ucop_cli.py cancel --job-id <job-id>
  
  # Delete job
  python ucop_cli.py delete --job-id <job-id>
        """
    )
    
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate blog post')
    generate_parser.add_argument('--input', '-i', required=True, help='Input KB article path')
    generate_parser.add_argument('--output', '-o', default='output/', help='Output directory')
    generate_parser.add_argument('--workflow', '-w', default='fast_draft', help='Workflow to use')
    generate_parser.set_defaults(func=cmd_generate)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check job status')
    status_parser.add_argument('--job-id', '-j', help='Job ID to check')
    status_parser.add_argument('--limit', '-l', type=int, default=10, help='Limit number of jobs')
    status_parser.set_defaults(func=cmd_status)
    
    # Cancel command
    cancel_parser = subparsers.add_parser('cancel', help='Cancel job')
    cancel_parser.add_argument('--job-id', '-j', required=True, help='Job ID to cancel')
    cancel_parser.set_defaults(func=cmd_cancel)
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete job')
    delete_parser.add_argument('--job-id', '-j', required=True, help='Job ID to delete')
    delete_parser.set_defaults(func=cmd_delete)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
