#!/usr/bin/env python3
"""UCOP CLI - Unified command-line interface using the unified engine."""

import sys
import argparse
import json
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.engine.engine import get_engine, RunSpec, JobStatus
from src.core.template_registry import list_templates


# Visualization command handlers

def cmd_viz_workflows(args):
    """List workflow profiles."""
    from src.visualization.workflow_visualizer import WorkflowVisualizer
    
    visualizer = WorkflowVisualizer()
    profiles = visualizer.workflows.get('profiles', {})
    
    if args.json:
        print(json.dumps({
            "profiles": [
                {
                    "id": profile_id,
                    "name": profile_data.get('name', profile_id),
                    "description": profile_data.get('description', ''),
                    "steps": len(profile_data.get('steps', []))
                }
                for profile_id, profile_data in profiles.items()
            ]
        }, indent=2))
    else:
        print(f"\n📊 Workflow Profiles ({len(profiles)})")
        print("="*60)
        for profile_id, profile_data in profiles.items():
            print(f"\n  {profile_id}")
            print(f"  Name: {profile_data.get('name', profile_id)}")
            print(f"  Description: {profile_data.get('description', 'N/A')}")
            print(f"  Steps: {len(profile_data.get('steps', []))}")
    
    return 0


def cmd_viz_graph(args):
    """Generate visual workflow graph."""
    from src.visualization.workflow_visualizer import WorkflowVisualizer
    
    visualizer = WorkflowVisualizer()
    
    try:
        graph = visualizer.create_visual_graph(args.profile)
        
        if args.json:
            print(json.dumps(graph, indent=2))
        else:
            print(f"\n📊 Workflow Graph: {args.profile}")
            print("="*60)
            print(f"Nodes: {len(graph['nodes'])}")
            print(f"Edges: {len(graph['edges'])}")
            
            if args.verbose:
                print("\nNodes:")
                for node in graph['nodes']:
                    print(f"  - {node['id']}: {node['data'].get('label', 'N/A')}")
                
                print("\nEdges:")
                for edge in graph['edges']:
                    print(f"  - {edge['source']} → {edge['target']}")
        
        return 0
    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_viz_metrics(args):
    """Get workflow execution metrics."""
    from src.visualization.workflow_visualizer import WorkflowVisualizer
    
    visualizer = WorkflowVisualizer()
    
    try:
        metrics = visualizer.get_execution_metrics(args.profile)
        
        if args.json:
            print(json.dumps(metrics, indent=2))
        else:
            print(f"\n📊 Workflow Metrics: {args.profile}")
            print("="*60)
            print(f"Total Steps: {metrics.get('total_steps', 0)}")
            print(f"Completed Steps: {metrics.get('completed_steps', 0)}")
            print(f"Total Duration: {metrics.get('total_duration', 0):.2f}s")
            
            if 'step_metrics' in metrics and args.verbose:
                print("\nStep Metrics:")
                for step_id, step_metrics in metrics['step_metrics'].items():
                    print(f"  {step_id}:")
                    print(f"    Status: {step_metrics.get('status', 'N/A')}")
                    print(f"    Duration: {step_metrics.get('duration', 0):.2f}s")
        
        return 0
    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_viz_agents(args):
    """Show agent status."""
    from src.visualization.monitor import get_monitor
    
    monitor = get_monitor()
    agents = monitor.get_agent_states()
    
    if args.json:
        print(json.dumps({"agents": agents, "total": len(agents)}, indent=2))
    else:
        print(f"\n🤖 Agent Status ({len(agents)} agents)")
        print("="*60)
        
        if not agents:
            print("  No agents registered")
        else:
            for agent in agents:
                print(f"\n  {agent.get('name', 'Unknown')}")
                print(f"    Status: {agent.get('status', 'unknown')}")
                print(f"    Last Seen: {agent.get('last_seen', 'N/A')}")
    
    return 0


def cmd_viz_flows(args):
    """Show active data flows."""
    from src.visualization.monitor import get_monitor
    
    monitor = get_monitor()
    flows = monitor.get_active_flows()
    
    if args.json:
        print(json.dumps({"active_flows": flows, "count": len(flows)}, indent=2))
    else:
        print(f"\n🔄 Active Flows ({len(flows)})")
        print("="*60)
        
        if not flows:
            print("  No active flows")
        else:
            for flow in flows:
                print(f"\n  Flow {flow.get('flow_id', 'unknown')}")
                print(f"    Source: {flow.get('source', 'N/A')}")
                print(f"    Target: {flow.get('target', 'N/A')}")
                print(f"    Status: {flow.get('status', 'N/A')}")
    
    return 0


def cmd_viz_bottlenecks(args):
    """Detect performance bottlenecks."""
    from src.visualization.agent_flow_monitor import get_flow_monitor
    
    monitor = get_flow_monitor()
    bottlenecks = monitor.detect_bottlenecks()
    
    if args.json:
        print(json.dumps({"bottlenecks": bottlenecks}, indent=2))
    else:
        print(f"\n⚠️  Performance Bottlenecks ({len(bottlenecks)})")
        print("="*60)
        
        if not bottlenecks:
            print("  No bottlenecks detected")
        else:
            for bottleneck in bottlenecks:
                print(f"\n  {bottleneck.get('agent_id', 'Unknown')}")
                print(f"    Duration: {bottleneck.get('duration', 0):.2f}s")
                print(f"    Flow ID: {bottleneck.get('flow_id', 'N/A')}")
                print(f"    Type: {bottleneck.get('event_type', 'N/A')}")
    
    return 0


def cmd_viz_debug(args):
    """Start a debug session."""
    from src.visualization.workflow_debugger import get_workflow_debugger
    
    debugger = get_workflow_debugger()
    
    if args.action == 'create':
        session_id = debugger.start_debug_session(args.correlation_id)
        print(f"✅ Debug session created: {session_id}")
        print(f"   Correlation ID: {args.correlation_id}")
        return 0
    
    elif args.action == 'list':
        sessions = debugger.debug_sessions
        
        if args.json:
            print(json.dumps({
                "sessions": [
                    session.to_dict()
                    for session in sessions.values()
                ]
            }, indent=2))
        else:
            print(f"\n🐛 Debug Sessions ({len(sessions)})")
            print("="*60)
            
            if not sessions:
                print("  No active debug sessions")
            else:
                for session_id, session in sessions.items():
                    print(f"\n  {session_id}")
                    print(f"    Correlation ID: {session.correlation_id}")
                    print(f"    Status: {session.status}")
                    print(f"    Breakpoints: {len(session.breakpoints)}")
        
        return 0
    
    elif args.action == 'breakpoint':
        if not args.session_id:
            print("❌ Error: --session-id required for breakpoint action")
            return 1
        
        breakpoint_id = debugger.add_breakpoint(
            session_id=args.session_id,
            agent_id=args.agent_id,
            event_type=args.event_type,
            condition=args.condition
        )
        
        print(f"✅ Breakpoint added: {breakpoint_id}")
        print(f"   Session: {args.session_id}")
        print(f"   Agent: {args.agent_id}")
        print(f"   Event: {args.event_type}")
        if args.condition:
            print(f"   Condition: {args.condition}")
        
        return 0
    
    else:
        print(f"❌ Error: Unknown debug action: {args.action}")
        return 1


def cmd_generate(args):
    """Generate content using the unified engine."""
    
    # Build run spec
    run_spec = RunSpec(
        topic=args.topic,
        template_name=args.template,
        kb_path=args.kb,
        docs_path=args.docs,
        blog_path=args.blog,
        api_path=args.api,
        tutorial_path=args.tutorial,
        auto_topic=args.auto_topic,
        output_dir=Path(args.output_dir)
    )
    
    # Validate
    errors = run_spec.validate()
    if errors:
        print("❌ Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    print(f"📝 Generating content with template: {args.template}")
    if args.topic:
        print(f"   Topic: {args.topic}")
    if args.auto_topic:
        print(f"   Auto-deriving topic from context")
    
    # Get engine and execute
    engine = get_engine()
    result = engine.generate_job(run_spec)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"Job ID: {result.job_id}")
    print(f"Status: {result.status.value}")
    print(f"Duration: {result.duration:.2f}s")
    
    if result.output_path:
        print(f"\n✅ Artifact written to: {result.output_path}")
        if result.manifest_path:
            print(f"📋 Manifest: {result.manifest_path}")
    
    if result.sources_used:
        print(f"\n📚 Sources used:")
        for source in result.sources_used:
            print(f"  - {source}")
    
    if result.error:
        print(f"\n⚠️ Errors occurred:")
        print(f"  {result.error}")
        
        if result.status == JobStatus.PARTIAL:
            print(f"\n  Partial artifact written with available content.")
    
    # Print pipeline
    if args.verbose:
        print(f"\n📊 Pipeline executed:")
        for i, agent_name in enumerate(result.pipeline_order, 1):
            log = next((l for l in result.agent_logs if l.agent_name == agent_name), None)
            if log:
                status = "✓" if not log.errors else "✗"
                print(f"  {i}. {status} {agent_name} ({log.duration:.2f}s)")
    
    # Return path to stdout for scripting
    if result.output_path:
        print(f"\nOUTPUT_PATH={result.output_path}")
    
    return 0 if result.status == JobStatus.COMPLETED else 1


def cmd_list_templates(args):
    """List available templates."""
    
    templates = list_templates(args.type)
    
    print(f"\n📋 Available Templates ({len(templates)})")
    print("="*60)
    
    for template in templates:
        print(f"\n  Name: {template.name}")
        print(f"  Type: {template.type.value}")
        
        if template.schema.required_placeholders:
            print(f"  Required: {', '.join(template.schema.required_placeholders)}")
        
        if template.metadata:
            print(f"  Metadata: {template.metadata}")
    
    return 0


def cmd_batch(args):
    """Execute batch job with multiple topics."""
    
    if not args.topics_file:
        print("❌ --topics-file required for batch mode")
        return 1
    
    # Read topics
    topics_file = Path(args.topics_file)
    if not topics_file.exists():
        print(f"❌ Topics file not found: {topics_file}")
        return 1
    
    topics = topics_file.read_text().strip().split('\n')
    topics = [t.strip() for t in topics if t.strip()]
    
    print(f"🚀 Starting batch job with {len(topics)} topics")
    print("="*60)
    
    # Get engine
    engine = get_engine()
    
    results = []
    for i, topic in enumerate(topics, 1):
        print(f"\n[{i}/{len(topics)}] Processing: {topic}")
        
        run_spec = RunSpec(
            topic=topic,
            template_name=args.template,
            kb_path=args.kb,
            docs_path=args.docs,
            blog_path=args.blog,
            api_path=args.api,
            tutorial_path=args.tutorial,
            output_dir=Path(args.output_dir)
        )
        
        result = engine.generate_job(run_spec)
        results.append(result)
        
        status_icon = "✅" if result.status == JobStatus.COMPLETED else "⚠️"
        print(f"  {status_icon} {result.status.value} - {result.output_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Batch Summary:")
    print(f"  Total: {len(results)}")
    print(f"  Completed: {sum(1 for r in results if r.status == JobStatus.COMPLETED)}")
    print(f"  Partial: {sum(1 for r in results if r.status == JobStatus.PARTIAL)}")
    print(f"  Failed: {sum(1 for r in results if r.status == JobStatus.FAILED)}")
    
    return 0


def cmd_validate(args):
    """Validate configuration files."""
    
    print("🔍 Validating configuration...")
    
    try:
        from config import load_validated_config
        
        snapshot = load_validated_config()
        
        print("✅ Configuration valid!")
        print(f"\n  Config hash: {snapshot.config_hash}")
        print(f"  Agent config: {len(snapshot.agent_config.get('agents', {}))} agents")
        print(f"  Performance config: loaded")
        print(f"  Tone config: loaded")
        print(f"  Main config: loaded")
        
        # Validate templates
        from src.core.template_registry import get_template_registry
        
        registry = get_template_registry()
        print(f"  Templates: {len(registry.list_templates())} loaded")
        
        return 0
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1


def cmd_list_jobs(args):
    """List all jobs (parity with web UI)."""
    from pathlib import Path
    import glob
    
    output_dir = Path('./output')
    if not output_dir.exists():
        if args.json:
            print(json.dumps({"jobs": []}))
        else:
            print("\n📋 No jobs found")
        return 0
    
    # Find job manifests
    manifests = glob.glob(str(output_dir / '**' / '.job_manifest.json'), recursive=True)
    
    jobs = []
    for manifest_path in manifests:
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                jobs.append(data)
        except Exception as e:
            continue
    
    if args.json:
        print(json.dumps({"jobs": jobs, "total": len(jobs)}, indent=2))
    else:
        print(f"\n📋 Jobs ({len(jobs)})")
        print("="*80)
        
        if not jobs:
            print("  No jobs found")
        else:
            for job in jobs:
                print(f"\n  Job ID: {job.get('job_id')}")
                print(f"    Status: {job.get('status')}")
                print(f"    Template: {job.get('run_spec', {}).get('template_name')}")
                print(f"    Topic: {job.get('run_spec', {}).get('topic', 'N/A')}")
                print(f"    Duration: {job.get('duration', 0):.2f}s")
                if job.get('output_path'):
                    print(f"    Output: {job.get('output_path')}")
    
    return 0


def cmd_get_job(args):
    """Get job details (parity with web UI)."""
    from pathlib import Path
    import glob
    
    # Search for job manifest
    output_dir = Path('./output')
    if not output_dir.exists():
        print(f"❌ Job {args.job_id} not found")
        return 1
    
    manifests = glob.glob(str(output_dir / '**' / '.job_manifest.json'), recursive=True)
    
    job_data = None
    for manifest_path in manifests:
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                if data.get('job_id') == args.job_id:
                    job_data = data
                    break
        except Exception:
            continue
    
    if not job_data:
        print(f"❌ Job {args.job_id} not found")
        return 1
    
    if args.json:
        print(json.dumps(job_data, indent=2))
    else:
        print(f"\n📋 Job Details: {args.job_id}")
        print("="*80)
        print(f"\n  Status: {job_data.get('status')}")
        print(f"  Duration: {job_data.get('duration', 0):.2f}s")
        
        run_spec = job_data.get('run_spec', {})
        print(f"\n  Run Specification:")
        print(f"    Template: {run_spec.get('template_name')}")
        print(f"    Topic: {run_spec.get('topic', 'N/A')}")
        print(f"    Auto-topic: {run_spec.get('auto_topic', False)}")
        
        if job_data.get('output_path'):
            print(f"\n  Output: {job_data.get('output_path')}")
        if job_data.get('manifest_path'):
            print(f"  Manifest: {job_data.get('manifest_path')}")
        
        if job_data.get('sources_used'):
            print(f"\n  Sources Used:")
            for source in job_data.get('sources_used', []):
                print(f"    - {source}")
        
        if job_data.get('pipeline_order'):
            print(f"\n  Pipeline Order:")
            for i, agent in enumerate(job_data.get('pipeline_order', []), 1):
                print(f"    {i}. {agent}")
        
        if args.show_logs and job_data.get('agent_logs'):
            print(f"\n  Agent Logs:")
            for log in job_data.get('agent_logs', []):
                agent_name = log.get('agent_name')
                duration = log.get('duration', 0)
                errors = log.get('errors', [])
                status = "✓" if not errors else "✗"
                print(f"    {status} {agent_name} ({duration:.2f}s)")
                if errors:
                    for error in errors:
                        print(f"      Error: {error}")
        
        if job_data.get('error'):
            print(f"\n  ⚠️ Error: {job_data.get('error')}")
    
    return 0


def cmd_config_snapshot(args):
    """Show configuration snapshot (parity with web UI /config/snapshot)."""
    from config import load_validated_config
    
    try:
        snapshot = load_validated_config()
        
        if args.json:
            print(json.dumps({
                "hash": snapshot.config_hash,
                "timestamp": snapshot.timestamp,
                "engine_version": snapshot.engine_version,
                "agent_count": len(snapshot.agent_config.get('agents', {})),
                "workflows": list(snapshot.main_config.get('workflows', {}).keys()),
                "tone_sections": list(snapshot.tone_config.get('section_controls', {}).keys()),
                "perf_timeouts": snapshot.perf_config.get('timeouts', {}),
                "perf_limits": snapshot.perf_config.get('limits', {})
            }, indent=2))
        else:
            print(f"\n⚙️  Configuration Snapshot")
            print("="*80)
            print(f"\n  Config Hash: {snapshot.config_hash}")
            print(f"  Timestamp: {snapshot.timestamp}")
            print(f"  Engine Version: {snapshot.engine_version}")
            print(f"\n  Components:")
            print(f"    Agents: {len(snapshot.agent_config.get('agents', {}))}")
            print(f"    Workflows: {len(snapshot.main_config.get('workflows', {}))}")
            print(f"    Tone Sections: {len(snapshot.tone_config.get('section_controls', {}))}")
            print(f"\n  Performance:")
            print(f"    Timeouts: {list(snapshot.perf_config.get('timeouts', {}).keys())}")
            print(f"    Limits: {list(snapshot.perf_config.get('limits', {}).keys())}")
        
        return 0
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1


def cmd_config_agents(args):
    """Show agent configurations (parity with web UI /config/agents)."""
    from config import load_validated_config
    
    try:
        snapshot = load_validated_config()
        agents = snapshot.agent_config.get('agents', {})
        
        if args.json:
            print(json.dumps({
                "agent_count": len(agents),
                "agents": {
                    agent_id: {
                        "id": agent_data.get('id'),
                        "version": agent_data.get('version'),
                        "description": agent_data.get('description')
                    }
                    for agent_id, agent_data in agents.items()
                }
            }, indent=2))
        else:
            print(f"\n🤖 Agent Configurations ({len(agents)})")
            print("="*80)
            
            for agent_id, agent_data in list(agents.items())[:10]:
                print(f"\n  {agent_id}")
                print(f"    Version: {agent_data.get('version')}")
                print(f"    Description: {agent_data.get('description', 'N/A')[:60]}...")
        
        return 0
    except Exception as e:
        print(f"❌ Failed to load agent config: {e}")
        return 1


def cmd_config_workflows(args):
    """Show workflow configurations (parity with web UI /config/workflows)."""
    from config import load_validated_config
    
    try:
        snapshot = load_validated_config()
        workflows = snapshot.main_config.get('workflows', {})
        
        if args.json:
            print(json.dumps({"workflow_count": len(workflows), "workflows": workflows}, indent=2))
        else:
            print(f"\n🔄 Workflow Configurations ({len(workflows)})")
            print("="*80)
            
            for workflow_name, workflow_data in workflows.items():
                print(f"\n  {workflow_name}")
                print(f"    Name: {workflow_data.get('name', workflow_name)}")
                print(f"    Steps: {len(workflow_data.get('steps', []))}")
        
        return 0
    except Exception as e:
        print(f"❌ Failed to load workflow config: {e}")
        return 1


def cmd_config_tone(args):
    """Show tone configurations (parity with web UI /config/tone)."""
    from config import load_validated_config
    
    try:
        snapshot = load_validated_config()
        tone_config = snapshot.tone_config
        
        if args.json:
            print(json.dumps({"global_voice": tone_config.get('global_voice', {})}, indent=2))
        else:
            print(f"\n✍️  Tone Configurations")
            print("="*80)
            
            global_voice = tone_config.get('global_voice', {})
            print(f"\n  Global Voice:")
            print(f"    POV: {global_voice.get('pov')}")
            print(f"    Formality: {global_voice.get('formality')}")
            print(f"    Technical Depth: {global_voice.get('technical_depth')}")
            print(f"    Personality: {global_voice.get('personality')}")
        
        return 0
    except Exception as e:
        print(f"❌ Failed to load tone config: {e}")
        return 1


def cmd_config_performance(args):
    """Show performance configurations (parity with web UI /config/performance)."""
    from config import load_validated_config
    
    try:
        snapshot = load_validated_config()
        perf_config = snapshot.perf_config
        
        if args.json:
            print(json.dumps({
                "timeouts": perf_config.get('timeouts', {}),
                "limits": perf_config.get('limits', {})
            }, indent=2))
        else:
            print(f"\n⚡ Performance Configurations")
            print("="*80)
            
            timeouts = perf_config.get('timeouts', {})
            print(f"\n  Timeouts:")
            for key, value in timeouts.items():
                print(f"    {key}: {value}s")
            
            limits = perf_config.get('limits', {})
            print(f"\n  Limits:")
            for key, value in limits.items():
                print(f"    {key}: {value}")
        
        return 0
    except Exception as e:
        print(f"❌ Failed to load performance config: {e}")
        return 1


def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(
        description='UCOP CLI - Unified Content Operations Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with topic
  ucop generate --template blog_standard --topic "Getting Started with Python"
  
  # Generate with context and auto-topic
  ucop generate --template blog_standard --auto-topic --kb ./knowledge --docs ./docs
  
  # Generate with all context sources
  ucop generate --template code_tutorial \
    --topic "API Usage" \
    --kb ./kb \
    --docs ./docs \
    --api ./api-ref \
    --blog ./existing-blogs
  
  # Batch generation
  ucop batch --template blog_standard --topics-file topics.txt
  
  # List templates
  ucop list-templates --type blog
  
  # Validate configuration
  ucop validate
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate content')
    gen_parser.add_argument('--template', default='default_blog', help='Template name')
    gen_parser.add_argument('--topic', help='Topic (or use --auto-topic)')
    gen_parser.add_argument('--auto-topic', action='store_true', help='Derive topic from context')
    gen_parser.add_argument('--kb', help='Knowledge base path')
    gen_parser.add_argument('--docs', help='Documentation path')
    gen_parser.add_argument('--blog', help='Blog content path')
    gen_parser.add_argument('--api', help='API reference path')
    gen_parser.add_argument('--tutorial', help='Tutorial path')
    gen_parser.add_argument('--output-dir', default='./output', help='Output directory')
    gen_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    gen_parser.set_defaults(func=cmd_generate)
    
    # List templates command
    list_parser = subparsers.add_parser('list-templates', help='List available templates')
    list_parser.add_argument('--type', choices=['blog', 'code', 'markdown', 'frontmatter'], 
                           help='Filter by template type')
    list_parser.set_defaults(func=cmd_list_templates)
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Execute batch job')
    batch_parser.add_argument('--template', default='default_blog', help='Template name')
    batch_parser.add_argument('--topics-file', required=True, help='File with topics (one per line)')
    batch_parser.add_argument('--kb', help='Knowledge base path')
    batch_parser.add_argument('--docs', help='Documentation path')
    batch_parser.add_argument('--blog', help='Blog content path')
    batch_parser.add_argument('--api', help='API reference path')
    batch_parser.add_argument('--tutorial', help='Tutorial path')
    batch_parser.add_argument('--output-dir', default='./output', help='Output directory')
    batch_parser.set_defaults(func=cmd_batch)
    
    # Validate command
    val_parser = subparsers.add_parser('validate', help='Validate configuration')
    val_parser.set_defaults(func=cmd_validate)
    
    # List jobs command (parity with web UI)
    jobs_parser = subparsers.add_parser('list-jobs', help='List all jobs')
    jobs_parser.add_argument('--json', action='store_true', help='Output as JSON')
    jobs_parser.set_defaults(func=cmd_list_jobs)
    
    # Get job command (parity with web UI)
    job_parser = subparsers.add_parser('get-job', help='Get job details')
    job_parser.add_argument('job_id', help='Job ID')
    job_parser.add_argument('--json', action='store_true', help='Output as JSON')
    job_parser.add_argument('--show-logs', action='store_true', help='Show agent logs')
    job_parser.set_defaults(func=cmd_get_job)
    
    # Config command (parity with web UI /config/* endpoints)
    config_parser = subparsers.add_parser('config', help='Configuration inspection commands')
    config_subparsers = config_parser.add_subparsers(dest='config_command', help='Config subcommands')
    
    # config snapshot
    config_snapshot_parser = config_subparsers.add_parser('snapshot', help='Show config snapshot')
    config_snapshot_parser.add_argument('--json', action='store_true', help='Output as JSON')
    config_snapshot_parser.set_defaults(func=cmd_config_snapshot)
    
    # config agents
    config_agents_parser = config_subparsers.add_parser('agents', help='Show agent configurations')
    config_agents_parser.add_argument('--json', action='store_true', help='Output as JSON')
    config_agents_parser.set_defaults(func=cmd_config_agents)
    
    # config workflows
    config_workflows_parser = config_subparsers.add_parser('workflows', help='Show workflow configurations')
    config_workflows_parser.add_argument('--json', action='store_true', help='Output as JSON')
    config_workflows_parser.set_defaults(func=cmd_config_workflows)
    
    # config tone
    config_tone_parser = config_subparsers.add_parser('tone', help='Show tone configurations')
    config_tone_parser.add_argument('--json', action='store_true', help='Output as JSON')
    config_tone_parser.set_defaults(func=cmd_config_tone)
    
    # config performance
    config_perf_parser = config_subparsers.add_parser('performance', help='Show performance configurations')
    config_perf_parser.add_argument('--json', action='store_true', help='Output as JSON')
    config_perf_parser.set_defaults(func=cmd_config_performance)
    
    # Visualization commands
    viz_parser = subparsers.add_parser('viz', help='Visualization and monitoring commands')
    viz_subparsers = viz_parser.add_subparsers(dest='viz_command', help='Visualization subcommands')
    
    # viz workflows
    viz_workflows_parser = viz_subparsers.add_parser('workflows', help='List workflow profiles')
    viz_workflows_parser.add_argument('--json', action='store_true', help='Output as JSON')
    viz_workflows_parser.set_defaults(func=cmd_viz_workflows)
    
    # viz graph
    viz_graph_parser = viz_subparsers.add_parser('graph', help='Generate workflow graph')
    viz_graph_parser.add_argument('profile', help='Workflow profile name')
    viz_graph_parser.add_argument('--json', action='store_true', help='Output as JSON')
    viz_graph_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    viz_graph_parser.set_defaults(func=cmd_viz_graph)
    
    # viz metrics
    viz_metrics_parser = viz_subparsers.add_parser('metrics', help='Get workflow metrics')
    viz_metrics_parser.add_argument('profile', help='Workflow profile name')
    viz_metrics_parser.add_argument('--json', action='store_true', help='Output as JSON')
    viz_metrics_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    viz_metrics_parser.set_defaults(func=cmd_viz_metrics)
    
    # viz agents
    viz_agents_parser = viz_subparsers.add_parser('agents', help='Show agent status')
    viz_agents_parser.add_argument('--json', action='store_true', help='Output as JSON')
    viz_agents_parser.set_defaults(func=cmd_viz_agents)
    
    # viz flows
    viz_flows_parser = viz_subparsers.add_parser('flows', help='Show active flows')
    viz_flows_parser.add_argument('--json', action='store_true', help='Output as JSON')
    viz_flows_parser.set_defaults(func=cmd_viz_flows)
    
    # viz bottlenecks
    viz_bottlenecks_parser = viz_subparsers.add_parser('bottlenecks', help='Detect bottlenecks')
    viz_bottlenecks_parser.add_argument('--json', action='store_true', help='Output as JSON')
    viz_bottlenecks_parser.set_defaults(func=cmd_viz_bottlenecks)
    
    # viz debug
    viz_debug_parser = viz_subparsers.add_parser('debug', help='Debug session management')
    viz_debug_parser.add_argument('action', choices=['create', 'list', 'breakpoint'], 
                                  help='Debug action')
    viz_debug_parser.add_argument('--correlation-id', help='Correlation ID for debug session')
    viz_debug_parser.add_argument('--session-id', help='Debug session ID')
    viz_debug_parser.add_argument('--agent-id', help='Agent ID for breakpoint')
    viz_debug_parser.add_argument('--event-type', help='Event type for breakpoint')
    viz_debug_parser.add_argument('--condition', help='Breakpoint condition')
    viz_debug_parser.add_argument('--json', action='store_true', help='Output as JSON')
    viz_debug_parser.set_defaults(func=cmd_viz_debug)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle viz subcommand
    if args.command == 'viz' and not hasattr(args, 'func'):
        viz_parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
