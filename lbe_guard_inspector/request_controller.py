"""Runtime-neutral coordination of bounded reasoning and deterministic LBE tools."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from agent import Context, GovernanceError
from audit_controller import AuditError, resolve_rule

from .contracts import ContractValidationError, validate_contract
from .guard_catalog import select_guard_catalog
from .guard_runner import GuardRunner
from .project_profiler import ProjectProfiler
from .reasoning_contracts import (
    EvidenceRequest,
    ExplanationRequest,
    ExplanationResult,
    LBERequest,
    LBEResponse,
    OrchestrationError,
    ReasoningBackend,
    ReasoningPlan,
    ReasoningRequest,
)
from .workspace_identity import resolve_workspace_identity, scoped_context


_APPROVED_TOOLS = frozenset({"workspace.read"})


class LBERequestController:
    """Coordinates LBE dependencies without becoming a provider or authority."""

    def __init__(
        self,
        *,
        backend: ReasoningBackend,
        context: Context | None = None,
        context_loader: Callable[[], Context] = Context.load,
        profiler: ProjectProfiler | None = None,
        catalog_selector: Callable[[dict[str, Any]], dict[str, Any]] = select_guard_catalog,
        runner: GuardRunner | None = None,
        rule_resolver: Callable[[str, str], Any] = resolve_rule,
    ) -> None:
        self._backend = backend
        self._context = context
        self._context_loader = context_loader
        self._profiler = profiler or ProjectProfiler()
        self._catalog_selector = catalog_selector
        self._runner = runner or GuardRunner()
        self._rule_resolver = rule_resolver

    def run(self, request: LBERequest) -> LBEResponse:
        """Run planning, deterministic inspection, and explanation in read-only mode."""
        try:
            return self._run(request)
        except _ControllerFailure as exc:
            return self._error_response(request, exc.code, str(exc), exc.details)
        except Exception as exc:  # provider failures and defensive boundary
            return self._error_response(request, "ORCHESTRATION_ERROR", f"{type(exc).__name__}: {exc}", ())

    def _run(self, request: LBERequest) -> LBEResponse:
        problem = _text(request.problem, "problem")
        context = self._context or self._context_loader()
        identity = resolve_workspace_identity(context, request.workspace_root)
        profile = self._profiler.profile(
            identity.target_project_root, configured_root_id=identity.configured_root_id
        )
        catalog = self._catalog_selector(profile)
        approved_guards = tuple(dict.fromkeys(
            [*catalog.get("foundation_guard_ids", []), *catalog.get("optional_guard_ids", [])]
        ))
        reasoning_request = ReasoningRequest(
            problem=problem,
            workspace_identity={
                "configured_root_id": identity.configured_root_id,
                "target_project_root": str(identity.target_project_root),
                "workspace_id": identity.workspace_id,
            },
            workspace_profile=profile,
            approved_guard_ids=approved_guards,
            approved_tools=tuple(sorted(_APPROVED_TOOLS)),
            reference_context=tuple(dict(item) for item in request.reference_context),
        )
        plan = _coerce_plan(self._backend.plan(reasoning_request))
        self._validate_plan(plan, identity.target_project_root, approved_guards)
        if not plan.candidate_guard_ids:
            return self._response(
                request, identity, profile, plan, None, None, "INSUFFICIENT_EVIDENCE",
                OrchestrationError("NO_GUARD_SELECTED", "Reasoning plan selected no approved guard."),
            )

        guard_id = next(guard for guard in approved_guards if guard in plan.candidate_guard_ids)
        pack_id = _pack_for(guard_id)
        try:
            self._rule_resolver(pack_id, guard_id)
        except (AuditError, OSError, ValueError) as exc:
            raise _ControllerFailure("UNREGISTERED_GUARD", f"Approved guard is not registered: {guard_id}: {exc}") from exc
        decision = self._runner.run(
            problem=problem,
            workspace_root=str(identity.target_project_root),
            workspace_id=identity.workspace_id,
            pack_id=pack_id,
            rule_id=guard_id,
            guard_id=guard_id,
            roots=[identity.configured_root_id],
            extensions=None,
            reason=f"controller-selected guard inspection: {guard_id}",
            retrieval_mode="guard",
            query=problem,
            path_patterns=None,
            evidence_requirements=None,
        )
        guard_result = decision.get("guard_result")
        package = decision.get("evidence_package")
        if not isinstance(guard_result, Mapping) or not isinstance(package, Mapping):
            raise _ControllerFailure("INVALID_DETERMINISTIC_RESULT", "GuardRunner did not return guard_result and evidence_package.")
        try:
            validated_result = validate_contract("guard_result", guard_result)
            validated_package = validate_contract("evidence_package", package)
        except ContractValidationError as exc:
            raise _ControllerFailure("INVALID_DETERMINISTIC_RESULT", str(exc), tuple(exc.errors)) from exc
        explanation_request = ExplanationRequest(
            guard_result=validated_result,
            current_workspace_evidence=tuple(validated_package["current_workspace_evidence"]),
            validation_evidence=tuple(validated_package["validation_evidence"]),
            governance_state=validated_result["governance_state"],
            explanation_focus=plan.explanation_focus,
        )
        try:
            explanation = _coerce_explanation(self._backend.explain(explanation_request))
        except Exception as exc:
            return self._response(
                request, identity, profile, plan, validated_result, None, "ORCHESTRATION_ERROR",
                OrchestrationError("EXPLANATION_FAILED", f"{type(exc).__name__}: {exc}"),
            )
        return self._response(request, identity, profile, plan, validated_result, explanation, "COMPLETED", None)

    def _validate_plan(self, plan: ReasoningPlan, root: Path, approved_guards: tuple[str, ...]) -> None:
        if len(plan.candidate_guard_ids) > 1:
            raise _ControllerFailure("MULTIPLE_GUARDS_SELECTED", "Reasoning plan must select at most one approved guard.")
        unknown_guards = sorted(set(plan.candidate_guard_ids) - set(approved_guards))
        if unknown_guards:
            raise _ControllerFailure("UNKNOWN_GUARD", "Reasoning plan requested unknown guard IDs.", tuple(unknown_guards))
        if plan.validation_requests:
            raise _ControllerFailure(
                "MODEL_VALIDATION_REQUEST_FORBIDDEN",
                "Reasoning plans must not select validation IDs; deterministic validation is owned by LBE.",
                tuple(plan.validation_requests),
            )
        for evidence in plan.evidence_requests:
            if evidence.tool_id not in _APPROVED_TOOLS:
                raise _ControllerFailure("UNKNOWN_TOOL", f"Reasoning plan requested unknown tool: {evidence.tool_id}")
            _bounded_path(root, evidence.path)
        if plan.candidate_guard_ids and not plan.evidence_requests:
            raise _ControllerFailure("MISSING_EVIDENCE_REQUEST", "A selected guard requires a bounded evidence request.")

    @staticmethod
    def _response(request, identity, profile, plan, result, explanation, outcome, error) -> LBEResponse:
        return LBEResponse(
            task_id=request.task_id or f"task-{uuid.uuid4()}",
            workspace_identity={"configured_root_id": identity.configured_root_id, "target_project_root": str(identity.target_project_root), "workspace_id": identity.workspace_id},
            workspace_profile=profile, plan=plan, deterministic_result=result,
            explanation=explanation, outcome=outcome, error=error,
        )

    def _error_response(self, request: LBERequest, code: str, message: str, details: tuple[str, ...]) -> LBEResponse:
        return LBEResponse(
            task_id=request.task_id or f"task-{uuid.uuid4()}", workspace_identity={}, workspace_profile={},
            plan=None, deterministic_result=None, explanation=None, outcome="ORCHESTRATION_ERROR",
            error=OrchestrationError(code, message, details),
        )


class _ControllerFailure(ValueError):
    def __init__(self, code: str, message: str, details: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.code, self.details = code, details


def _coerce_plan(value: ReasoningPlan | Mapping[str, Any]) -> ReasoningPlan:
    return value if isinstance(value, ReasoningPlan) else ReasoningPlan.from_mapping(value)


def _coerce_explanation(value: ExplanationResult | Mapping[str, Any]) -> ExplanationResult:
    return value if isinstance(value, ExplanationResult) else ExplanationResult.from_mapping(value)


def _bounded_path(root: Path, value: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise _ControllerFailure("OUT_OF_WORKSPACE_PATH", f"Evidence path escapes the workspace: {value}")
    try:
        (root / path).resolve().relative_to(root)
    except ValueError as exc:
        raise _ControllerFailure("OUT_OF_WORKSPACE_PATH", f"Evidence path escapes the workspace: {value}") from exc


def _pack_for(guard_id: str) -> str:
    prefix = guard_id.split(".", 1)[0]
    if prefix == "module_registry":
        return "module_registry"
    return prefix


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _ControllerFailure("INVALID_REQUEST", f"{field} must be a non-empty string")
    return value.strip()
