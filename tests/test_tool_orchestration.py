from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.runtime.authorization_resolver import AuthorizationVerdict
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolAccessClass,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolNetworkBehavior,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
    ToolRiskClass,
    ToolSpec,
    build_workspace_read_handler,
    build_workspace_delete_handler,
    workspace_delete_spec,
    workspace_read_spec,
)


def _mode(*capabilities: str) -> ModeDecision:
    return ModeDecision(
        mode="coding",
        allowed_behaviors=("development_mode_capabilities",),
        capabilities=tuple(capabilities),
        rationale="test",
    )


def _context(tmp_path: Path, *capabilities: str, **overrides) -> ToolExecutionContext:
    values = {
        "mode_decision": _mode(*capabilities),
        "workspace_id": "workspace-1",
        "workspace_root": tmp_path,
        "configured_root_id": "dev",
    }
    values.update(overrides)
    return ToolExecutionContext(**values)


def _request(tmp_path: Path, *, operation_id="op-1", tool_id="workspace.read", arguments=None, capabilities=("inspect",), **context_overrides) -> ToolRequest:
    return ToolRequest(
        operation_id=operation_id,
        tool_id=tool_id,
        arguments=arguments if arguments is not None else {"path": "README.md"},
        context=_context(tmp_path, *capabilities, **context_overrides),
    )


def _registry(handler) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), handler)
    return registry


def test_workspace_read_spec_declares_required_governance_metadata() -> None:
    spec = workspace_read_spec()
    assert spec.tool_id == "workspace.read"
    assert spec.capability == "inspect"
    assert spec.required_arguments == ("path",)
    assert spec.access_class is ToolAccessClass.READ
    assert spec.network_behavior is ToolNetworkBehavior.NONE
    assert spec.risk_class is ToolRiskClass.LOW
    assert spec.timeout_seconds > 0
    assert spec.retry_policy
    assert spec.preconditions
    assert spec.expected_evidence
    assert spec.failure_modes


def test_registry_rejects_duplicate_tool_id() -> None:
    registry = ToolRegistry()
    spec = workspace_read_spec()
    registry.register(spec, lambda request: ToolExecutionResult(output={}))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec, lambda request: ToolExecutionResult(output={}))


def test_unregistered_tool_cannot_execute(tmp_path: Path) -> None:
    orchestrator = GovernedToolOrchestrator(registry=ToolRegistry())
    receipt = orchestrator.invoke(_request(tmp_path, tool_id="shell.execute"))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "UNREGISTERED_TOOL"
    assert receipt.authorization is None


def test_authorized_registered_tool_executes_and_captures_evidence(tmp_path: Path) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return ToolExecutionResult(
            output={"ok": True},
            evidence=({"ref": "workspace:1:README.md", "verified": True},),
        )

    orchestrator = GovernedToolOrchestrator(registry=_registry(handler))
    receipt = orchestrator.invoke(_request(tmp_path))
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.ALLOW
    assert receipt.output == {"ok": True}
    assert receipt.evidence == ({"ref": "workspace:1:README.md", "verified": True},)
    assert len(calls) == 1


def test_missing_mode_capability_escalates_without_execution(tmp_path: Path) -> None:
    calls = []
    orchestrator = GovernedToolOrchestrator(
        registry=_registry(lambda request: calls.append(request) or ToolExecutionResult(output={}))
    )
    receipt = orchestrator.invoke(_request(tmp_path, capabilities=("search",)))
    assert receipt.status is ToolReceiptStatus.ESCALATED
    assert receipt.error_code == "AUTHORIZATION_REQUIRED"
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.ESCALATE
    assert calls == []


def test_explicit_forbidden_policy_denies_without_execution(tmp_path: Path) -> None:
    calls = []
    orchestrator = GovernedToolOrchestrator(
        registry=_registry(lambda request: calls.append(request) or ToolExecutionResult(output={}))
    )
    receipt = orchestrator.invoke(_request(tmp_path, explicitly_forbidden=True))
    assert receipt.status is ToolReceiptStatus.DENIED
    assert receipt.error_code == "AUTHORIZATION_DENIED"
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.DENY
    assert calls == []


def test_workspace_scope_expansion_escalates_before_execution(tmp_path: Path) -> None:
    calls = []
    orchestrator = GovernedToolOrchestrator(
        registry=_registry(lambda request: calls.append(request) or ToolExecutionResult(output={}))
    )
    receipt = orchestrator.invoke(_request(tmp_path, within_workspace_scope=False))
    assert receipt.status is ToolReceiptStatus.ESCALATED
    assert calls == []


def test_invalid_arguments_fail_before_authorization_or_execution(tmp_path: Path) -> None:
    calls = []
    orchestrator = GovernedToolOrchestrator(
        registry=_registry(lambda request: calls.append(request) or ToolExecutionResult(output={}))
    )
    receipt = orchestrator.invoke(_request(tmp_path, arguments={"unknown": True}))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "INVALID_TOOL_ARGUMENTS"
    assert receipt.authorization is None
    assert calls == []


def test_duplicate_operation_id_returns_original_receipt_without_reexecution(tmp_path: Path) -> None:
    calls = []

    def handler(request):
        calls.append(request.operation_id)
        return ToolExecutionResult(output={"count": len(calls)})

    orchestrator = GovernedToolOrchestrator(registry=_registry(handler))
    request = _request(tmp_path, operation_id="op-repeat")
    first = orchestrator.invoke(request)
    second = orchestrator.invoke(request)
    assert second is first
    assert first.output == {"count": 1}
    assert calls == ["op-repeat"]
    assert orchestrator.receipt("op-repeat") is first


def test_handler_failure_becomes_structured_receipt(tmp_path: Path) -> None:
    def handler(request):
        raise OSError("read failed")

    receipt = GovernedToolOrchestrator(registry=_registry(handler)).invoke(_request(tmp_path))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"
    assert "read failed" in receipt.error_message
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.ALLOW


class FakeEvidenceService(EvidenceService):
    def __init__(self, evidence=None):
        self.calls = []
        self.evidence = evidence or [{"ref": "workspace:workspace-1:README.md", "verified": True}]

    def build_evidence_package(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "current_workspace_evidence": list(self.evidence),
            "missing_evidence": [],
        }


def test_workspace_read_handler_delegates_to_existing_evidence_service(tmp_path: Path) -> None:
    service = FakeEvidenceService()
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), build_workspace_read_handler(service))
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        _request(tmp_path, arguments={"path": "docs/README.md"})
    )
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output == {
        "path": "docs/README.md",
        "evidence_count": 1,
        "missing_evidence": [],
    }
    assert receipt.evidence == ({"ref": "workspace:workspace-1:README.md", "verified": True},)
    assert len(service.calls) == 1
    call = service.calls[0]
    assert call["workspace_id"] == "workspace-1"
    assert call["workspace_root"] == str(tmp_path.resolve())
    assert call["roots"] == ["dev"]
    assert call["retrieval_mode"] == "guard"
    assert call["rule_id"] == "workspace.read"
    assert call["path_patterns"] == ["docs/README.md"]


def test_workspace_read_handler_rejects_path_escape_before_evidence_read(tmp_path: Path) -> None:
    service = FakeEvidenceService()
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), build_workspace_read_handler(service))
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        _request(tmp_path, arguments={"path": "../outside.txt"})
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"
    assert service.calls == []


def test_workspace_glob_handler_matches_files_and_excludes_symlinks(tmp_path: Path) -> None:
    from lbe_guard_inspector.runtime.tool_orchestration import (
        build_workspace_glob_handler,
        workspace_glob_spec,
    )

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.rs").write_text("fn main() {}", encoding="utf-8")
    (tmp_path / "src" / "notes.txt").write_text("notes", encoding="utf-8")
    registry = ToolRegistry()
    registry.register(workspace_glob_spec(), build_workspace_glob_handler())

    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        _request(
            tmp_path,
            tool_id="workspace.glob",
            arguments={"pattern": "**/*.rs"},
        )
    )

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output == {
        "pattern": "**/*.rs",
        "matches": [{"path": "src/main.rs", "type": "file"}],
        "match_count": 1,
    }
    assert receipt.evidence[0]["ref"] == "workspace:workspace-1:src/main.rs"


def test_workspace_glob_handler_rejects_path_escape(tmp_path: Path) -> None:
    from lbe_guard_inspector.runtime.tool_orchestration import (
        build_workspace_glob_handler,
        workspace_glob_spec,
    )

    registry = ToolRegistry()
    registry.register(workspace_glob_spec(), build_workspace_glob_handler())
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        _request(tmp_path, tool_id="workspace.glob", arguments={"pattern": "../*.rs"})
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"


def test_workspace_search_handler_projects_validated_evidence_package(tmp_path: Path) -> None:
    from lbe_guard_inspector.runtime.tool_orchestration import (
        build_workspace_search_handler,
        workspace_search_spec,
    )

    class FakeSearchEvidenceService(EvidenceService):
        def build_evidence_package(self, **kwargs):
            assert kwargs["query"] == "workspace glob"
            return {
                "indexed_reference_evidence": [
                    {
                        "ref": "index:dev:README.md",
                        "path": "README.md",
                        "line_start": 4,
                        "line_end": 4,
                        "snippet": "workspace glob",
                        "score": 120.0,
                        "source_type": "index",
                        "verified": False,
                    }
                ],
                "current_workspace_evidence": [
                    {
                        "ref": "workspace:workspace-1:README.md",
                        "path": str(tmp_path / "README.md"),
                        "line_start": 1,
                        "line_end": 1,
                        "snippet": "workspace glob",
                        "score": 2.0,
                        "source_type": "workspace",
                        "verified": True,
                    }
                ],
                "missing_evidence": [],
            }

    registry = ToolRegistry()
    registry.register(workspace_search_spec(), build_workspace_search_handler(FakeSearchEvidenceService()))
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        _request(
            tmp_path,
            tool_id="workspace.search",
            arguments={"query": "workspace glob"},
        )
    )

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output["indexed_result_count"] == 1
    assert receipt.output["current_result_count"] == 1
    assert len(receipt.output["results"]) == 2
    assert len(receipt.evidence) == 2


def test_workspace_search_handler_rejects_empty_query(tmp_path: Path) -> None:
    from lbe_guard_inspector.runtime.tool_orchestration import (
        build_workspace_search_handler,
        workspace_search_spec,
    )

    registry = ToolRegistry()
    registry.register(workspace_search_spec(), build_workspace_search_handler(EvidenceService()))
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        _request(tmp_path, tool_id="workspace.search", arguments={"query": "  "})
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"


def _delete_orchestrator() -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    registry.register(workspace_delete_spec(), build_workspace_delete_handler())
    return GovernedToolOrchestrator(registry=registry)


def _delete_request(tmp_path: Path, path: str, *, operation_id: str = "delete-1", **arguments) -> ToolRequest:
    destructive_authorized = arguments.pop("destructive_authorized", True)
    return ToolRequest(
        operation_id=operation_id,
        tool_id="workspace.delete",
        arguments={"path": path, **arguments},
        context=_context(
            tmp_path,
            "modify",
            destructive=True,
            destructive_authorized=destructive_authorized,
        ),
    )


def test_workspace_delete_spec_uses_existing_modify_vocabulary() -> None:
    spec = workspace_delete_spec()
    assert spec.tool_id == "workspace.delete"
    assert spec.capability == "modify"
    assert spec.access_class is ToolAccessClass.WRITE
    assert spec.network_behavior is ToolNetworkBehavior.NONE
    assert spec.risk_class is ToolRiskClass.HIGH
    assert spec.required_arguments == ("path", "classification", "expected_type")


def test_workspace_delete_removes_file_and_records_hash_evidence(tmp_path: Path) -> None:
    target = tmp_path / "generated.pyc"
    target.write_bytes(b"generated")
    digest = hashlib.sha256(b"generated").hexdigest()
    receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path,
        "generated.pyc",
        classification="GENERATED_REGENERABLE",
        expected_type="file",
        expected_sha256=digest,
    ))
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output["deleted"] is True
    assert receipt.evidence[0]["before_sha256"] == digest
    assert receipt.evidence[0]["after_exists"] is False
    assert not target.exists()


def test_workspace_delete_removes_disposable_directory(tmp_path: Path) -> None:
    target = tmp_path / ".pytest_cache"
    target.mkdir()
    (target / "cache").write_text("generated", encoding="utf-8")
    receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, ".pytest_cache", classification="CACHE", expected_type="directory"
    ))
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert not target.exists()


def test_workspace_delete_requires_destructive_authority(tmp_path: Path) -> None:
    target = tmp_path / "temp.txt"
    target.write_text("keep", encoding="utf-8")
    receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, "temp.txt", classification="TEMPORARY", expected_type="file", destructive_authorized=False
    ))
    assert receipt.status is ToolReceiptStatus.ESCALATED
    assert receipt.error_code == "AUTHORIZATION_REQUIRED"
    assert target.exists()


@pytest.mark.parametrize("path", ["../outside.txt", "C:/outside.txt"])
def test_workspace_delete_rejects_escape_paths(tmp_path: Path, path: str) -> None:
    receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, path, classification="TEMPORARY", expected_type="file"
    ))
    assert receipt.status is ToolReceiptStatus.FAILED


def test_workspace_delete_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("protected", encoding="utf-8")
    link = tmp_path / "linked-cache"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows host")
    receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, "linked-cache", classification="CACHE", expected_type="directory"
    ))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert link.exists()
    assert (outside / "secret.txt").exists()


def test_workspace_delete_rejects_root_and_protected_classification(tmp_path: Path) -> None:
    root_receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, ".", classification="CACHE", expected_type="directory"
    ))
    assert root_receipt.status is ToolReceiptStatus.FAILED
    target = tmp_path / "important.txt"
    target.write_text("keep", encoding="utf-8")
    protected_receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, "important.txt", classification="PROTECTED_USER_WORK", expected_type="file"
    ))
    assert protected_receipt.status is ToolReceiptStatus.FAILED
    assert target.exists()


def test_workspace_delete_rejects_type_and_hash_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "generated.pyc"
    target.write_bytes(b"generated")
    type_receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, "generated.pyc", classification="GENERATED_REGENERABLE", expected_type="directory"
    ))
    assert type_receipt.status is ToolReceiptStatus.FAILED
    hash_receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, "generated.pyc", classification="GENERATED_REGENERABLE", expected_type="file", expected_sha256="0" * 64
    ))
    assert hash_receipt.status is ToolReceiptStatus.FAILED
    assert target.exists()


def test_workspace_delete_physical_failure_is_failed_receipt(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "generated.pyc"
    target.write_bytes(b"generated")
    monkeypatch.setattr(Path, "unlink", lambda self: (_ for _ in ()).throw(OSError("blocked")))
    receipt = _delete_orchestrator().invoke(_delete_request(
        tmp_path, "generated.pyc", classification="GENERATED_REGENERABLE", expected_type="file"
    ))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert target.exists()


def test_workspace_delete_duplicate_operation_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "generated.pyc"
    target.write_bytes(b"generated")
    request = _delete_request(tmp_path, "generated.pyc", classification="GENERATED_REGENERABLE", expected_type="file")
    orchestrator = _delete_orchestrator()
    first = orchestrator.invoke(request)
    second = orchestrator.invoke(request)
    assert first.status is ToolReceiptStatus.EXECUTED
    assert second is first


def test_unregistered_equivalent_delete_tool_cannot_execute(tmp_path: Path) -> None:
    target = tmp_path / "generated.pyc"
    target.write_bytes(b"keep")
    request = _delete_request(tmp_path, "generated.pyc", classification="CACHE", expected_type="file")
    request = ToolRequest(operation_id=request.operation_id, tool_id="filesystem.delete", arguments=request.arguments, context=request.context)
    receipt = GovernedToolOrchestrator(registry=ToolRegistry()).invoke(request)
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "UNREGISTERED_TOOL"
    assert target.exists()
