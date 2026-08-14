from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from lbe_guard_inspector.runtime.completion_gate import (
    CompletionRequirement,
    TaskCompletionContract,
)
from lbe_guard_inspector.runtime.completion_runtime import CodingCompletionRuntime
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.professional_validation_session_backends import (
    register_validation_evidence_session_backends,
)
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
)
from lbe_guard_inspector.runtime.validation_command_policy import (
    ValidationCommandPolicy,
    ValidationCommandPolicyCatalog,
)
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


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
    (root / "README.md").write_bytes(b"hello\n")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "initial")
    return root


def _runtime(tmp_path: Path):
    root = _repo(tmp_path)
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="workspace-1",
        workspace_root=root,
        session_id="session-1",
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
    )
    catalog = ValidationCommandPolicyCatalog((
        ValidationCommandPolicy(
            policy_id="test.focused.v1",
            operation_id="reasoning.inspect",
            applicable_mode="coding",
            evidence_kind="focused_test",
            command=(sys.executable, "-c", "print('validation-ok')"),
            timeout_seconds=20.0,
        ),
    ))
    registry = ToolRegistry()
    specs = register_validation_evidence_session_backends(
        registry=registry,
        runtime=runtime,
        validation_command_catalog=catalog,
    )
    return root, runtime, GovernedToolOrchestrator(registry=registry), specs


def _context(root: Path, *, mode: str = "coding", workspace_id: str = "workspace-1") -> ToolExecutionContext:
    capabilities = (
        ("inspect", "modify", "validate_proposal")
        if mode == "coding"
        else ("inspect",)
    )
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode=mode,
            allowed_behaviors=("development_mode_capabilities",) if mode == "coding" else ("audit_mode_constraints",),
            capabilities=capabilities,
            rationale="test",
        ),
        workspace_id=workspace_id,
        workspace_root=root,
        configured_root_id="dev",
    )


def _persist_focused_contract(runtime: SessionMemoryRuntimeBridge, task_id: str = "task-1") -> None:
    CodingCompletionRuntime(runtime=runtime).persist_contract(
        task_id=task_id,
        contract=TaskCompletionContract(requirements=(
            CompletionRequirement(
                requirement_id="focused",
                evidence_kind="focused_test",
                description="focused validation must pass",
            ),
        )),
    )


def test_registers_exact_validation_evidence_session_surface(tmp_path: Path) -> None:
    _, _, _, specs = _runtime(tmp_path)
    assert tuple(spec.tool_id for spec in specs) == (
        "validation.run",
        "evidence.get",
        "session.checkpoint",
        "session.resume",
    )
    assert specs[0].capability == "validate_proposal"
    assert specs[1].capability == "inspect"
    assert specs[2].capability == "modify"
    assert specs[3].capability == "inspect"


def test_validation_run_delegates_to_policy_selected_existing_producer(tmp_path: Path) -> None:
    root, runtime, orchestrator, _ = _runtime(tmp_path)
    _persist_focused_contract(runtime)

    receipt = orchestrator.invoke(ToolRequest(
        operation_id="tool-validation-1",
        tool_id="validation.run",
        arguments={
            "task_id": "task-1",
            "operation_id": "reasoning.inspect",
            "evidence_kind": "focused_test",
        },
        context=_context(root),
    ))

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output is not None
    assert receipt.output["kind"] == "focused_test"
    assert receipt.output["status"] == "PASS"
    assert receipt.output["producer_id"] == "lbe.completion.focused_test.v1"
    assert receipt.output["operation_id"] == "reasoning.inspect"
    details = receipt.output["details"]
    assert details["validation_policy_id"] == "test.focused.v1"
    assert details["exit_code"] == 0


def test_evidence_get_reads_existing_immutable_completion_evidence(tmp_path: Path) -> None:
    root, runtime, orchestrator, _ = _runtime(tmp_path)
    _persist_focused_contract(runtime)
    validation = orchestrator.invoke(ToolRequest(
        operation_id="tool-validation-1",
        tool_id="validation.run",
        arguments={"task_id": "task-1", "operation_id": "reasoning.inspect", "evidence_kind": "focused_test"},
        context=_context(root),
    ))
    assert validation.status is ToolReceiptStatus.EXECUTED

    receipt = orchestrator.invoke(ToolRequest(
        operation_id="tool-evidence-1",
        tool_id="evidence.get",
        arguments={"task_id": "task-1", "evidence_kind": "focused_test"},
        context=_context(root),
    ))

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output is not None
    assert receipt.output["evidence_count"] == 1
    item = receipt.output["items"][0]
    assert item["evidence_id"] == validation.output["evidence_id"]
    assert item["status"] == "PASS"


def test_session_checkpoint_uses_inline_compaction_and_existing_persistence_owner(tmp_path: Path) -> None:
    root, runtime, orchestrator, _ = _runtime(tmp_path)
    compaction = {
        "source_message_count": 3,
        "source_prefix_hash": "sha256:" + "a" * 64,
        "source_last_message_key": "message-3",
    }
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="tool-checkpoint-1",
        tool_id="session.checkpoint",
        arguments={"compaction": compaction, "active_constraints": ["stay in workspace"]},
        context=_context(root),
    ))

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output is not None
    checkpoint_id = receipt.output["checkpoint_id"]
    assert checkpoint_id.startswith("cp-")
    state = runtime.store.load_session_state(session_id=runtime.session_id)
    assert state is not None
    assert state.checkpoint_id == checkpoint_id


def test_session_resume_rehydrates_existing_session_checkpoint_context(tmp_path: Path) -> None:
    root, runtime, orchestrator, _ = _runtime(tmp_path)
    checkpoint = orchestrator.invoke(ToolRequest(
        operation_id="tool-checkpoint-1",
        tool_id="session.checkpoint",
        arguments={
            "compaction": {
                "source_message_count": 1,
                "source_prefix_hash": "sha256:" + "b" * 64,
                "source_last_message_key": "message-1",
            }
        },
        context=_context(root),
    ))
    assert checkpoint.status is ToolReceiptStatus.EXECUTED

    receipt = orchestrator.invoke(ToolRequest(
        operation_id="tool-resume-1",
        tool_id="session.resume",
        arguments={"task_id": "task-1"},
        context=_context(root),
    ))

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output is not None
    assert receipt.output["session_id"] == runtime.session_id
    assert receipt.output["workspace"]["project_workspace_id"] == runtime.project_workspace_id
    assert receipt.output["checkpoint"]["checkpoint_id"] == checkpoint.output["checkpoint_id"]
    assert receipt.output["checkpoint_revalidation"]["authority_owner"] == "LBE_MEMORY_RUNTIME"


def test_checkpoint_rejects_provider_path_and_audit_write_authority(tmp_path: Path) -> None:
    root, _, orchestrator, _ = _runtime(tmp_path)
    path_payload = orchestrator.invoke(ToolRequest(
        operation_id="tool-checkpoint-path",
        tool_id="session.checkpoint",
        arguments={"compaction": "../compaction.json"},
        context=_context(root),
    ))
    audit = orchestrator.invoke(ToolRequest(
        operation_id="tool-checkpoint-audit",
        tool_id="session.checkpoint",
        arguments={
            "compaction": {
                "source_message_count": 0,
                "source_prefix_hash": "sha256:" + "c" * 64,
                "source_last_message_key": None,
            }
        },
        context=_context(root, mode="audit"),
    ))

    assert path_payload.status is ToolReceiptStatus.FAILED
    assert "inline structured mapping" in (path_payload.error_message or "")
    assert audit.status is ToolReceiptStatus.ESCALATED


def test_bound_session_workspace_identity_fails_closed(tmp_path: Path) -> None:
    root, _, orchestrator, _ = _runtime(tmp_path)
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="tool-evidence-wrong-workspace",
        tool_id="evidence.get",
        arguments={"task_id": "task-1"},
        context=_context(root, workspace_id="other-workspace"),
    ))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert "workspace identity" in (receipt.error_message or "")


def test_validation_run_rejects_undeclared_or_provider_selected_evidence_kind(tmp_path: Path) -> None:
    root, runtime, orchestrator, _ = _runtime(tmp_path)
    _persist_focused_contract(runtime)
    unsupported = orchestrator.invoke(ToolRequest(
        operation_id="tool-validation-unsupported",
        tool_id="validation.run",
        arguments={"task_id": "task-1", "operation_id": "reasoning.inspect", "evidence_kind": "source_change"},
        context=_context(root),
    ))
    missing_contract = orchestrator.invoke(ToolRequest(
        operation_id="tool-validation-missing-contract",
        tool_id="validation.run",
        arguments={"task_id": "task-2", "operation_id": "reasoning.inspect", "evidence_kind": "focused_test"},
        context=_context(root),
    ))

    assert unsupported.status is ToolReceiptStatus.FAILED
    assert "supports only focused_test" in (unsupported.error_message or "")
    assert missing_contract.status is ToolReceiptStatus.FAILED
    assert "declared" in (missing_contract.error_message or "")
