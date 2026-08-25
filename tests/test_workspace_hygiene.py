from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from lbe_guard_inspector.runtime.authorization_resolver import AuthorizationVerdict
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
)
from lbe_guard_inspector.runtime.workspace_hygiene import (
    build_workspace_delete_disposable_handler,
    workspace_delete_disposable_spec,
)


def _orchestrator() -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    registry.register(workspace_delete_disposable_spec(), build_workspace_delete_disposable_handler())
    return GovernedToolOrchestrator(registry=registry)


def _request(workspace: Path, path: str, **arguments) -> ToolRequest:
    return ToolRequest(
        operation_id=f"delete:{path}",
        tool_id="workspace.delete_disposable",
        arguments={"path": path, **arguments},
        context=ToolExecutionContext(
            mode_decision=ModeDecision(
                mode="coding",
                allowed_behaviors=("development_mode_capabilities",),
                capabilities=("cleanup_disposable",),
                rationale="workspace hygiene test",
            ),
            workspace_id="workspace-1",
            workspace_root=workspace,
            configured_root_id="workspace-1",
            destructive=True,
            destructive_authorized=True,
        ),
    )


def test_disposable_file_is_deleted_with_receipt_and_evidence(tmp_path: Path) -> None:
    target = tmp_path / "generated.pyc"
    target.write_bytes(b"generated")
    digest = hashlib.sha256(b"generated").hexdigest()

    receipt = _orchestrator().invoke(_request(
        tmp_path,
        "generated.pyc",
        classification="GENERATED_REGENERABLE",
        expected_state="file",
        expected_sha256=digest,
    ))

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.ALLOW
    assert receipt.output["deleted"] is True
    assert receipt.evidence[0]["after_exists"] is False
    assert not target.exists()


def test_outside_workspace_is_rejected_before_deletion(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.tmp"
    outside.write_text("keep", encoding="utf-8")
    receipt = _orchestrator().invoke(_request(
        tmp_path,
        "../outside.tmp",
        classification="TEMPORARY",
        expected_state="file",
    ))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert not receipt.output
    assert outside.exists()


def test_protected_authority_path_is_rejected(tmp_path: Path) -> None:
    protected = tmp_path / ".lbe"
    protected.mkdir()
    (protected / "governance.json").write_text("keep", encoding="utf-8")
    receipt = _orchestrator().invoke(_request(
        tmp_path,
        ".lbe",
        classification="CACHE",
        expected_state="directory",
    ))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert protected.exists()


def test_unknown_classification_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "unknown.txt"
    target.write_text("keep", encoding="utf-8")
    receipt = _orchestrator().invoke(_request(
        tmp_path,
        "unknown.txt",
        classification="UNKNOWN",
        expected_state="file",
    ))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert target.exists()


def test_direct_unregistered_delete_cannot_execute(tmp_path: Path) -> None:
    target = tmp_path / "keep.txt"
    target.write_text("keep", encoding="utf-8")
    request = _request(tmp_path, "keep.txt", classification="CACHE", expected_state="file")
    request = ToolRequest(
        operation_id=request.operation_id,
        tool_id="filesystem.delete",
        arguments=request.arguments,
        context=request.context,
    )
    receipt = GovernedToolOrchestrator(registry=ToolRegistry()).invoke(request)
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "UNREGISTERED_TOOL"
    assert target.exists()
