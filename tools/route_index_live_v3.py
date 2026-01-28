"""Route index generator for live_e2e_full_v3 - extracts API contract."""

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


def extract_openapi_routes(app):
    """Extract routes from OpenAPI schema."""
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Try to get OpenAPI schema via HTTP first
    try:
        response = client.get("/openapi.json")
        if response.status_code == 200:
            openapi_schema = response.json()
        else:
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
    """Extract routes directly from app.routes."""
    routes = []

    for route in app.routes:
        route_info = {
            'path': getattr(route, 'path', None),
            'name': getattr(route, 'name', None),
            'methods': list(getattr(route, 'methods', [])) if hasattr(route, 'methods') else [],
            'type': type(route).__name__
        }
        routes.append(route_info)

    return routes


def generate_markdown_report(routes_by_prefix, openapi_schema):
    """Generate markdown report of routes grouped by prefix."""
    lines = []
    lines.append("# API Route Index - Live E2E Full V3")
    lines.append(f"\nGenerated: {datetime.utcnow().isoformat()}Z")
    lines.append(f"\nAPI Title: {openapi_schema.get('info', {}).get('title', 'Unknown')}")
    lines.append(f"API Version: {openapi_schema.get('info', {}).get('version', 'Unknown')}")
    lines.append("\n---\n")

    total_paths = sum(len(routes) for routes in routes_by_prefix.values())
    total_methods = sum(
        len(route['methods'])
        for routes in routes_by_prefix.values()
        for route in routes
    )

    lines.append(f"**Total Paths**: {total_paths}")
    lines.append(f"**Total Methods**: {total_methods}\n")

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
    if len(sys.argv) < 2:
        print("Usage: python route_index_live_v3.py <output_dir>")
        return 1

    output_dir = Path(sys.argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Route Index Generator - Live E2E Full V3")
    print("=" * 60)
    print(f"Output directory: {output_dir}\n")

    # Import and create app
    print("Importing FastAPI app...")
    try:
        from src.web.app import create_app
        app = create_app()
        print("[OK] App created successfully\n")
    except Exception as e:
        print(f"[ERROR] Failed to create app: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Extract OpenAPI routes
    print("Extracting OpenAPI schema...")
    try:
        openapi_schema, routes_by_prefix = extract_openapi_routes(app)
        print(f"[OK] Found {len(openapi_schema.get('paths', {}))} paths\n")
    except Exception as e:
        print(f"[ERROR] Failed to extract OpenAPI routes: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Extract app routes
    print("Extracting app.routes...")
    try:
        app_routes = extract_app_routes(app)
        print(f"[OK] Found {len(app_routes)} routes\n")
    except Exception as e:
        print(f"[ERROR] Failed to extract app routes: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Save outputs
    print("Saving outputs...")

    # routes_app.json
    with open(output_dir / "routes_app.json", 'w') as f:
        json.dump(app_routes, f, indent=2)
    print(f"[OK] routes_app.json")

    # routes_openapi.json
    with open(output_dir / "routes_openapi.json", 'w') as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"[OK] routes_openapi.json")

    # routes_summary.md
    markdown_content = generate_markdown_report(routes_by_prefix, openapi_schema)
    with open(output_dir / "routes_summary.md", 'w') as f:
        f.write(markdown_content)
    print(f"[OK] routes_summary.md")

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

    # Check for /api/jobs
    print("\n" + "=" * 60)
    print("KEY ENDPOINTS CHECK")
    print("=" * 60)
    paths = openapi_schema.get('paths', {})

    if '/api/jobs' in paths:
        print("[OK] /api/jobs exists")
        methods = [m.upper() for m in paths['/api/jobs'].keys() if m.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']]
        print(f"    Methods: {', '.join(methods)}")
    else:
        print("[WARN] /api/jobs NOT found")

    jobs_id_path = None
    for path in paths:
        if path.startswith('/api/jobs/') and '{' in path:
            jobs_id_path = path
            break

    if jobs_id_path:
        print(f"[OK] {jobs_id_path} exists")
        methods = [m.upper() for m in paths[jobs_id_path].keys() if m.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']]
        print(f"    Methods: {', '.join(methods)}")
    else:
        print("[WARN] /api/jobs/{id} NOT found")

    if '/mcp/request' in paths:
        print("[OK] /mcp/request exists")
    else:
        print("[WARN] /mcp/request NOT found")

    print(f"\n[OK] Route index generation complete!")

    return 0


if __name__ == '__main__':
    sys.exit(main())
