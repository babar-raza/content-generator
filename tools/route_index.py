"""Route index generator - extracts API contract from running FastAPI app.

This tool is the source of truth for what endpoints actually exist.
It extracts the OpenAPI schema and app.routes to help align tests with reality.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment for safe operation
os.environ['TEST_MODE'] = 'mock'
os.environ.setdefault('CONFIG_PATH', 'config.yaml')


def get_karachi_time():
    """Get current time in Asia/Karachi (UTC+5)."""
    utc_now = datetime.utcnow()
    karachi_time = utc_now + timedelta(hours=5)
    return karachi_time.strftime('%Y%m%d-%H%M')


def extract_openapi_routes(app):
    """Extract routes from OpenAPI schema.

    Args:
        app: FastAPI application instance

    Returns:
        tuple: (openapi_schema dict, routes_by_prefix dict)
    """
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Try to get OpenAPI schema via HTTP first
    try:
        response = client.get("/openapi.json")
        if response.status_code == 200:
            openapi_schema = response.json()
        else:
            # Fallback to direct OpenAPI method
            openapi_schema = app.openapi()
    except Exception as e:
        print(f"Warning: Failed to get OpenAPI via HTTP ({e}), using direct method")
        openapi_schema = app.openapi()

    # Group paths by prefix
    routes_by_prefix = defaultdict(list)

    if 'paths' in openapi_schema:
        for path, methods in openapi_schema['paths'].items():
            # Determine prefix
            if path.startswith('/api/'):
                parts = path.split('/')
                if len(parts) >= 3:
                    prefix = f"/{parts[1]}/{parts[2]}"
                else:
                    prefix = f"/{parts[1]}"
            elif path.startswith('/mcp'):
                prefix = '/mcp'
            elif path == '/' or path == '/health' or path == '/docs' or path == '/redoc':
                prefix = '/root'
            else:
                prefix = '/other'

            # Extract methods and operations
            route_info = {
                'path': path,
                'methods': []
            }

            for method, operation in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']:
                    method_info = {
                        'method': method.upper(),
                        'operation_id': operation.get('operationId', ''),
                        'summary': operation.get('summary', ''),
                        'tags': operation.get('tags', [])
                    }
                    route_info['methods'].append(method_info)

            routes_by_prefix[prefix].append(route_info)

    return openapi_schema, routes_by_prefix


def extract_app_routes(app):
    """Extract routes directly from app.routes.

    Args:
        app: FastAPI application instance

    Returns:
        list: List of route information dicts
    """
    routes = []

    for route in app.routes:
        route_info = {
            'path': getattr(route, 'path', None),
            'name': getattr(route, 'name', None),
            'methods': list(getattr(route, 'methods', [])) if hasattr(route, 'methods') else []
        }

        # Add route type
        route_info['type'] = type(route).__name__

        routes.append(route_info)

    return routes


def generate_markdown_report(routes_by_prefix, openapi_schema):
    """Generate markdown report of routes grouped by prefix.

    Args:
        routes_by_prefix: Dict of routes grouped by prefix
        openapi_schema: Full OpenAPI schema

    Returns:
        str: Markdown formatted report
    """
    lines = []
    lines.append("# UCOP API Route Index")
    lines.append(f"\nGenerated: {datetime.utcnow().isoformat()}Z")
    lines.append(f"\nAPI Title: {openapi_schema.get('info', {}).get('title', 'Unknown')}")
    lines.append(f"API Version: {openapi_schema.get('info', {}).get('version', 'Unknown')}")
    lines.append("\n---\n")

    # Count total endpoints
    total_paths = sum(len(routes) for routes in routes_by_prefix.values())
    total_methods = sum(
        len(route['methods'])
        for routes in routes_by_prefix.values()
        for route in routes
    )

    lines.append(f"**Total Paths**: {total_paths}")
    lines.append(f"**Total Methods**: {total_methods}\n")

    # Sort prefixes
    sorted_prefixes = sorted(routes_by_prefix.keys())

    for prefix in sorted_prefixes:
        routes = routes_by_prefix[prefix]
        lines.append(f"\n## {prefix}")
        lines.append(f"\n{len(routes)} path(s)\n")

        for route in sorted(routes, key=lambda r: r['path']):
            lines.append(f"\n### `{route['path']}`\n")

            for method_info in route['methods']:
                method = method_info['method']
                summary = method_info['summary']
                operation_id = method_info['operation_id']

                lines.append(f"- **{method}**")
                if summary:
                    lines.append(f" - {summary}")
                if operation_id:
                    lines.append(f" (operation: `{operation_id}`)")
                lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    print("=" * 60)
    print("UCOP Route Index Generator")
    print("=" * 60)

    # Get timestamp
    ts = get_karachi_time()
    print(f"\nTimestamp: {ts}")

    # Output directory
    output_dir = project_root / "reports" / "wave2_align" / ts / "01_routes"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Import and create app
    print("\nImporting FastAPI app...")
    try:
        from src.web.app import create_app
        app = create_app()  # Create without executor for route inspection
        print(f"[OK] App created successfully")
    except Exception as e:
        print(f"[ERROR] Failed to create app: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Extract OpenAPI routes
    print("\nExtracting OpenAPI schema...")
    try:
        openapi_schema, routes_by_prefix = extract_openapi_routes(app)
        print(f"[OK] Found {len(openapi_schema.get('paths', {}))} paths in OpenAPI schema")
    except Exception as e:
        print(f"[ERROR] Failed to extract OpenAPI routes: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Extract app routes
    print("Extracting app.routes...")
    try:
        app_routes = extract_app_routes(app)
        print(f"[OK] Found {len(app_routes)} routes in app.routes")
    except Exception as e:
        print(f"[ERROR] Failed to extract app routes: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Save OpenAPI paths JSON
    openapi_paths_file = output_dir / "openapi_paths.json"
    print(f"\nSaving OpenAPI paths to {openapi_paths_file.name}...")
    with open(openapi_paths_file, 'w') as f:
        json.dump(openapi_schema.get('paths', {}), f, indent=2)
    print(f"[OK] Saved")

    # Save OpenAPI full schema
    openapi_full_file = output_dir / "openapi_schema.json"
    print(f"Saving full OpenAPI schema to {openapi_full_file.name}...")
    with open(openapi_full_file, 'w') as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"[OK] Saved")

    # Save app routes JSON
    app_routes_file = output_dir / "app_routes.json"
    print(f"Saving app routes to {app_routes_file.name}...")
    with open(app_routes_file, 'w') as f:
        json.dump(app_routes, f, indent=2)
    print(f"[OK] Saved")

    # Generate and save markdown report
    markdown_file = output_dir / "openapi_paths.md"
    print(f"Generating markdown report to {markdown_file.name}...")
    markdown_content = generate_markdown_report(routes_by_prefix, openapi_schema)
    with open(markdown_file, 'w') as f:
        f.write(markdown_content)
    print(f"[OK] Saved")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"OpenAPI paths: {len(openapi_schema.get('paths', {}))}")
    print(f"App routes: {len(app_routes)}")
    print(f"\nRoute prefixes found:")
    for prefix in sorted(routes_by_prefix.keys()):
        count = len(routes_by_prefix[prefix])
        print(f"  {prefix}: {count} path(s)")

    print(f"\n[OK] Route index generation complete!")
    print(f"[OK] Outputs saved to: {output_dir}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
