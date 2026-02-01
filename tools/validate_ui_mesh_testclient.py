#!/usr/bin/env python3
"""UI/Mesh validation using TestClient (faster, no real server needed)."""
import os
import sys
import json
import time
from pathlib import Path

os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["ALLOW_NETWORK"] = "0"

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from tools.live_e2e.executor_factory import create_live_executor
from src.web.app import create_app


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--collection", default="aspose_kb_20260131-0256")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Creating executor and app...")
    executor = create_live_executor(
        blog_collection=args.collection,
        ref_collection=args.collection
    )

    app = create_app(executor=executor)
    client = TestClient(app)

    print("App created with TestClient")

    # Save app info
    (output_dir / "app_start_command.txt").write_text("TestClient (no real server)")
    (output_dir / "port.txt").write_text("N/A (TestClient)")
    (output_dir / "app_stdout.log").write_text("Using FastAPI TestClient\n")

    results = {
        "mode": "TestClient",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "endpoints": {},
        "groups": {},
        "status": "UNKNOWN"
    }

    calls_log = []

    # Fetch OpenAPI
    try:
        resp = client.get("/openapi.json")
        if resp.status_code == 200:
            openapi = resp.json()
            with open(output_dir / "openapi.json", "w") as f:
                json.dump(openapi, f, indent=2)
            results["openapi"] = "OK"
            print(f"[OK] OpenAPI spec retrieved ({len(openapi.get('paths', {}))} paths)")
        else:
            results["openapi"] = f"FAIL:{resp.status_code}"
    except Exception as e:
        results["openapi"] = f"ERROR:{e}"

    # Test required endpoints
    required = [
        ("GET", "/api/agents"),
        ("GET", "/api/workflows")
    ]

    for method, path in required:
        try:
            resp = client.get(path)
            status = resp.status_code

            call_record = {
                "method": method,
                "url": path,
                "status": status
            }

            if status in [200, 201]:
                data = resp.json()
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    count = len(data.get("items", data.get("agents", data.get("workflows", []))))
                else:
                    count = 1

                call_record["count"] = count
                call_record["passed"] = count >= 1
                results["endpoints"][path] = {
                    "status": "PASS" if count >= 1 else "FAIL",
                    "count": count
                }
                print(f"[{'PASS' if count >= 1 else 'FAIL'}] {path}: {count} items")
            else:
                results["endpoints"][path] = {
                    "status": "FAIL",
                    "http_status": status
                }
                print(f"[FAIL] {path}: HTTP {status}")

            calls_log.append(call_record)

        except Exception as e:
            results["endpoints"][path] = {"status": "ERROR", "error": str(e)}
            print(f"[ERROR] {path}: {e}")

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
            resp = client.get(group)
            status = resp.status_code

            results["groups"][group] = {
                "status": "PASS" if status in [200, 201, 404, 405] else "FAIL",
                "http_status": status
            }

            calls_log.append({
                "method": "GET",
                "url": group,
                "status": status
            })

            print(f"  {group}: HTTP {status}")

        except Exception as e:
            results["groups"][group] = {"status": "ERROR", "error": str(e)}
            print(f"  {group}: ERROR {e}")

    # Write calls log
    with open(output_dir / "calls.jsonl", "w") as f:
        for call in calls_log:
            f.write(json.dumps(call) + "\n")

    # Determine overall status
    endpoint_pass = all(
        ep.get("status") == "PASS"
        for ep in results["endpoints"].values()
    )

    results["status"] = "PASS" if (endpoint_pass and results.get("openapi") == "OK") else "FAIL"

    # Write summary
    md_lines = [
        "# UI/Mesh Endpoint Validation (TestClient)",
        "",
        f"**Status:** {results['status']}",
        f"**Mode:** TestClient",
        f"**Timestamp:** {results['timestamp']}",
        "",
        "## Required Endpoints",
        ""
    ]

    for path, data in results["endpoints"].items():
        status_icon = "✅" if data.get("status") == "PASS" else "❌"
        count = data.get("count", "N/A")
        md_lines.append(f"- {status_icon} **{path}**: {data.get('status')} (count: {count})")

    md_lines.extend(["", "## Endpoint Groups", ""])

    for group, data in results["groups"].items():
        status_icon = "✅" if data.get("status") == "PASS" else "⚠️"
        md_lines.append(f"- {status_icon} **{group}**: HTTP {data.get('http_status', 'error')}")

    with open(output_dir / "ui_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    with open(output_dir / "validation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[{results['status']}] UI/Mesh validation complete")
    print(f"Results: {output_dir / 'ui_summary.md'}")

    return 0 if results["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
