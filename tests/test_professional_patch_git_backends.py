from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.professional_patch_git_backends import (
    register_patch_and_blame_backends,
)
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
)


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "LBE Test")
    (root / "README.md").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "initial")
    return root


def _context(root: Path, *, mode: str = "coding") -> ToolExecutionContext:
    caps = ("inspect", "modify") if mode == "coding" else ("inspect",)
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode=mode,
            allowed_behaviors=("development_mode_capabilities",) if mode == "coding" else ("audit_mode_constraints",),
            capabilities=caps,
            rationale="test",
        ),
        workspace_id="workspace-1",
        workspace_root=root,
        configured_root_id="dev",
    )


def _runtime():
    registry = ToolRegistry()
    specs = register_patch_and_blame_backends(registry=registry)
    return GovernedToolOrchestrator(registry=registry), specs


def test_registers_exact_remaining_backends() -> None:
    _, specs = _runtime()
    assert tuple(spec.tool_id for spec in specs) == ("workspace.apply_patch", "git.blame")
    assert specs[0].capability == "modify"
    assert specs[1].capability == "inspect"


def test_apply_patch_reuses_exact_text_mutation_with_hash_guard(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    target = root / "README.md"
    before = target.read_bytes()
    expected = hashlib.sha256(before).hexdigest()
    orchestrator, _ = _runtime()

    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-patch",
        tool_id="workspace.apply_patch",
        arguments={
            "path": "README.md",
            "old_text": "beta\n",
            "new_text": "BETA\n",
            "expected_before_sha256": expected,
        },
        context=_context(root),
    ))

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert target.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"
    assert receipt.output and receipt.output["patch_kind"] == "exact_text_replacement"
    assert receipt.output["before_sha256"] == expected
    assert receipt.evidence and receipt.evidence[0]["tool_id"] == "workspace.apply_patch"


def test_apply_patch_fails_closed_on_stale_hash_without_mutation(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    target = root / "README.md"
    before = target.read_text(encoding="utf-8")
    orchestrator, _ = _runtime()

    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-stale",
        tool_id="workspace.apply_patch",
        arguments={
            "path": "README.md",
            "old_text": "beta\n",
            "new_text": "BETA\n",
            "expected_before_sha256": "0" * 64,
        },
        context=_context(root),
    ))

    assert receipt.status is ToolReceiptStatus.FAILED
    assert "stale before hash" in (receipt.error_message or "")
    assert target.read_text(encoding="utf-8") == before


def test_apply_patch_rejects_escape_and_audit_write(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    orchestrator, _ = _runtime()
    escaped = orchestrator.invoke(ToolRequest(
        operation_id="op-escape",
        tool_id="workspace.apply_patch",
        arguments={"path": "../outside.txt", "old_text": "x", "new_text": "y"},
        context=_context(root),
    ))
    audit = orchestrator.invoke(ToolRequest(
        operation_id="op-audit",
        tool_id="workspace.apply_patch",
        arguments={"path": "README.md", "old_text": "beta", "new_text": "BETA"},
        context=_context(root, mode="audit"),
    ))
    assert escaped.status is ToolReceiptStatus.FAILED
    assert audit.status is ToolReceiptStatus.ESCALATED


def test_git_blame_is_bounded_read_with_line_range(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    orchestrator, _ = _runtime()
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-blame",
        tool_id="git.blame",
        arguments={"path": "README.md", "revision": "HEAD", "start_line": 2, "end_line": 2},
        context=_context(root),
    ))

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output is not None
    assert receipt.output["path"] == "README.md"
    assert receipt.output["revision"] == "HEAD"
    assert receipt.output["start_line"] == 2
    assert receipt.output["end_line"] == 2
    assert "summary initial" in receipt.output["text"]
    assert _git(root, "status", "--porcelain=v1") == ""


def test_git_blame_rejects_escape_revision_options_and_unbounded_ranges(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    orchestrator, _ = _runtime()
    requests = (
        {"path": "../README.md"},
        {"path": "README.md", "revision": "--contents"},
        {"path": "README.md", "start_line": 1, "end_line": 501},
    )
    for index, arguments in enumerate(requests):
        receipt = orchestrator.invoke(ToolRequest(
            operation_id=f"op-invalid-{index}",
            tool_id="git.blame",
            arguments=arguments,
            context=_context(root),
        ))
        assert receipt.status is ToolReceiptStatus.FAILED
