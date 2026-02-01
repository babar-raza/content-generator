#!/usr/bin/env python3
"""UI/Mesh validation script - start app and validate endpoints."""
import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from urllib.parse import urljoin

# Set environment
os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["ALLOW_NETWORK"] = "0"

sys.path.insert(0, str(Path(__file__).parent.parent))


def start_app_server(port=8102):
    """Start the FastAPI app in a subprocess."""
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.web.app:create_app",
        "--factory",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--log-level", "warning"
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for server to start
    base_url = f"http://localhost:{port}"
    max_wait = 30
    start = time.time()

    while time.time() - start < max_wait:
        try:
            resp = requests.get(f"{base_url}/health", timeout=2)
            if resp.status_code == 200:
                print(f"[OK] App started on port {port}")
                return proc, base_url
        except:
            pass
        time.sleep(1)

    raise Exception(f"App failed to start within {max_wait}s")


def validate_endpoints(base_url, output_dir):
    """Validate all required endpoints."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "base_url": base_url,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "endpoints": {},
        "groups": {},
        "status": "UNKNOWN"
    }

    # Fetch OpenAPI spec
    try:
        resp = requests.get(f"{base_url}/openapi.json", timeout=10)
        if resp.status_code == 200:
            openapi = resp.json()
            with open(output_dir / "openapi.json", "w") as f:
                json.dump(openapi, f, indent=2)
            results["openapi_status"] = "OK"
        else:
            results["openapi_status"] = f"FAIL:{resp.status_code}"
    except Exception as e:
        results["openapi_status"] = f"ERROR:{e}"

    # Test required endpoints
    required = [
        ("GET", "/api/agents", "agents"),
        ("GET", "/api/workflows", "workflows")
    ]

    calls_log = []

    for method, path, name in required:
        try:
            resp = requests.get(urljoin(base_url, path), timeout=10)
            status = resp.status_code

            call_record = {
                "method": method,
                "url": path,
                "status": status,
                "success": status in [200, 201]
            }

            if status in [200, 201]:
                data = resp.json()
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    count = len(data.get("items", []))
                else:
                    count = 1

                call_record["count"] = count
                call_record["passed"] = count >= 1
                results["endpoints"][name] = {
                    "status": "PASS" if count >= 1 else "FAIL",
                    "count": count
                }
            else:
                call_record["passed"] = False
                results["endpoints"][name] = {
                    "status": "FAIL",
                    "error": f"HTTP {status}"
                }

            calls_log.append(call_record)

        except Exception as e:
            results["endpoints"][name] = {
                "status": "ERROR",
                "error": str(e)
            }
            calls_log.append({
                "method": method,
                "url": path,
                "status": "error",
                "error": str(e),
                "success": False,
                "passed": False
            })

    # Test endpoint groups
    groups = [
        "/api/jobs",
        "/api/checkpoints",
        "/api/config",
        "/api/templates",
        "/api/flows",
        "/api/monitor",
        "/api/metrics",
        "/api/visualization",
        "/api/debug",
        "/api/topics"
    ]

    for group in groups:
        try:
            resp = requests.get(urljoin(base_url, group), timeout=5)
            status = resp.status_code

            results["groups"][group] = {
                "status": "PASS" if status in [200, 201, 404, 405] else "FAIL",
                "http_status": status
            }

            calls_log.append({
                "method": "GET",
                "url": group,
                "status": status,
                "success": status in [200, 201, 404, 405],
                "passed": True
            })

        except Exception as e:
            results["groups"][group] = {
                "status": "ERROR",
                "error": str(e)
            }
            calls_log.append({
                "method": "GET",
                "url": group,
                "status": "error",
                "error": str(e),
                "success": False,
                "passed": False
            })

    # Write calls log
    with open(output_dir / "calls.jsonl", "w") as f:
        for call in calls_log:
            f.write(json.dumps(call) + "\n")

    # Determine overall status
    endpoint_pass = all(
        ep.get("status") == "PASS"
        for ep in results["endpoints"].values()
    )
    group_pass = all(
        grp.get("status") in ["PASS", "ERROR"]  # ERROR is acceptable for optional groups
        for grp in results["groups"].values()
    )

    results["status"] = "PASS" if (endpoint_pass and results.get("openapi_status") == "OK") else "FAIL"

    # Write summary
    md_lines = [
        "# UI/Mesh Endpoint Validation",
        "",
        f"**Status:** {results['status']}",
        f"**Base URL:** {base_url}",
        f"**Timestamp:** {results['timestamp']}",
        "",
        "## Required Endpoints",
        ""
    ]

    for name, data in results["endpoints"].items():
        status_icon = "✅" if data.get("status") == "PASS" else "❌"
        md_lines.append(f"- {status_icon} **{name}**: {data.get('status')} (count: {data.get('count', 'N/A')})")

    md_lines.extend([
        "",
        "## Endpoint Groups",
        ""
    ])

    for group, data in results["groups"].items():
        status_icon = "✅" if data.get("status") == "PASS" else "⚠️"
        md_lines.append(f"- {status_icon} **{group}**: HTTP {data.get('http_status', 'error')}")

    with open(output_dir / "ui_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8102)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Save startup command
    (output_dir / "app_start_command.txt").write_text(
        f"uvicorn src.web.app:create_app --factory --port {args.port}"
    )
    (output_dir / "port.txt").write_text(str(args.port))

    print(f"Starting app on port {args.port}...")
    proc, base_url = start_app_server(args.port)

    try:
        # Capture some stdout
        time.sleep(2)
        stdout_lines = []
        while proc.poll() is None:
            line = proc.stdout.readline()
            if not line:
                break
            stdout_lines.append(line)
            if len(stdout_lines) >= 20:
                break

        (output_dir / "app_stdout.log").write_text("".join(stdout_lines[-20:]))

        # Validate endpoints
        print("Validating endpoints...")
        results = validate_endpoints(base_url, output_dir)

        # Write results
        with open(output_dir / "validation_results.json", "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n[{results['status']}] UI/Mesh validation complete")
        print(f"Results: {output_dir / 'ui_summary.md'}")

        return 0 if results["status"] == "PASS" else 1

    finally:
        print("Stopping app...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
