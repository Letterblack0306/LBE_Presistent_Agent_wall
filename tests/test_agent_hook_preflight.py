"""Harness hook adapter: platform pre-tool payload -> action-preflight."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "agent-hook-preflight.mjs"
NL = chr(10)


def run_hook(payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        ["node", str(HOOK)], cwd=ROOT, input=raw,
        capture_output=True, text=True, timeout=30,
    )


def patch(*lines: str) -> str:
    return NL.join(("*** Begin Patch", *lines, "*** End Patch"))


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
    assert result.returncode in (0, 2)
    assert result.returncode == 0 or "BLOCK" in result.stderr


def test_codex_apply_patch_governed_paths_checked():
    protected = patch("*** Update File: .governance/task-scope.json", "@@", "-a", "+b")
    result = run_hook({"tool_name": "apply_patch", "tool_input": {"command": protected}, "cwd": str(ROOT)})
    assert result.returncode == 2
    assert "PROTECTED_PATH_REQUIRES_SEPARATE_AUTHORITY" in result.stderr


def test_codex_apply_patch_ordinary_file_allowed():
    text = patch("*** Add File: tools/new_probe.py", "+x = 1")
    result = run_hook({"tool_name": "apply_patch", "tool_input": {"command": text}, "cwd": str(ROOT)})
    assert result.returncode == 0, result.stderr


def test_gemini_write_file_protected_blocked_and_shell_commit_classified():
    blocked = run_hook({"tool_name": "write_file", "tool_input": {"file_path": ".governance/task-scope.json", "content": "x"}, "cwd": str(ROOT)})
    assert blocked.returncode == 2
    commit = run_hook({"tool_name": "run_shell_command", "tool_input": {"command": "git commit -m x"}, "cwd": str(ROOT)})
    assert commit.returncode == 0, commit.stderr


def test_relative_path_outside_workspace_passes_through():
    result = run_hook({"tool_name": "write_file", "tool_input": {"file_path": "../../outside.txt"}, "cwd": str(ROOT)})
    assert result.returncode == 0, result.stderr
