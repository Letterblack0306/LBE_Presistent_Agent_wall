from __future__ import annotations

import subprocess
from pathlib import Path

from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.professional_capability_backends import (
    git_diff_spec,
    git_show_spec,
    register_workspace_and_git_backends,
    workspace_glob_spec,
    workspace_search_spec,
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
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("def greet():\n    return 'hello workspace'\n", encoding="utf-8")
    _git(root, "add", "README.md", "src/main.py")
    _git(root, "commit", "-m", "initial")
    return root


def _context(root: Path) -> ToolExecutionContext:
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode="coding",
            allowed_behaviors=("development_mode_capabilities",),
            capabilities=("inspect", "modify"),
            rationale="test",
        ),
        workspace_id="workspace-1",
        workspace_root=root,
        configured_root_id="dev",
    )


def _runtime(root: Path):
    registry = ToolRegistry()
    specs = register_workspace_and_git_backends(registry=registry, evidence_service=EvidenceService())
    return registry, GovernedToolOrchestrator(registry=registry), specs


def test_registry_composes_existing_workspace_and_typed_git_backends(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    registry, _, specs = _runtime(root)
    ids = tuple(spec.tool_id for spec in specs)
    assert ids == (
        "workspace.read",
        "workspace.search",
        "workspace.glob",
        "workspace.inspect",
        "workspace.diff",
        "workspace.replace_text",
        "git.status",
        "git.diff",
        "git.log",
        "git.show",
        "git.branch",
        "git.remote",
        "git.worktree.list",
    )
    assert tuple(spec.tool_id for spec in registry.specs()) == tuple(sorted(ids))
    assert all(spec.capability in {"inspect", "modify"} for spec in specs)


def test_workspace_search_glob_and_inspect_are_bounded_reads(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _, orchestrator, _ = _runtime(root)
    context = _context(root)

    search = orchestrator.invoke(ToolRequest(
        operation_id="op-search",
        tool_id="workspace.search",
        arguments={"query": "hello workspace", "path": "src", "max_results": 10},
        context=context,
    ))
    globbed = orchestrator.invoke(ToolRequest(
        operation_id="op-glob",
        tool_id="workspace.glob",
        arguments={"pattern": "src/*.py", "max_results": 10},
        context=context,
    ))
    inspected = orchestrator.invoke(ToolRequest(
        operation_id="op-inspect",
        tool_id="workspace.inspect",
        arguments={"path": "src/main.py"},
        context=context,
    ))

    assert search.status is ToolReceiptStatus.EXECUTED
    assert search.output and search.output["match_count"] == 1
    assert search.output["matches"][0]["path"] == "src/main.py"
    assert globbed.status is ToolReceiptStatus.EXECUTED
    assert globbed.output and globbed.output["paths"] == ["src/main.py"]
    assert inspected.status is ToolReceiptStatus.EXECUTED
    assert inspected.output and inspected.output["path"] == "src/main.py"
    assert inspected.output["kind"] == "file"
    assert inspected.output["utf8_text"] is True
    assert isinstance(inspected.output["sha256"], str)


def test_workspace_diff_reuses_bounded_git_diff_semantics(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "README.md").write_text("hello\nchanged\n", encoding="utf-8")
    _, orchestrator, _ = _runtime(root)
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-workspace-diff",
        tool_id="workspace.diff",
        arguments={"path": "README.md"},
        context=_context(root),
    ))
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output and "+changed" in receipt.output["text"]
    assert receipt.evidence[0]["tool_id"] == "workspace.diff"


def test_workspace_read_backends_reject_escape_and_unbounded_limits(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _, orchestrator, _ = _runtime(root)
    context = _context(root)

    escaped_search = orchestrator.invoke(ToolRequest(
        operation_id="op-search-escape",
        tool_id="workspace.search",
        arguments={"query": "hello", "path": "../outside"},
        context=context,
    ))
    escaped_glob = orchestrator.invoke(ToolRequest(
        operation_id="op-glob-escape",
        tool_id="workspace.glob",
        arguments={"pattern": "../*.py"},
        context=context,
    ))
    excessive = orchestrator.invoke(ToolRequest(
        operation_id="op-search-limit",
        tool_id="workspace.search",
        arguments={"query": "hello", "max_results": 201},
        context=context,
    ))

    assert escaped_search.status is ToolReceiptStatus.FAILED
    assert escaped_glob.status is ToolReceiptStatus.FAILED
    assert excessive.status is ToolReceiptStatus.FAILED


def test_git_status_reads_live_repository_without_mutation(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "README.md").write_text("hello\nchanged\n", encoding="utf-8")
    before = _git(root, "status", "--porcelain=v1")
    _, orchestrator, _ = _runtime(root)
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-status",
        tool_id="git.status",
        arguments={},
        context=_context(root),
    ))
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output is not None
    assert receipt.output["head"] == _git(root, "rev-parse", "HEAD")
    assert receipt.output["status_short"]
    assert _git(root, "status", "--porcelain=v1") == before


def test_git_diff_is_path_bounded_and_read_only(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "README.md").write_text("hello\nchanged\n", encoding="utf-8")
    _, orchestrator, _ = _runtime(root)
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-diff",
        tool_id="git.diff",
        arguments={"path": "README.md"},
        context=_context(root),
    ))
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output is not None
    assert "+changed" in receipt.output["text"]

    escaped = orchestrator.invoke(ToolRequest(
        operation_id="op-diff-escape",
        tool_id="git.diff",
        arguments={"path": "../outside.txt"},
        context=_context(root),
    ))
    assert escaped.status is ToolReceiptStatus.FAILED
    assert escaped.error_code == "TOOL_EXECUTION_FAILED"


def test_git_log_show_branch_remote_and_worktree_are_bounded_reads(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _git(root, "remote", "add", "origin", "https://example.invalid/repo.git")
    _, orchestrator, _ = _runtime(root)
    context = _context(root)
    requests = (
        ("git.log", {"max_count": 1}),
        ("git.show", {"revision": "HEAD"}),
        ("git.branch", {}),
        ("git.remote", {}),
        ("git.worktree.list", {}),
    )
    outputs = {}
    for index, (tool_id, arguments) in enumerate(requests, start=1):
        receipt = orchestrator.invoke(ToolRequest(
            operation_id=f"op-{index}", tool_id=tool_id, arguments=arguments, context=context,
        ))
        assert receipt.status is ToolReceiptStatus.EXECUTED
        outputs[tool_id] = receipt.output["text"] if receipt.output else ""
    assert "initial" in outputs["git.log"]
    assert "commit" in outputs["git.show"]
    assert _git(root, "branch", "--show-current") in outputs["git.branch"]
    assert "origin" in outputs["git.remote"]
    assert root.as_posix() in outputs["git.worktree.list"].replace("\\", "/")


def test_git_argument_contracts_fail_closed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _, orchestrator, _ = _runtime(root)
    context = _context(root)
    bad_count = orchestrator.invoke(ToolRequest(
        operation_id="op-bad-count", tool_id="git.log", arguments={"max_count": 0}, context=context,
    ))
    bad_revision = orchestrator.invoke(ToolRequest(
        operation_id="op-bad-revision", tool_id="git.show", arguments={"revision": "--help"}, context=context,
    ))
    unknown_argument = orchestrator.invoke(ToolRequest(
        operation_id="op-unknown", tool_id="git.status", arguments={"command": "reset --hard"}, context=context,
    ))
    assert bad_count.status is ToolReceiptStatus.FAILED
    assert bad_revision.status is ToolReceiptStatus.FAILED
    assert unknown_argument.status is ToolReceiptStatus.FAILED
    assert unknown_argument.error_code == "INVALID_TOOL_ARGUMENTS"


def test_read_specs_are_read_only_and_non_networked() -> None:
    for spec in (git_diff_spec(), git_show_spec(), workspace_search_spec(), workspace_glob_spec()):
        assert spec.access_class.value == "read"
        assert spec.network_behavior.value == "none"
        assert spec.capability == "inspect"
