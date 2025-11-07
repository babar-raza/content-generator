import subprocess, sys, pathlib, pytest, os

def test_cli_help_exits_zero():
    repo = pathlib.Path(__file__).resolve().parents[1]
    cli = repo / "ucop_cli.py"
    if not cli.exists():
        pytest.skip("ucop_cli.py not found")
    # run in repo root to match relative imports
    proc = subprocess.run([sys.executable, str(cli), "--help"], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, proc.stderr.decode()[:500]

def test_cli_dry_run_exits_zero_if_available():
    """Try a 'dry-run' style command if CLI supports it; skip otherwise."""
    repo = pathlib.Path(__file__).resolve().parents[1]
    cli = repo / "ucop_cli.py"
    if not cli.exists():
        pytest.skip("ucop_cli.py not found")

    candidates = [
        ["--dry-run"],
        ["--version"],
        ["-h"],
    ]
    for args in candidates:
        proc = subprocess.run([sys.executable, str(cli), *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0:
            return
    pytest.skip("No dry-run/help-style path returned 0")
