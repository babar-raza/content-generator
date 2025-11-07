#!/usr/bin/env python3
import os, subprocess, sys, pathlib

def main():
    repo = pathlib.Path(__file__).resolve().parents[1]
    os.makedirs(repo / "reports", exist_ok=True)
    env = os.environ.copy()
    env.setdefault("PERF_RESULTS_PATH", str(repo / "reports" / "perf_results.json"))
    env.setdefault("PERF_ITERS", "10")
    env.setdefault("PERF_WARMUP", "3")
    cmd = [sys.executable, "-m", "pytest", "-q", "tests/performance"]
    print("+", " ".join(cmd))
    code = subprocess.call(cmd, cwd=repo, env=env)
    print("+ python tools/perf_report.py")
    subprocess.call([sys.executable, "tools/perf_report.py"], cwd=repo, env=env)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
