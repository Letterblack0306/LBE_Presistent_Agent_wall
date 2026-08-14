"""P5 typed adapters over existing validation, evidence, and session owners.

No validation engine, evidence store, or session persistence is introduced here.
The adapters bind provider-visible tool requests to the already-authoritative
CompletionEvidenceProducers, TaskCompletionEvidencePersistence, and
SessionMemoryRuntimeBridge owners through the existing GovernedToolOrchestrator.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ..memory.completion_evidence import StoredCompletionEvidence, TaskCompletionEvidencePersistence
from ..session_memory_runtime import SessionMemoryRuntimeBridge
from .completion_evidence_producers import CompletionEvidenceProducers
from .tool_orchestration import (
    ToolAccessClass,
    ToolExecutionResult,
    ToolHandler,
    ToolNetworkBehavior,
    ToolRegistry,
    ToolRequest,
    ToolRiskClass,
    ToolSpec,
)
from .validation_command_policy import (
    DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG,
    ValidationCommandPolicyCatalog,
)


class ProfessionalValidationSessionBackendError(RuntimeError):
    """Raised when a request does not match its bound persistent runtime."""


def register_validation_evidence_session_backends(
    *,
    registry: ToolRegistry,
    runtime: SessionMemoryRuntimeBridge,
    validation_command_catalog: ValidationCommandPolicyCatalog = DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG,
) -> tuple[ToolSpec, ...]:
    """Register typed projections over existing validation/evidence/session owners."""
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be ToolRegistry")
    if not isinstance(runtime, SessionMemoryRuntimeBridge):
        raise TypeError("runtime must be SessionMemoryRuntimeBridge")
    if not isinstance(validation_command_catalog, ValidationCommandPolicyCatalog):
        raise TypeError("validation_command_catalog must be ValidationCommandPolicyCatalog")

    producers = CompletionEvidenceProducers(
        runtime=runtime,
        validation_command_catalog=validation_command_catalog,
    )
    evidence = TaskCompletionEvidencePersistence(runtime.store)
    entries: tuple[tuple[ToolSpec, ToolHandler], ...] = (
        (validation_run_spec(), build_validation_run_handler(runtime=runtime, producers=producers)),
        (evidence_get_spec(), build_evidence_get_handler(runtime=runtime, persistence=evidence)),
        (session_checkpoint_spec(), build_session_checkpoint_handler(runtime=runtime)),
        (session_resume_spec(), build_session_resume_handler(runtime=runtime)),
    )
    for spec, handler in entries:
        registry.register(spec, handler)
    return tuple(spec for spec, _ in entries)


def validation_run_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="validation.run",
        capability="validate_proposal",
        required_arguments=("task_id", "operation_id", "evidence_kind"),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.MEDIUM,
        timeout_seconds=300.0,
        retry_policy="none",
        preconditions=(
            "bound persistent session/workspace",
            "declared completion evidence requirement",
            "fixed LBE validation command policy",
        ),
        expected_evidence=("producer-bound immutable validation evidence",),
        failure_modes=(
            "session/workspace mismatch",
            "unsupported evidence kind",
            "missing completion requirement",
            "missing validation policy",
            "validation command failure",
            "authorization failure",
        ),
    )


def evidence_get_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="evidence.get",
        capability="inspect",
        required_arguments=("task_id",),
        optional_arguments=("evidence_kind",),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=("bound persistent session/workspace",),
        expected_evidence=("persisted producer-bound completion evidence",),
        failure_modes=("session/workspace mismatch", "invalid argument", "read failure", "authorization failure"),
    )


def session_checkpoint_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="session.checkpoint",
        capability="modify",
        required_arguments=("compaction",),
        optional_arguments=("active_constraints",),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.MEDIUM,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=(
            "bound persistent session/workspace",
            "inline structured compaction payload",
            "active coding authority",
        ),
        expected_evidence=("persisted checkpoint identity", "captured current Git identity"),
        failure_modes=("session/workspace mismatch", "invalid compaction", "persistence failure", "authorization failure"),
    )


def session_resume_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="session.resume",
        capability="inspect",
        required_arguments=(),
        optional_arguments=("task_id",),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=("bound persistent session/workspace",),
        expected_evidence=("rehydrated session/workspace/checkpoint context",),
        failure_modes=("session/workspace mismatch", "rehydration failure", "authorization failure"),
    )


def build_validation_run_handler(
    *,
    runtime: SessionMemoryRuntimeBridge,
    producers: CompletionEvidenceProducers,
) -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        _require_runtime_context(runtime, request)
        task_id = _required_text(request.arguments["task_id"], "task_id")
        operation_id = _required_text(request.arguments["operation_id"], "operation_id")
        evidence_kind = _required_text(request.arguments["evidence_kind"], "evidence_kind")
        if evidence_kind != "focused_test":
            raise ValueError("validation.run currently supports only focused_test evidence")
        stored = producers.produce_focused_test(task_id=task_id, operation_id=operation_id)
        output = _stored_evidence_payload(stored)
        return ToolExecutionResult(
            output=output,
            evidence=({
                "source_class": "producer_bound_completion_evidence",
                "evidence_id": stored.evidence_id,
                "kind": stored.kind,
                "status": stored.status,
                "producer_id": stored.producer_id,
                "operation_id": stored.operation_id,
            },),
        )

    return handler


def build_evidence_get_handler(
    *,
    runtime: SessionMemoryRuntimeBridge,
    persistence: TaskCompletionEvidencePersistence,
) -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        _require_runtime_context(runtime, request)
        task_id = _required_text(request.arguments["task_id"], "task_id")
        requested_kind = request.arguments.get("evidence_kind")
        if requested_kind is not None:
            requested_kind = _required_text(requested_kind, "evidence_kind")
        records = persistence.load(
            session_id=runtime.session_id,
            task_id=task_id,
            project_workspace_id=runtime.project_workspace_id,
        )
        if requested_kind is not None:
            records = tuple(item for item in records if item.kind == requested_kind)
        items = [_stored_evidence_payload(item) for item in records]
        return ToolExecutionResult(
            output={"task_id": task_id, "items": items, "evidence_count": len(items)},
            evidence=tuple({
                "source_class": "persisted_completion_evidence",
                "evidence_id": item.evidence_id,
                "kind": item.kind,
                "status": item.status,
            } for item in records),
        )

    return handler


def build_session_checkpoint_handler(*, runtime: SessionMemoryRuntimeBridge) -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        _require_runtime_context(runtime, request)
        compaction = request.arguments["compaction"]
        if not isinstance(compaction, Mapping):
            raise TypeError("compaction must be an inline structured mapping")
        constraints = request.arguments.get("active_constraints", ())
        if not isinstance(constraints, (list, tuple)) or not all(
            isinstance(item, str) and item.strip() for item in constraints
        ):
            raise ValueError("active_constraints must contain non-empty strings")
        checkpoint_id = runtime.checkpoint(
            compaction=dict(compaction),
            active_constraints=tuple(item.strip() for item in constraints),
        )
        state = runtime.store.load_session_state(session_id=runtime.session_id)
        if state is None or state.checkpoint_id != checkpoint_id:
            raise ProfessionalValidationSessionBackendError("checkpoint persistence did not update bound session state")
        output = {
            "session_id": runtime.session_id,
            "checkpoint_id": checkpoint_id,
            "project_workspace_id": runtime.project_workspace_id,
            "canonical_workspace_root": str(runtime.workspace_root).replace("\\", "/"),
        }
        return ToolExecutionResult(
            output=output,
            evidence=({"source_class": "persistent_session_checkpoint", **output},),
        )

    return handler


def build_session_resume_handler(*, runtime: SessionMemoryRuntimeBridge) -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        _require_runtime_context(runtime, request)
        task_id = request.arguments.get("task_id")
        if task_id is not None:
            task_id = _required_text(task_id, "task_id")
        packet = runtime.start_or_resume(task_id=task_id)
        session = packet.get("session") if isinstance(packet, Mapping) else None
        workspace = packet.get("workspace") if isinstance(packet, Mapping) else None
        checkpoint = packet.get("checkpoint") if isinstance(packet, Mapping) else None
        output = {
            "session_id": runtime.session_id,
            "task_id": task_id,
            "session": session,
            "workspace": workspace,
            "checkpoint": checkpoint,
            "checkpoint_revalidation": packet.get("checkpoint_revalidation"),
            "verified_facts": list(packet.get("verified_facts") or ()),
            "active_constraints": list(packet.get("active_constraints") or ()),
            "recent_failures": list(packet.get("recent_failures") or ()),
            "live_evidence_required": list(packet.get("live_evidence_required") or ()),
        }
        return ToolExecutionResult(
            output=output,
            evidence=({
                "source_class": "rehydrated_session_context",
                "session_id": runtime.session_id,
                "project_workspace_id": runtime.project_workspace_id,
                "checkpoint_id": (checkpoint or {}).get("checkpoint_id") if isinstance(checkpoint, Mapping) else None,
            },),
        )

    return handler


def _require_runtime_context(runtime: SessionMemoryRuntimeBridge, request: ToolRequest) -> None:
    if request.context.workspace_id != runtime.project_workspace_id:
        raise ProfessionalValidationSessionBackendError("tool workspace identity does not match bound session")
    request_root = Path(request.context.workspace_root).resolve()
    if request_root != runtime.workspace_root.resolve():
        raise ProfessionalValidationSessionBackendError("tool workspace root does not match bound session")


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _stored_evidence_payload(item: StoredCompletionEvidence) -> dict[str, Any]:
    return {
        "session_id": item.session_id,
        "task_id": item.task_id,
        "project_workspace_id": item.project_workspace_id,
        "evidence_id": item.evidence_id,
        "kind": item.kind,
        "status": item.status,
        "source": item.source,
        "producer_id": item.producer_id,
        "operation_id": item.operation_id,
        "details": dict(item.details),
        "created_at": item.created_at,
    }
