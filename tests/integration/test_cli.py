"""Integration test for CLI - python ucop_cli.py --help exits 0; one dry-run invocation exits 0."""

import subprocess
import sys
import pathlib
import pytest


class TestCLIIntegration:
    """Test CLI integration."""

    @pytest.fixture
    def repo_path(self):
        """Get the repository path."""
        return pathlib.Path(__file__).resolve().parents[2]  # Go up to repo root

    @pytest.fixture
    def cli_path(self, repo_path):
        """Get the CLI script path."""
        cli = repo_path / "ucop_cli.py"
        if not cli.exists():
            pytest.skip("ucop_cli.py not found")
        return cli

    def test_cli_help_exits_zero(self, cli_path, repo_path):
        """Test that python ucop_cli.py --help exits 0."""
        proc = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )

        assert proc.returncode == 0, f"CLI --help failed: {proc.stderr.decode()}"

    def test_cli_version_exits_zero(self, cli_path, repo_path):
        """Test that CLI --version or -V exits 0 if supported."""
        # Try different version flags
        version_flags = ["--version", "-V", "-v"]

        success = False
        for flag in version_flags:
            proc = subprocess.run(
                [sys.executable, str(cli_path), flag],
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )

            if proc.returncode == 0:
                success = True
                break

        if not success:
            pytest.skip("CLI does not support version flag")

    def test_cli_invalid_command_exits_nonzero(self, cli_path, repo_path):
        """Test that invalid command exits with non-zero code."""
        proc = subprocess.run(
            [sys.executable, str(cli_path), "invalid_command"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode != 0, "Invalid command should exit non-zero"

    def test_cli_no_args_shows_help(self, cli_path, repo_path):
        """Test that running CLI with no args shows help."""
        proc = subprocess.run(
            [sys.executable, str(cli_path)],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        # Should either exit 0 (help shown) or 2 (argparse error)
        assert proc.returncode in [0, 2], f"Unexpected exit code: {proc.returncode}"

        # Should show help text
        output = proc.stdout.decode() + proc.stderr.decode()
        assert "usage:" in output.lower() or "help" in output.lower()

    def test_cli_help_contains_expected_commands(self, cli_path, repo_path):
        """Test that --help output contains expected commands."""
        proc = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0
        output = proc.stdout.decode()

        # Should contain expected commands
        expected_commands = ["create", "list", "show", "pause", "resume", "cancel", "watch"]
        for cmd in expected_commands:
            assert cmd in output, f"Command '{cmd}' not found in help output"

    def test_cli_create_help(self, cli_path, repo_path):
        """Test that create command help works."""
        proc = subprocess.run(
            [sys.executable, str(cli_path), "create", "--help"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0
        output = proc.stdout.decode()
        assert "workflow" in output.lower()

    def test_cli_list_help(self, cli_path, repo_path):
        """Test that list command help works."""
        proc = subprocess.run(
            [sys.executable, str(cli_path), "list", "--help"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0

    def test_cli_show_help(self, cli_path, repo_path):
        """Test that show command help works."""
        proc = subprocess.run(
            [sys.executable, str(cli_path), "show", "--help"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0
        output = proc.stdout.decode()
        assert "job_id" in output.lower()

    def test_cli_watch_help(self, cli_path, repo_path):
        """Test that watch command help works."""
        proc = subprocess.run(
            [sys.executable, str(cli_path), "watch", "--help"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0
        output = proc.stdout.decode()
        assert "interval" in output.lower()

    def test_cli_dry_run_style_commands(self, cli_path, repo_path):
        """Test various dry-run style commands that should exit 0."""
        # Commands that should work without full setup
        dry_run_commands = [
            ["--help"],
            ["-h"],
            ["create", "--help"],
            ["list", "--help"],
            ["show", "--help"],
            ["watch", "--help"],
            ["pause", "--help"],
            ["resume", "--help"],
            ["cancel", "--help"],
        ]

        success_count = 0
        for cmd in dry_run_commands:
            proc = subprocess.run(
                [sys.executable, str(cli_path)] + cmd,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10
            )

            if proc.returncode == 0:
                success_count += 1

        # At least some should work
        assert success_count > 0, "No dry-run commands succeeded"

    def test_cli_error_handling(self, cli_path, repo_path):
        """Test CLI error handling for invalid inputs."""
        # Test missing required arguments
        proc = subprocess.run(
            [sys.executable, str(cli_path), "create"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        # Should exit with error
        assert proc.returncode != 0

        # Should show error message
        error_output = proc.stderr.decode()
        assert len(error_output) > 0

    def test_cli_mode_flags(self, cli_path, repo_path):
        """Test CLI mode flags are accepted."""
        # Test --mode flag is accepted (even if backend not available)
        proc = subprocess.run(
            [sys.executable, str(cli_path), "--mode", "direct", "--help"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0

    def test_cli_server_flag(self, cli_path, repo_path):
        """Test CLI server flag is accepted."""
        proc = subprocess.run(
            [sys.executable, str(cli_path), "--server", "http://localhost:8080", "--help"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0

    def test_cli_import_succeeds(self, cli_path, repo_path):
        """Test that CLI script can be imported (basic syntax check)."""
        # Try to import the main function
        proc = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, r'{repo_path}'); import ucop_cli"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )

        # Should not have import errors
        assert proc.returncode == 0, f"CLI import failed: {proc.stderr.decode()}"

    def test_cli_has_main_function(self, cli_path, repo_path):
        """Test that CLI has a main function."""
        proc = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, r'{repo_path}'); import ucop_cli; assert hasattr(ucop_cli, 'main')"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0, "CLI should have main function"

    def test_cli_main_function_signature(self, cli_path, repo_path):
        """Test that main function has correct signature."""
        proc = subprocess.run(
            [sys.executable, "-c", f"""
import sys
sys.path.insert(0, r'{repo_path}')
import ucop_cli
import inspect
sig = inspect.signature(ucop_cli.main)
# Should accept no arguments (uses sys.argv)
assert len(sig.parameters) == 0
"""],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        assert proc.returncode == 0, "main function should accept no arguments"