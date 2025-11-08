#!/usr/bin/env python3
"""UCOP CLI - Command-line interface for job management."""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Union, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.engine import UnifiedJobExecutor, JobConfig


class UCOPClient:
    """Client for direct job execution."""
    
    def __init__(self, mode: str = "direct"):
        self.mode = mode
        
        if mode == "direct":
            self.executor = UnifiedJobExecutor()
        else:
            # HTTP mode for backward compatibility
            import requests
            self.requests = requests
            self.base_url = "http://localhost:8080"
        
    def check_health(self) -> bool:
        """Check if executor is ready."""
        if self.mode == "direct":
            return True
        
        try:
            response = self.requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def create_job(self, workflow_name: str, params: Dict[str, Any], 
                   input_spec: Union[str, Path, List] = None,
                   blog_mode: bool = False,
                   title: str = None) -> Optional[Dict]:
        """Create a new job."""
        
        if self.mode == "direct":
            # Use unified executor
            try:
                # Determine input
                job_input = input_spec or params.get('topic', 'Unknown Topic')
                
                config = JobConfig(
                    workflow=workflow_name,
                    input=job_input,
                    params=params,
                    blog_mode=blog_mode,
                    title=title
                )
                
                result = self.executor.run_job(config)
                
                return {
                    "job_id": result.job_id,
                    "status": result.status,
                    "output_path": str(result.output_path) if result.output_path else None,
                    "error": result.error
                }
                
            except Exception as e:
                print(f"❌ Error creating job: {e}")
                return None
        
        else:
            # HTTP mode
            try:
                response = self.requests.post(
                    f"{self.base_url}/api/jobs/create",
                    json={
                        "workflow_name": workflow_name,
                        "params": params
                    },
                    timeout=5
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"❌ Error creating job: {e}")
                return None
    
    def list_jobs(self) -> Optional[Dict]:
        """List all jobs."""
        if self.mode == "direct":
            try:
                jobs = self.executor.job_engine._jobs
                return {
                    "jobs": [job.to_dict() for job in jobs.values()]
                }
            except Exception as e:
                print(f"❌ Error listing jobs: {e}")
                return None
        
        try:
            response = self.requests.get(f"{self.base_url}/api/jobs", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error listing jobs: {e}")
            return None
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job details."""
        if self.mode == "direct":
            try:
                job = self.executor.job_engine._jobs.get(job_id)
                if job:
                    return job.to_dict()
                return None
            except Exception as e:
                print(f"❌ Error getting job: {e}")
                return None
        
        try:
            response = self.requests.get(f"{self.base_url}/api/jobs/{job_id}", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting job: {e}")
            return None
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a running job."""
        if self.mode == "direct":
            try:
                self.executor.job_engine.pause_job(job_id)
                return True
            except Exception as e:
                print(f"❌ Error pausing job: {e}")
                return False
        
        try:
            response = self.requests.post(f"{self.base_url}/api/jobs/{job_id}/pause", timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Error pausing job: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if self.mode == "direct":
            try:
                self.executor.job_engine.resume_job(job_id)
                return True
            except Exception as e:
                print(f"❌ Error resuming job: {e}")
                return False
        
        try:
            response = self.requests.post(f"{self.base_url}/api/jobs/{job_id}/resume", timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Error resuming job: {e}")
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        if self.mode == "direct":
            try:
                self.executor.job_engine.cancel_job(job_id)
                return True
            except Exception as e:
                print(f"❌ Error cancelling job: {e}")
                return False
        
        try:
            response = self.requests.post(f"{self.base_url}/api/jobs/{job_id}/cancel", timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Error cancelling job: {e}")
            return False
    
    def watch_job(self, job_id: str, interval: float = 2.0):
        """Watch a job's progress in real-time."""
        print(f"📊 Watching job {job_id} (Ctrl+C to stop)")
        print("=" * 60)
        
        try:
            while True:
                job = self.get_job(job_id)
                if not job:
                    break
                
                status = job.get('status', 'unknown')
                progress = job.get('progress', 0.0)
                step = job.get('current_step', 'N/A')
                
                # Clear line and print status
                sys.stdout.write('\r' + ' ' * 80 + '\r')
                sys.stdout.write(f"Status: {status} | Progress: {progress:.1f}% | Step: {step}")
                sys.stdout.flush()
                
                # Check if terminal status
                if status in ['completed', 'failed', 'cancelled']:
                    print()
                    if status == 'completed':
                        print("✅ Job completed successfully!")
                    elif status == 'failed':
                        error = job.get('error_message', 'Unknown error')
                        print(f"❌ Job failed: {error}")
                    else:
                        print("⚠️  Job cancelled")
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⚠️  Stopped watching (job still running)")


def cmd_create(args, client: UCOPClient):
    """Create a new job."""
    # Parse parameters from JSON or key=value format
    params = {}
    if args.params:
        if args.params.startswith('{'):
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                return 1
        else:
            for param in args.params.split(','):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key.strip()] = value.strip()
    
    # Handle input
    input_spec = None
    if args.input:
        input_path = Path(args.input)
        if input_path.exists():
            if input_path.is_dir():
                input_spec = input_path
            else:
                input_spec = input_path
        else:
            # Might be a list
            if ',' in args.input:
                input_spec = [Path(p.strip()) for p in args.input.split(',')]
            else:
                print(f"⚠️  Input path not found: {args.input}")
                input_spec = args.input  # Use as topic
    
    # Get blog mode and title
    blog_mode = getattr(args, 'blog', False)
    title = getattr(args, 'title', None)
    
    result = client.create_job(args.workflow, params, input_spec, blog_mode, title)
    if result:
        job_id = result.get('job_id')
        print(f"✅ Job created: {job_id}")
        print(f"   Workflow: {args.workflow}")
        print(f"   Status: {result.get('status', 'unknown')}")
        
        if blog_mode:
            print(f"   Blog mode: ON (output to {{slug}}/index.md)")
        
        if result.get('output_path'):
            print(f"   Output: {result['output_path']}")
        
        if args.watch and client.mode == "http":
            print()
            client.watch_job(job_id)
    
    return 0


def cmd_list(args, client: UCOPClient):
    """List all jobs."""
    result = client.list_jobs()
    if not result:
        return 1
    
    jobs = result.get('jobs', [])
    
    if not jobs:
        print("No jobs found")
        return 0
    
    print(f"📋 Found {len(jobs)} jobs:")
    print("=" * 100)
    print(f"{'Job ID':<16} {'Workflow':<20} {'Status':<12} {'Progress':<10} {'Started':<20}")
    print("=" * 100)
    
    for job in jobs:
        job_id = job.get('job_id', 'N/A')[:14]
        workflow = job.get('workflow_name', 'N/A')[:18]
        status = job.get('status', 'N/A')[:10]
        progress = f"{job.get('progress', 0):.1f}%"
        started = job.get('started_at', 'N/A')[:19]
        
        print(f"{job_id:<16} {workflow:<20} {status:<12} {progress:<10} {started:<20}")
    
    return 0


def cmd_show(args, client: UCOPClient):
    """Show job details."""
    job = client.get_job(args.job_id)
    if not job:
        return 1
    
    print(f"📄 Job Details: {args.job_id}")
    print("=" * 60)
    print(f"Workflow:      {job.get('workflow_name')}")
    print(f"Status:        {job.get('status')}")
    print(f"Progress:      {job.get('progress', 0):.1f}%")
    print(f"Current Step:  {job.get('current_step', 'N/A')}")
    print(f"Started:       {job.get('started_at', 'N/A')}")
    print(f"Completed:     {job.get('completed_at', 'N/A')}")
    
    if job.get('error_message'):
        print(f"\n❌ Error: {job['error_message']}")
    
    if job.get('input_params'):
        print("\n📥 Input Parameters:")
        print(json.dumps(job['input_params'], indent=2))
    
    if job.get('output_data'):
        print("\n📤 Output Data:")
        print(json.dumps(job['output_data'], indent=2))
    
    if args.watch:
        print()
        client.watch_job(args.job_id)
    
    return 0


def cmd_pause(args, client: UCOPClient):
    """Pause a job."""
    if client.pause_job(args.job_id):
        print(f"⏸️  Job {args.job_id} paused")
        return 0
    return 1


def cmd_resume(args, client: UCOPClient):
    """Resume a job."""
    if client.resume_job(args.job_id):
        print(f"▶️  Job {args.job_id} resumed")
        return 0
    return 1


def cmd_cancel(args, client: UCOPClient):
    """Cancel a job."""
    if client.cancel_job(args.job_id):
        print(f"🛑 Job {args.job_id} cancelled")
        return 0
    return 1


def cmd_watch(args, client: UCOPClient):
    """Watch a job's progress."""
    client.watch_job(args.job_id, args.interval)
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="UCOP CLI - Unified Content Operations Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new job (direct mode - default)
  ucop_cli.py create blog_generation --params '{"topic": "Python Tips"}'
  
  # Create with file input
  ucop_cli.py create blog_generation --input article.md
  
  # Create with folder input
  ucop_cli.py create blog_generation --input ./docs/
  
  # List all jobs
  ucop_cli.py list
  
  # Show job details and watch progress
  ucop_cli.py show <job-id> --watch
  
  # Use HTTP mode (requires web server running)
  ucop_cli.py --mode http create blog_generation --params '{"topic": "Python"}'
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['direct', 'http'],
        default='direct',
        help='Execution mode: direct (default) or http (requires web server)'
    )
    
    parser.add_argument(
        '--server',
        default='http://localhost:8080',
        help='Server URL for HTTP mode (default: http://localhost:8080)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new job')
    create_parser.add_argument('workflow', help='Workflow name')
    create_parser.add_argument(
        '--params',
        help='Job parameters (JSON or key=value,key=value)'
    )
    create_parser.add_argument(
        '--input',
        help='Input file, folder, or list of files (default: uses topic from params)'
    )
    create_parser.add_argument(
        '--blog',
        action='store_true',
        help='Enable blog mode (output to {slug}/index.md instead of {slug}.md)'
    )
    create_parser.add_argument(
        '--title',
        help='Post title for slug generation (default: uses input topic)'
    )
    create_parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch job progress after creation'
    )
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all jobs')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show job details')
    show_parser.add_argument('job_id', help='Job ID')
    show_parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch job progress'
    )
    
    # Pause command
    pause_parser = subparsers.add_parser('pause', help='Pause a job')
    pause_parser.add_argument('job_id', help='Job ID')
    
    # Resume command
    resume_parser = subparsers.add_parser('resume', help='Resume a job')
    resume_parser.add_argument('job_id', help='Job ID')
    
    # Cancel command
    cancel_parser = subparsers.add_parser('cancel', help='Cancel a job')
    cancel_parser.add_argument('job_id', help='Job ID')
    
    # Watch command
    watch_parser = subparsers.add_parser('watch', help='Watch job progress')
    watch_parser.add_argument('job_id', help='Job ID')
    watch_parser.add_argument(
        '--interval',
        type=float,
        default=2.0,
        help='Update interval in seconds (default: 2.0)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Create client
    client = UCOPClient(mode=args.mode)
    
    # Check health (only for HTTP mode)
    if args.mode == "http":
        client.base_url = args.server
        if not client.check_health():
            print(f"❌ Cannot connect to server at {args.server}")
            print("   Make sure the web UI is running: python start_web_ui.py")
            return 1
    else:
        print(f"🚀 Running in direct mode")
    
    # Execute command
    commands = {
        'create': cmd_create,
        'list': cmd_list,
        'show': cmd_show,
        'pause': cmd_pause,
        'resume': cmd_resume,
        'cancel': cmd_cancel,
        'watch': cmd_watch
    }
    
    try:
        return commands[args.command](args, client)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        return 130
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
