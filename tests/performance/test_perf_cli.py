import subprocess, sys, pathlib, pytest
from ._perf_utils import time_call, record_result

def _cli_path():
    repo = pathlib.Path(__file__).resolve().parents[2]
    for name in ["ucop_cli.py", "cli.py", "main.py"]:
        p = repo / name
        if p.exists():
            return p
    pytest.skip("No CLI entrypoint (ucop_cli.py/cli.py/main.py)")

def test_cli_help_latency():
    cli = _cli_path()
    timings = time_call(lambda: subprocess.run([sys.executable, str(cli), "--help"], cwd=cli.parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    res = record_result("cli", "help", timings)
    assert res["mean"] < 0.5, f"CLI --help too slow: {res['mean']:.3f}s"
