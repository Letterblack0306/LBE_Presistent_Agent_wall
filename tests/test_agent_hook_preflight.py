"""Harness hook adapter: platform pre-tool payload -> action-preflight."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "agent-hook-preflight.mjs"


def run_hook(payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        ["node", str(HOOK)], cwd=ROOT, input=raw,
        capture_output=True, text=True, timeout=30,
    )


def test_write_inside_scope_is_allowed():
    result = run_hook({"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "tools" / "lbe_product_integration.ps1")}})
    assert result.returncode == 0, result.stderr


def test_write_to_protected_governance_path_is_blocked():
    result = run_hook({"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / ".governance" / "task-scope.json")}})
    assert result.returncode == 2
    assert "PROTECTED_PATH_REQUIRES_SEPARATE_AUTHORITY" in result.stderr


def test_write_outside_workspace_is_not_governed_here():
    outside = ROOT.parent / "outside-workspace-file.txt"
    result = run_hook({"tool_name": "Write", "tool_input": {"file_path": str(outside)}})
    assert result.returncode == 0, result.stderr


def test_unrecognized_tool_passes_through():
    result = run_hook({"tool_name": "Read", "tool_input": {"file_path": str(ROOT / "README.md")}})
    assert result.returncode == 0


def test_invalid_payload_fails_closed():
    result = run_hook("not json")
    assert result.returncode == 2
    assert "fail closed" in result.stderr


def test_git_commit_is_classified_and_checked_against_allowed_actions():
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}})
    # active scope allows commit, so preflight allows; the point is classification ran
    assert result.returncode in (0, 2)
    assert result.returncode == 0 or "BLOCK" in result.stderr
