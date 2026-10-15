"""Installed identity query: `lbe --version` must not fall through to the legacy CLI parser."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_entry(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "lbe_guard_inspector.product_entry", *args],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
    )


def test_long_version_flag_reports_product_identity():
    result = run_entry("--version")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith("lbe")
    assert "usage:" not in result.stdout + result.stderr


def test_short_version_flag_reports_product_identity():
    result = run_entry("-V")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith("lbe")


def test_unknown_command_still_uses_cli_parser():
    result = run_entry("definitely-not-a-command")
    assert result.returncode != 0
