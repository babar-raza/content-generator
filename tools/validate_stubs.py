#!/usr/bin/env python3
"""Validate stub servers for external integrations."""
import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path


def test_stub(name, port, test_func):
    """Test a stub server."""
    print(f"\n[Testing] {name} stub on port {port}")

    # Start stub server
    stub_script = f"tools/stubs/{name}_stub.py"
    proc = subprocess.Popen(
        [sys.executable, stub_script, str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for startup
    time.sleep(2)

    try:
        # Run test function
        result = test_func(port)
        print(f"[{'PASS' if result['passed'] else 'FAIL'}] {name}: {result.get('message', '')}")
        return result
    finally:
        # Stop stub
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except:
            proc.kill()


def test_gist_stub(port):
    """Test GitHub Gist stub."""
    base_url = f"http://localhost:{port}"

    try:
        # Test POST /gists
        resp = requests.post(
            f"{base_url}/gists",
            json={
                "description": "Test gist",
                "public": True,
                "files": {"test.md": {"content": "# Test"}}
            },
            timeout=5
        )

        if resp.status_code == 201:
            data = resp.json()
            if data.get("id") and data.get("html_url"):
                return {"passed": True, "message": f"Created gist {data['id']}", "data": data}

        return {"passed": False, "message": f"HTTP {resp.status_code}"}

    except Exception as e:
        return {"passed": False, "message": str(e)}


def test_trends_stub(port):
    """Test Trends stub."""
    try:
        resp = requests.get(f"http://localhost:{port}/trends", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "trending_searches" in data:
                return {"passed": True, "message": f"{len(data['trending_searches'])} trends", "data": data}

        return {"passed": False, "message": f"HTTP {resp.status_code}"}

    except Exception as e:
        return {"passed": False, "message": str(e)}


def test_competitor_stub(port):
    """Test Competitor stub."""
    try:
        resp = requests.get(f"http://localhost:{port}/competitors", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "competitors" in data:
                return {"passed": True, "message": f"{len(data['competitors'])} competitors", "data": data}

        return {"passed": False, "message": f"HTTP {resp.status_code}"}

    except Exception as e:
        return {"passed": False, "message": str(e)}


def test_link_validation_stub(port):
    """Test Link Validation stub."""
    try:
        resp = requests.post(
            f"http://localhost:{port}/validate",
            json={"links": ["https://example.com", "https://test.com"]},
            timeout=5
        )

        if resp.status_code == 200:
            data = resp.json()
            if "total_links" in data and "results" in data:
                return {"passed": True, "message": f"Validated {data['total_links']} links", "data": data}

        return {"passed": False, "message": f"HTTP {resp.status_code}"}

    except Exception as e:
        return {"passed": False, "message": str(e)}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("STUB VALIDATION")
    print("="*80)

    # Test each stub
    stubs = [
        ("github_gist", 8201, test_gist_stub),
        ("trends", 8202, test_trends_stub),
        ("competitor", 8203, test_competitor_stub),
        ("link_validation", 8204, test_link_validation_stub)
    ]

    results = {}
    all_logs = []

    for name, port, test_func in stubs:
        result = test_stub(name, port, test_func)
        results[name] = result
        all_logs.append({
            "stub": name,
            "port": port,
            "passed": result.get("passed", False),
            "message": result.get("message", ""),
            "data": result.get("data")
        })

    # Save results
    with open(output_dir / "stub_verification.json", "w") as f:
        json.dump({"stubs": results, "logs": all_logs}, f, indent=2)

    # Write markdown summary
    md_lines = [
        "# Stub Integration Verification",
        "",
        f"**Total Stubs:** {len(stubs)}",
        f"**Passed:** {sum(1 for r in results.values() if r.get('passed'))}",
        f"**Failed:** {sum(1 for r in results.values() if not r.get('passed'))}",
        "",
        "## Results",
        ""
    ]

    for name, result in results.items():
        status_icon = "✅" if result.get("passed") else "❌"
        md_lines.append(f"- {status_icon} **{name}**: {result.get('message', 'N/A')}")

    with open(output_dir / "stub_verification.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Determine overall status
    all_passed = all(r.get("passed", False) for r in results.values())
    status = "PASS" if all_passed else "FAIL"

    print(f"\n{'='*80}")
    print(f"[{status}] Stub validation complete: {sum(1 for r in results.values() if r.get('passed'))}/{len(stubs)} passed")
    print(f"Results: {output_dir / 'stub_verification.md'}")
    print(f"{'='*80}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
