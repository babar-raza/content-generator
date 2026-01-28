"""Live Web + MCP E2E Test

Tests REST and MCP JSON-RPC endpoints with live executor.
"""
import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["TEST_MODE"] = "live"

from fastapi.testclient import TestClient
from tools.live_executor_factory import create_live_executor
from src.web.app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(report_dir):
    report_dir = Path(report_dir)
    results = {"rest": {}, "mcp": {}, "status": "UNKNOWN"}
    
    logger.info("=== PHASE 3: WEB + MCP E2E ===")
    
    # Create executor and app
    executor = create_live_executor()
    app = create_app(executor=executor)
    client = TestClient(app)
    
    # REST Tests
    logger.info("Testing REST endpoints...")
    
    # A) GET /api/agents
    resp = client.get("/api/agents")
    results["rest"]["agents"] = {
        "status": resp.status_code,
        "ok": resp.status_code == 200
    }
    logger.info(f"GET /api/agents: {resp.status_code}")
    
    # B) GET /api/workflows
    resp = client.get("/api/workflows")
    results["rest"]["workflows"] = {
        "status": resp.status_code,
        "ok": resp.status_code == 200
    }
    logger.info(f"GET /api/workflows: {resp.status_code}")
    
    # MCP Tests
    logger.info("Testing MCP endpoints...")
    
    # F) Single JSON-RPC
    mcp_req = {
        "jsonrpc": "2.0",
        "method": "workflows.list",
        "params": {},
        "id": 1
    }
    resp = client.post("/mcp/request", json=mcp_req)
    results["mcp"]["single"] = {
        "status": resp.status_code,
        "ok": resp.status_code == 200 and "result" in resp.json()
    }
    logger.info(f"MCP workflows.list: {resp.status_code}")
    
    # G) Batch JSON-RPC
    mcp_batch = [
        {"jsonrpc": "2.0", "method": "workflows.list", "params": {}, "id": 1},
        {"jsonrpc": "2.0", "method": "agents.list", "params": {}, "id": 2}
    ]
    resp = client.post("/mcp/request", json=mcp_batch)
    results["mcp"]["batch"] = {
        "status": resp.status_code,
        "ok": resp.status_code == 200 and isinstance(resp.json(), list)
    }
    logger.info(f"MCP batch: {resp.status_code}")
    
    # Overall status
    all_ok = all([
        results["rest"]["agents"]["ok"],
        results["rest"]["workflows"]["ok"],
        results["mcp"]["single"]["ok"],
        results["mcp"]["batch"]["ok"]
    ])
    
    results["status"] = "PASS" if all_ok else "FAIL"
    
    # Save results
    with open(report_dir / "web_mcp_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Summary
    with open(report_dir / "web_mcp_summary.md", "w") as f:
        f.write("# Web + MCP E2E Results\n\n")
        f.write(f"**Status**: {results['status']}\n\n")
        f.write("## REST Endpoints\n\n")
        for name, res in results["rest"].items():
            f.write(f"- {name}: {res['status']} {'PASS' if res['ok'] else 'FAIL'}\n")
        f.write("\n## MCP Endpoints\n\n")
        for name, res in results["mcp"].items():
            f.write(f"- {name}: {res['status']} {'PASS' if res['ok'] else 'FAIL'}\n")
    
    print(f"[{results['status']}] Web + MCP E2E completed")
    return 0 if results["status"] == "PASS" else 1

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--report-dir", required=True)
    args = p.parse_args()
    
    try:
        sys.exit(main(args.report_dir))
    except Exception as e:
        logger.error(f"[FAIL] {e}")
        sys.exit(1)
