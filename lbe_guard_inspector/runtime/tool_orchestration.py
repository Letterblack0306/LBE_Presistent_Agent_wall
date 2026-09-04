"""Governed tool orchestration for the R6E runtime slice.

The orchestrator owns lifecycle ordering only: registered lookup, deterministic
R6C authorization, bounded handler invocation, structured receipts, and
operation-id idempotency. Tool implementations remain separate services.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol
import hashlib
import shutil
import uuid

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
    approval_granted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mode_decision, ModeDecision):
            raise TypeError("mode_decision must be a ModeDecision")
        for name in ("workspace_id", "configured_root_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
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
    output: Mapping[str, Any] | None = None
    evidence: tuple[Mapping[str, Any], ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    receipt_id: str = field(default_factory=lambda: f"receipt-{uuid.uuid4().hex}")


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
        if spec.tool_id in self._tools:
            raise ValueError(f"tool already registered: {spec.tool_id}")
        self._tools[spec.tool_id] = RegisteredTool(spec=spec, handler=handler)

    def get(self, tool_id: str) -> RegisteredTool | None:
        return self._tools.get(str(tool_id).strip())

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools[key].spec for key in sorted(self._tools))


class GovernedToolOrchestrator:
    """Run registered tools only after R6C authorization succeeds."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        authorization_resolver: Callable[[AuthorizationRequest], AuthorizationDecision] = resolve_authorization,
    ) -> None:
        self._registry = registry
        self._authorization_resolver = authorization_resolver
        self._receipts: dict[str, ToolReceipt] = {}
        self._requests: dict[str, ToolRequest] = {}

    def invoke(self, request: ToolRequest) -> ToolReceipt:
        if not isinstance(request, ToolRequest):
            raise TypeError("request must be ToolRequest")
        prior = self._receipts.get(request.operation_id)
        if prior is not None:
            if prior.status is not ToolReceiptStatus.ESCALATED or not request.context.approval_granted:
                return prior
            original = self._requests.get(request.operation_id)
            if original is None or not _same_operation_request(original, request):
                return prior
        else:
            self._requests[request.operation_id] = request

        registered = self._registry.get(request.tool_id)
        if registered is None:
            return self._remember(ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.FAILED,
                authorization=None,
                error_code="UNREGISTERED_TOOL",
                error_message=f"tool is not registered: {request.tool_id}",
            ))

        argument_error = _validate_arguments(registered.spec, request.arguments)
        if argument_error is not None:
            return self._remember(ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.FAILED,
                authorization=None,
                error_code="INVALID_TOOL_ARGUMENTS",
                error_message=argument_error,
            ))

        context = request.context
        authorization = self._authorization_resolver(AuthorizationRequest(
            mode_decision=context.mode_decision,
            capability=registered.spec.capability,
            within_workspace_scope=context.within_workspace_scope,
            explicitly_forbidden=context.explicitly_forbidden,
            destructive=context.destructive,
            destructive_authorized=context.destructive_authorized,
            persistent_policy_change=context.persistent_policy_change,
            persistent_policy_authorized=context.persistent_policy_authorized,
            intent_scope_conflict=context.intent_scope_conflict,
            approval_granted=context.approval_granted,
        ))
        if authorization.verdict is AuthorizationVerdict.DENY:
            return self._remember(ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.DENIED,
                authorization=authorization,
                error_code="AUTHORIZATION_DENIED",
                error_message=authorization.rationale,
            ))
        if authorization.verdict is AuthorizationVerdict.ESCALATE:
            return self._remember(ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.ESCALATED,
                authorization=authorization,
                error_code="AUTHORIZATION_REQUIRED",
                error_message=authorization.rationale,
            ))

        try:
            result = registered.handler(request)
            if not isinstance(result, ToolExecutionResult):
                raise TypeError("tool handler must return ToolExecutionResult")
        except Exception as exc:
            return self._remember(ToolReceipt(
                operation_id=request.operation_id,
                tool_id=request.tool_id,
                status=ToolReceiptStatus.FAILED,
                authorization=authorization,
                error_code="TOOL_EXECUTION_FAILED",
                error_message=f"{type(exc).__name__}: {exc}",
            ))

        return self._remember(ToolReceipt(
            operation_id=request.operation_id,
            tool_id=request.tool_id,
            status=ToolReceiptStatus.EXECUTED,
            authorization=authorization,
            output=dict(result.output),
            evidence=tuple(dict(item) for item in result.evidence),
        ))

    def receipt(self, operation_id: str) -> ToolReceipt | None:
        return self._receipts.get(operation_id)

    def _remember(self, receipt: ToolReceipt) -> ToolReceipt:
        self._receipts[receipt.operation_id] = receipt
        return receipt


def workspace_read_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.read",
        capability="inspect",
        required_arguments=("path",),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=30.0,
        retry_policy="transient_read_failure_only",
        preconditions=("relative workspace path", "active workspace scope"),
        expected_evidence=("current workspace evidence", "content hash"),
        failure_modes=("invalid path", "missing file", "read failure", "authorization failure"),
    )


def build_workspace_read_handler(evidence_service: EvidenceService) -> ToolHandler:
    """Delegate real workspace reads to the existing EvidenceService owner."""
    if not isinstance(evidence_service, EvidenceService):
        raise TypeError("evidence_service must be EvidenceService")

    def handler(request: ToolRequest) -> ToolExecutionResult:
        raw_path = request.arguments["path"]
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("path must be a non-empty string")
        path = raw_path.replace("\\", "/").strip()
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("path must stay within the active workspace")

        context = request.context
        package = evidence_service.build_evidence_package(
            task_id=request.operation_id,
            query=path,
            workspace_id=context.workspace_id,
            workspace_root=str(context.workspace_root),
            max_results=1,
            roots=[context.configured_root_id],
            retrieval_mode="guard",
            rule_id="workspace.read",
            path_patterns=[path],
            evidence_requirements=["explicit governed workspace.read request"],
        )
        evidence = tuple(dict(item) for item in package.get("current_workspace_evidence", ()))
        return ToolExecutionResult(
            output={
                "path": path,
                "evidence_count": len(evidence),
                "missing_evidence": list(package.get("missing_evidence", ())),
            },
            evidence=evidence,
        )

    return handler


def workspace_list_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.list",
        capability="inspect",
        required_arguments=("path",),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=30.0,
        retry_policy="transient_read_failure_only",
        preconditions=("relative workspace directory", "active workspace scope"),
        expected_evidence=("directory entries", "entry types"),
        failure_modes=("invalid path", "workspace escape", "missing directory", "read failure", "authorization failure"),
    )


def build_workspace_list_handler() -> ToolHandler:
    """List one bounded directory without exposing direct provider filesystem access."""

    def handler(request: ToolRequest) -> ToolExecutionResult:
        raw_path = request.arguments["path"]
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("path must be a non-empty string")
        relative = Path(raw_path.replace("\\", "/").strip())
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("path must stay within the active workspace")

        root = Path(request.context.workspace_root).resolve()
        candidate = (root / relative).resolve(strict=False)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("path must stay within the active workspace") from exc
        if not candidate.exists():
            raise FileNotFoundError(f"directory does not exist: {relative.as_posix() or '.'}")
        if not candidate.is_dir():
            raise ValueError("workspace.list path must be a directory")

        entries = []
        evidence = []
        for item in sorted(candidate.iterdir(), key=lambda value: value.name.casefold()):
            if item.is_symlink():
                continue
            entry_type = "directory" if item.is_dir() else "file" if item.is_file() else "other"
            entry_path = (relative / item.name).as_posix() if relative.as_posix() != "." else item.name
            entries.append({"name": item.name, "path": entry_path, "type": entry_type})
            evidence.append({
                "ref": f"workspace:{request.context.workspace_id}:{entry_path}",
                "source_type": "workspace",
                "workspace_id": request.context.workspace_id,
                "path": str(item),
                "entry_type": entry_type,
                "verified": True,
                "metadata": {"operation_id": request.operation_id, "tool_id": request.tool_id},
            })

        return ToolExecutionResult(
            output={"path": relative.as_posix() or ".", "entries": entries, "entry_count": len(entries)},
            evidence=tuple(evidence),
        )

    return handler


def workspace_glob_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.glob",
        capability="inspect",
        required_arguments=("pattern",),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=30.0,
        retry_policy="transient_read_failure_only",
        preconditions=("relative workspace glob pattern", "active workspace scope"),
        expected_evidence=("matching workspace paths", "entry types"),
        failure_modes=("invalid pattern", "workspace escape", "read failure", "authorization failure"),
    )


def build_workspace_glob_handler() -> ToolHandler:
    """Match bounded workspace paths without exposing direct provider filesystem access."""

    def handler(request: ToolRequest) -> ToolExecutionResult:
        raw_pattern = request.arguments["pattern"]
        if not isinstance(raw_pattern, str) or not raw_pattern.strip():
            raise ValueError("pattern must be a non-empty string")
        pattern = raw_pattern.replace("\\", "/").strip()
        relative = Path(pattern)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("pattern must stay within the active workspace")

        root = Path(request.context.workspace_root).resolve()
        matches = []
        evidence = []
        for item in sorted(root.glob(pattern), key=lambda value: value.as_posix().casefold()):
            if item.is_symlink():
                continue
            candidate = item.resolve(strict=False)
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            match_path = item.relative_to(root).as_posix()
            entry_type = "directory" if item.is_dir() else "file" if item.is_file() else "other"
            matches.append({"path": match_path, "type": entry_type})
            evidence.append({
                "ref": f"workspace:{request.context.workspace_id}:{match_path}",
                "source_type": "workspace",
                "workspace_id": request.context.workspace_id,
                "path": str(item),
                "entry_type": entry_type,
                "verified": True,
                "metadata": {"operation_id": request.operation_id, "tool_id": request.tool_id},
            })

        return ToolExecutionResult(
            output={"pattern": pattern, "matches": matches, "match_count": len(matches)},
            evidence=tuple(evidence),
        )

    return handler


def workspace_search_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.search",
        capability="inspect",
        required_arguments=("query",),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=30.0,
        retry_policy="transient_read_failure_only",
        preconditions=("non-empty workspace query", "active workspace scope"),
        expected_evidence=("indexed reference evidence", "current workspace evidence"),
        failure_modes=("invalid query", "workspace escape", "search failure", "authorization failure"),
    )


def build_workspace_search_handler(evidence_service: EvidenceService) -> ToolHandler:
    """Delegate governed workspace search to the existing EvidenceService owner."""
    if not isinstance(evidence_service, EvidenceService):
        raise TypeError("evidence_service must be EvidenceService")

    def handler(request: ToolRequest) -> ToolExecutionResult:
        raw_query = request.arguments["query"]
        if not isinstance(raw_query, str) or not raw_query.strip():
            raise ValueError("query must be a non-empty string")
        context = request.context
        package = evidence_service.build_evidence_package(
            task_id=request.operation_id,
            query=raw_query.strip(),
            workspace_id=context.workspace_id,
            workspace_root=str(context.workspace_root),
            max_results=50,
            roots=[context.configured_root_id],
            retrieval_mode="investigation",
            evidence_requirements=["explicit governed workspace.search request"],
        )
        indexed = tuple(dict(item) for item in package.get("indexed_reference_evidence", ()))
        current = tuple(dict(item) for item in package.get("current_workspace_evidence", ()))
        return ToolExecutionResult(
            output={
                "query": raw_query.strip(),
                "indexed_result_count": len(indexed),
                "current_result_count": len(current),
                "missing_evidence": list(package.get("missing_evidence", ())),
                "results": [
                    {
                        "ref": item.get("ref"),
                        "path": item.get("path"),
                        "line_start": item.get("line_start"),
                        "line_end": item.get("line_end"),
                        "snippet": item.get("snippet"),
                        "score": item.get("score"),
                        "source_type": item.get("source_type"),
                        "verified": item.get("verified"),
                    }
                    for item in (*indexed, *current)
                ],
            },
            evidence=(*indexed, *current),
        )

    return handler


_DELETABLE_CLASSIFICATIONS = frozenset({
    "GENERATED_REGENERABLE",
    "CACHE",
    "TEMPORARY",
    "OS_METADATA",
})
_PROTECTED_TOP_LEVEL = frozenset({".git", ".lbe", ".github"})


def workspace_delete_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.delete",
        capability="modify",
        required_arguments=("path", "classification", "expected_type"),
        optional_arguments=("expected_sha256",),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.HIGH,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=(
            "relative workspace path",
            "approved disposable classification",
            "active workspace scope",
            "expected type or hash matches",
            "protected authority paths excluded",
        ),
        expected_evidence=("deletion receipt", "before state or hash", "target absent"),
        failure_modes=(
            "invalid classification",
            "workspace escape",
            "symlink escape",
            "protected path",
            "type mismatch",
            "hash mismatch",
            "deletion failure",
        ),
    )


def build_workspace_delete_handler() -> ToolHandler:
    """Delete only already-classified disposable material inside the workspace."""

    def handler(request: ToolRequest) -> ToolExecutionResult:
        classification = str(request.arguments["classification"]).strip().upper()
        if classification not in _DELETABLE_CLASSIFICATIONS:
            raise ValueError("path classification is not approved for deletion")

        expected_type = str(request.arguments["expected_type"]).strip().lower()
        if expected_type not in {"file", "directory"}:
            raise ValueError("expected_type must be file or directory")

        raw_path = request.arguments["path"]
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("path must be a non-empty relative path")
        relative = Path(raw_path.replace("\\", "/").strip())
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("path must stay within the active workspace")
        if not relative.parts or relative.parts[0] in _PROTECTED_TOP_LEVEL:
            raise PermissionError("protected workspace authority path cannot be deleted")

        root = Path(request.context.workspace_root).resolve()
        candidate = root / relative
        if candidate == root:
            raise PermissionError("workspace root cannot be deleted")
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError("path escapes the active workspace") from exc
        if candidate.exists() and candidate.is_symlink():
            raise PermissionError("symlink deletion is not allowed")
        if not candidate.exists():
            raise FileNotFoundError(f"disposable path does not exist: {relative.as_posix()}")
        actual_type = "directory" if candidate.is_dir() else "file" if candidate.is_file() else "other"
        if actual_type != expected_type:
            raise ValueError("expected_type does not match target")

        before_sha256 = _workspace_file_sha256(candidate) if actual_type == "file" else None
        expected_sha256 = request.arguments.get("expected_sha256")
        if expected_sha256 is not None and expected_sha256 != before_sha256:
            raise ValueError("expected_sha256 does not match target")

        if actual_type == "directory":
            shutil.rmtree(candidate)
        else:
            candidate.unlink()
        if candidate.exists() or candidate.is_symlink():
            raise OSError("target remains after deletion")

        return ToolExecutionResult(
            output={
                "path": relative.as_posix(),
                "classification": classification,
                "expected_type": expected_type,
                "deleted": True,
            },
            evidence=(
                {
                    "ref": f"workspace:{request.context.workspace_id}:{relative.as_posix()}",
                    "source_type": "workspace",
                    "workspace_id": request.context.workspace_id,
                    "path": str(candidate),
                    "classification": classification,
                    "before_sha256": before_sha256,
                    "after_exists": False,
                    "verified": True,
                    "metadata": {
                        "operation_id": request.operation_id,
                        "tool_id": request.tool_id,
                    },
                },
            ),
        )

    return handler


def _workspace_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same_operation_request(original: ToolRequest, current: ToolRequest) -> bool:
    return (
        original.operation_id == current.operation_id
        and original.tool_id == current.tool_id
        and dict(original.arguments) == dict(current.arguments)
        and replace(original.context, approval_granted=False)
        == replace(current.context, approval_granted=False)
    )


def _validate_arguments(spec: ToolSpec, arguments: Mapping[str, Any]) -> str | None:
    allowed = set(spec.required_arguments) | set(spec.optional_arguments)
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        return f"unsupported arguments for {spec.tool_id}: {unknown}"
    missing = sorted(name for name in spec.required_arguments if name not in arguments)
    if missing:
        return f"missing required arguments for {spec.tool_id}: {missing}"
    return None
