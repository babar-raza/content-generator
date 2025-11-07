#!/usr/bin/env python3
"""UCOP CLI - Unified command-line interface using the unified engine."""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.engine.unified_engine import get_engine, RunSpec, JobStatus
from src.core.template_registry import list_templates


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
        from src.core.config_validator import get_config
        
        config = get_config()
        
        print("✅ Configuration valid!")
        print(f"\n  Agent config: {len(config['agent']['agents'])} agents")
        print(f"  Performance config: loaded")
        print(f"  Tone config: loaded")
        
        # Validate templates
        from src.core.template_registry import get_template_registry
        
        registry = get_template_registry()
        print(f"  Templates: {len(registry.list_templates())} loaded")
        
        return 0
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
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
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
