from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lbe_guard_inspector.runtime.change_registration import check_change_registration
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolAccessClass,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
    ToolSpec,
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


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-b", "main")
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(
        root,
        "-c",
        "user.name=LBE Tests",
        "-c",
        "user.email=lbe-tests@example.invalid",
        "commit",
        "-m",
        "initial",
    )


def _enable_gate(root: Path) -> None:
    ai = root / ".ai"
    ai.mkdir(exist_ok=True)
    (ai / "change-gate.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "enabled": True,
                "canonicalBranch": "main",
                "requireIntentForAllMutations": True,
                "requireBranchRegistrationOutsideCanonical": True,
                "requireWorktreeRegistrationForLinkedWorktree": True,
                "intentFile": ".ai/intent.json",
            }
        ),
        encoding="utf-8",
    )


def _write_intent(
    root: Path,
    *,
    branch: str | None = None,
    worktree_path: Path | None = None,
    allowed_paths: list[str] | None = None,
    explicit_exclusions: list[str] | None = None,
) -> None:
    ai = root / ".ai"
    ai.mkdir(exist_ok=True)
    payload: dict[str, object] = {
        "schemaVersion": 1,
        "changeId": "CHANGE-test",
        "status": "active",
        "intent": "exercise the governed mutation registration gate",
    }
    if branch is not None:
        payload["branch"] = branch
    if worktree_path is not None:
        payload["worktreePath"] = str(worktree_path.resolve())
    if allowed_paths is not None:
        payload["allowedPaths"] = allowed_paths
    if explicit_exclusions is not None:
        payload["explicitExclusions"] = explicit_exclusions
    (ai / "intent.json").write_text(json.dumps(payload), encoding="utf-8")


def _mode(*capabilities: str) -> ModeDecision:
    return ModeDecision(
        mode="coding",
        allowed_behaviors=("development_mode_capabilities",),
        capabilities=tuple(capabilities),
        rationale="test",
    )


def test_repository_without_gate_remains_neutral(tmp_path: Path) -> None:
    result = check_change_registration(tmp_path)
    assert result.allowed is True
    assert result.code == "CHANGE_GATE_NOT_CONFIGURED"


def test_enabled_gate_blocks_missing_intent_on_main(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _enable_gate(tmp_path)

    result = check_change_registration(tmp_path, requested_path="README.md")

    assert result.allowed is False
    assert result.code == "CHANGE_INTENT_REQUIRED"
    assert result.branch == "main"


def test_main_workspace_requires_intent_but_not_duplicate_branch_registration(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _enable_gate(tmp_path)
    _write_intent(tmp_path)

    result = check_change_registration(tmp_path, requested_path="README.md")

    assert result.allowed is True
    assert result.code == "CHANGE_INTENT_ACTIVE"
    assert result.branch == "main"


def test_feature_branch_requires_exact_branch_registration(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _enable_gate(tmp_path)
    _git(tmp_path, "checkout", "-b", "feature/change-gate")
    _write_intent(tmp_path)

    missing = check_change_registration(tmp_path, requested_path="README.md")
    assert missing.allowed is False
    assert missing.code == "CHANGE_INTENT_BRANCH_REQUIRED"

    _write_intent(tmp_path, branch="feature/change-gate")
    matching = check_change_registration(tmp_path, requested_path="README.md")
    assert matching.allowed is True
    assert matching.code == "CHANGE_INTENT_ACTIVE"


def test_mismatched_branch_registration_blocks(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _enable_gate(tmp_path)
    _git(tmp_path, "checkout", "-b", "feature/actual")
    _write_intent(tmp_path, branch="feature/other")

    result = check_change_registration(tmp_path, requested_path="README.md")

    assert result.allowed is False
    assert result.code == "CHANGE_INTENT_BRANCH_MISMATCH"


def test_linked_worktree_requires_exact_worktree_registration(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    linked = tmp_path / "linked"
    _init_repo(primary)
    _enable_gate(primary)
    _git(primary, "add", ".ai/change-gate.json")
    _git(
        primary,
        "-c",
        "user.name=LBE Tests",
        "-c",
        "user.email=lbe-tests@example.invalid",
        "commit",
        "-m",
        "enable gate",
    )
    _git(primary, "branch", "feature/linked")
    _git(primary, "worktree", "add", str(linked), "feature/linked")

    _write_intent(linked, branch="feature/linked")
    missing = check_change_registration(linked, requested_path="README.md")
    assert missing.allowed is False
    assert missing.code == "CHANGE_INTENT_WORKTREE_REQUIRED"

    _write_intent(linked, branch="feature/linked", worktree_path=linked)
    matching = check_change_registration(linked, requested_path="README.md")
    assert matching.allowed is True
    assert matching.code == "CHANGE_INTENT_ACTIVE"

    _write_intent(linked, branch="feature/linked", worktree_path=primary)
    mismatch = check_change_registration(linked, requested_path="README.md")
    assert mismatch.allowed is False
    assert mismatch.code == "CHANGE_INTENT_WORKTREE_MISMATCH"


def test_intent_path_scope_blocks_unregistered_or_excluded_paths(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _enable_gate(tmp_path)
    _write_intent(
        tmp_path,
        allowed_paths=["src/**"],
        explicit_exclusions=["src/release/**"],
    )

    allowed = check_change_registration(tmp_path, requested_path="src/runtime.py")
    outside = check_change_registration(tmp_path, requested_path="tests/test_runtime.py")
    excluded = check_change_registration(tmp_path, requested_path="src/release/publish.py")

    assert allowed.allowed is True
    assert outside.allowed is False
    assert outside.code == "CHANGE_INTENT_SCOPE_MISMATCH"
    assert excluded.allowed is False
    assert excluded.code == "CHANGE_INTENT_EXCLUSION"


def test_orchestrator_blocks_write_before_handler_when_intent_missing(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _enable_gate(tmp_path)
    calls: list[ToolRequest] = []
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            tool_id="test.write",
            capability="modify",
            required_arguments=("path",),
            access_class=ToolAccessClass.WRITE,
        ),
        lambda request: calls.append(request) or ToolExecutionResult(output={"ok": True}),
    )
    orchestrator = GovernedToolOrchestrator(registry=registry)
    request = ToolRequest(
        operation_id="write-1",
        tool_id="test.write",
        arguments={"path": "README.md"},
        context=ToolExecutionContext(
            mode_decision=_mode("modify"),
            workspace_id="workspace-1",
            workspace_root=tmp_path,
            configured_root_id="dev",
        ),
    )

    receipt = orchestrator.invoke(request)

    assert receipt.status is ToolReceiptStatus.DENIED
    assert receipt.error_code == "CHANGE_INTENT_REQUIRED"
    assert receipt.authorization is None
    assert calls == []


def test_orchestrator_read_tool_is_not_blocked_by_change_gate(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _enable_gate(tmp_path)
    calls: list[ToolRequest] = []
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            tool_id="test.read",
            capability="inspect",
            required_arguments=(),
            access_class=ToolAccessClass.READ,
        ),
        lambda request: calls.append(request) or ToolExecutionResult(output={"ok": True}),
    )
    orchestrator = GovernedToolOrchestrator(registry=registry)
    request = ToolRequest(
        operation_id="read-1",
        tool_id="test.read",
        arguments={},
        context=ToolExecutionContext(
            mode_decision=_mode("inspect"),
            workspace_id="workspace-1",
            workspace_root=tmp_path,
            configured_root_id="dev",
        ),
    )

    receipt = orchestrator.invoke(request)

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert len(calls) == 1
