"""Governed tool orchestration for the R6E runtime slice.

The orchestrator owns lifecycle ordering only: registered lookup, deterministic
R6C authorization, bounded handler invocation, structured receipts, and
operation-id idempotency. Tool implementations remain separate services.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from ..evidence_service import EvidenceService
from .authorization_resolver import (
    AuthorizationDecision,
    AuthorizationRequest,
    AuthorizationVerdict,
    resolve_authorization,
)
from .mode_controller import ModeDecision


class ToolAccessClass(StrEnum):
    READ = "read"
    WRITE = "write"


class ToolNetworkBehavior(StrEnum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


class ToolRiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolReceiptStatus(StrEnum):
    EXECUTED = "EXECUTED"
    DENIED = "DENIED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    capability: str
    required_arguments: tuple[str, ...]
    optional_arguments: tuple[str, ...] = ()
    access_class: ToolAccessClass = ToolAccessClass.READ
    network_behavior: ToolNetworkBehavior = ToolNetworkBehavior.NONE
    risk_class: ToolRiskClass = ToolRiskClass.LOW
    timeout_seconds: float = 30.0
    retry_policy: str = "none"
    preconditions: tuple[str, ...] = ()
    expected_evidence: tuple[str, ...] = ()
    failure_modes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.tool_id, str) or not self.tool_id.strip():
            raise ValueError("tool_id must be a non-empty string")
        if not isinstance(self.capability, str) or not self.capability.strip():
            raise ValueError("capability must be a non-empty string")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        overlap = set(self.required_arguments) & set(self.optional_arguments)
        if overlap:
            raise ValueError(f"tool arguments cannot be both required and optional: {sorted(overlap)}")


@dataclass(frozen=True)
class ToolExecutionContext:
    mode_decision: ModeDecision
    workspace_id: str
    workspace_root: str | Path
    configured_root_id: str
    within_workspace_scope: bool = True
    explicitly_forbidden: bool = False
    destructive: bool = False
    destructive_authorized: bool = False
    persistent_policy_change: bool = False
    persistent_policy_authorized: bool = False
    intent_scope_conflict: bool = False
    runtime_event_observer: Callable[[object], None] | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mode_decision, ModeDecision):
            raise TypeError("mode_decision must be a ModeDecision")
        for name in ("workspace_id", "configured_root_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.runtime_event_observer is not None and not callable(self.runtime_event_observer):
            raise TypeError("runtime_event_observer must be callable")
        object.__setattr__(self, "workspace_root", Path(self.workspace_root).expanduser().resolve())


@dataclass(frozen=True)
class ToolRequest:
    operation_id: str
    tool_id: str
    arguments: Mapping[str, Any]
    context: ToolExecutionContext

    def __post_init__(self) -> None:
        if not isinstance(self.operation_id, str) or not self.operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        if not isinstance(self.tool_id, str) or not self.tool_id.strip():
            raise ValueError("tool_id must be a non-empty string")
        if not isinstance(self.arguments, Mapping):
            raise TypeError("arguments must be a mapping")
        if not isinstance(self.context, ToolExecutionContext):
            raise TypeError("context must be ToolExecutionContext")


@dataclass(frozen=True)
class ToolExecutionResult:
    output: Mapping[str, Any]
    evidence: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class ToolReceipt:
    operation_id: str
    tool_id: str
    status: ToolReceiptStatus
    authorization: AuthorizationDecision | None
    receipt_id: str = field(default_factory=lambda: f"tool-receipt-{uuid.uuid4().hex}")
    output: Mapping[str, Any] | None = None
    evidence: tuple[Mapping[str, Any], ...] = ()
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, str) or not self.receipt_id.strip():
            raise ValueError("receipt_id must be a non-empty string")
        if self.receipt_id == self.operation_id:
            raise ValueError("receipt_id must remain distinct from operation_id")


class ToolHandler(Protocol):
    def __call__(self, request: ToolRequest) -> ToolExecutionResult: ...


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry:
    """Explicit registry; unregistered model requests cannot execute."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if not isinstance(spec, ToolSpec):
            raise TypeError("spec must be ToolSpec")
        if not callable(handler):
            raise TypeError("handler must be callable")
        if spec.tool_id in self._tools:
            raise ValueError(f"tool already registered: {spec.tool_id}")
        self._tools[spec.tool_id] = RegisteredTool(spec=spec, handler=handler)

    def get(self, tool_id: str) -> RegisteredTool | None:
        return self._tools.get(tool_id)

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools[key].spec for key in sorted(self._tools))


class GovernedToolOrchestrator:
    """Deterministic lookup -> authorize -> execute -> receipt owner."""

    def __init__(self, *, registry: ToolRegistry) -> None:
        if not isinstance(registry, ToolRegistry):
            raise TypeError("registry must be ToolRegistry")
        self.registry = registry
        self._receipts: dict[str, ToolReceipt] = {}

    def invoke(self, request: ToolRequest) -> ToolReceipt:
        if not isinstance(request, ToolRequest):
            raise TypeError("request must be ToolRequest")
        existing = self._receipts.get(request.operation_id)
        if existing is not None:
            if existing.tool_id != request.tool_id:
                raise ValueError("operation_id already used for a different tool")
            return existing

        registered = self.registry.get(request.tool_id)
        if registered is None:
            receipt = ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.DENIED,
                authorization=None,
                error_code="TOOL_NOT_REGISTERED",
                error_message="tool is not registered",
            )
            self._receipts[request.operation_id] = receipt
            return receipt

        try:
            _validate_arguments(registered.spec, request.arguments)
        except Exception as exc:
            receipt = ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.FAILED,
                authorization=None,
                error_code="INVALID_TOOL_ARGUMENTS",
                error_message=f"{type(exc).__name__}: {exc}",
            )
            self._receipts[request.operation_id] = receipt
            return receipt

        authorization = resolve_authorization(
            AuthorizationRequest(
                tool_id=registered.spec.tool_id,
                capability=registered.spec.capability,
                access_class=registered.spec.access_class.value,
                network_behavior=registered.spec.network_behavior.value,
                risk_class=registered.spec.risk_class.value,
                mode=request.context.mode_decision.mode,
                allowed_capabilities=request.context.mode_decision.capabilities,
                within_workspace_scope=request.context.within_workspace_scope,
                explicitly_forbidden=request.context.explicitly_forbidden,
                destructive=request.context.destructive,
                destructive_authorized=request.context.destructive_authorized,
                persistent_policy_change=request.context.persistent_policy_change,
                persistent_policy_authorized=request.context.persistent_policy_authorized,
                intent_scope_conflict=request.context.intent_scope_conflict,
            )
        )

        if authorization.verdict is AuthorizationVerdict.DENY:
            receipt = ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.DENIED,
                authorization=authorization,
                error_code="AUTHORIZATION_DENIED",
                error_message=authorization.rationale,
            )
            self._receipts[request.operation_id] = receipt
            return receipt
        if authorization.verdict is AuthorizationVerdict.ESCALATE:
            receipt = ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.ESCALATED,
                authorization=authorization,
                error_code="AUTHORIZATION_ESCALATED",
                error_message=authorization.rationale,
            )
            self._receipts[request.operation_id] = receipt
            return receipt

        try:
            result = registered.handler(request)
            if not isinstance(result, ToolExecutionResult):
                raise TypeError("tool handler must return ToolExecutionResult")
        except Exception as exc:
            receipt = ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.FAILED,
                authorization=authorization,
                error_code="TOOL_EXECUTION_FAILED",
                error_message=f"{type(exc).__name__}: {exc}",
            )
        else:
            receipt = ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.EXECUTED,
                authorization=authorization,
                output=dict(result.output),
                evidence=tuple(dict(item) for item in result.evidence),
            )
        self._receipts[request.operation_id] = receipt
        return receipt


def workspace_read_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.read",
        capability="inspect",
        required_arguments=("path",),
        optional_arguments=(),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=10.0,
        retry_policy="none",
        preconditions=("relative workspace path", "non-symlink target", "UTF-8 text file"),
        expected_evidence=("verified live file content", "sha256"),
        failure_modes=("path escape", "missing file", "symlink target", "non-UTF-8 file"),
    )


def workspace_replace_text_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.replace_text",
        capability="modify",
        required_arguments=("path", "old_text", "new_text"),
        optional_arguments=(),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.MEDIUM,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=("coding mode delegates modify", "relative workspace path", "unique exact match"),
        expected_evidence=("before sha256", "after sha256", "replacement count"),
        failure_modes=("authorization failure", "path escape", "symlink target", "non-UTF-8 file", "non-unique match"),
    )


def build_workspace_read_handler(evidence_service: EvidenceService) -> ToolHandler:
    if not isinstance(evidence_service, EvidenceService):
        raise TypeError("evidence_service must be EvidenceService")

    def handler(request: ToolRequest) -> ToolExecutionResult:
        path = _resolve_workspace_file(request.context.workspace_root, request.arguments["path"])
        if path.is_symlink():
            raise ValueError("workspace.read does not follow symlink targets")
        if not path.is_file():
            raise FileNotFoundError("workspace file does not exist")
        relative = path.relative_to(request.context.workspace_root).as_posix()
        evidence = evidence_service.read_current_file(
            request.context.configured_root_id,
            relative,
        )
        output = {
            "path": relative,
            "content": evidence.content,
            "sha256": evidence.sha256,
        }
        return ToolExecutionResult(
            output=output,
            evidence=({
                "source_class": evidence.source_class,
                "root_id": evidence.root_id,
                "relative_path": evidence.relative_path,
                "sha256": evidence.sha256,
            },),
        )

    return handler


def build_workspace_replace_text_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        path = _resolve_workspace_file(request.context.workspace_root, request.arguments["path"])
        if path.is_symlink():
            raise ValueError("workspace.replace_text does not modify symlink targets")
        if not path.is_file():
            raise FileNotFoundError("workspace file does not exist")
        old_text = request.arguments["old_text"]
        new_text = request.arguments["new_text"]
        if not isinstance(old_text, str) or not old_text:
            raise ValueError("old_text must be a non-empty string")
        if not isinstance(new_text, str):
            raise ValueError("new_text must be a string")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("workspace file is not UTF-8 text") from exc
        count = content.count(old_text)
        if count != 1:
            raise ValueError(f"old_text must occur exactly once; observed {count}")
        before_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        updated = content.replace(old_text, new_text, 1)
        after_hash = hashlib.sha256(updated.encode("utf-8")).hexdigest()
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(updated, encoding="utf-8", newline="")
        os.replace(temporary, path)
        relative = path.relative_to(request.context.workspace_root).as_posix()
        output = {
            "path": relative,
            "before_sha256": before_hash,
            "after_sha256": after_hash,
            "replacement_count": 1,
        }
        return ToolExecutionResult(
            output=output,
            evidence=({
                "source_class": "governed_workspace_mutation",
                "path": relative,
                "before_sha256": before_hash,
                "after_sha256": after_hash,
                "replacement_count": 1,
            },),
        )

    return handler


def _validate_arguments(spec: ToolSpec, arguments: Mapping[str, Any]) -> None:
    keys = set(arguments)
    required = set(spec.required_arguments)
    allowed = required | set(spec.optional_arguments)
    missing = sorted(required - keys)
    unexpected = sorted(keys - allowed)
    if missing:
        raise ValueError(f"missing required tool arguments: {missing}")
    if unexpected:
        raise ValueError(f"unexpected tool arguments: {unexpected}")


def _resolve_workspace_file(workspace_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a non-empty string")
    relative = Path(value.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("path must remain relative to the active workspace")
    root = workspace_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes the active workspace") from exc
    return candidate
