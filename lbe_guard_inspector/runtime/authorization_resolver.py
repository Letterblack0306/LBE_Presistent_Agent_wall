"""Deterministic authorization resolver for R6C.

This layer decides whether a requested capability is already within delegated
runtime authority. It does not execute tools, mutate the workspace, or create
new policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .mode_controller import ModeDecision


class AuthorizationVerdict(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class AuthorizationRequest:
    mode_decision: ModeDecision
    capability: str
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
        if not isinstance(self.capability, str) or not self.capability.strip():
            raise ValueError("capability must be a non-empty string")


@dataclass(frozen=True)
class AuthorizationDecision:
    verdict: AuthorizationVerdict
    capability: str
    rationale: str
    meaning: str | None = None
    fix: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()
    decision_options: tuple[str, ...] = ()

    @property
    def decisionOptions(self) -> tuple[str, ...]:
        return self.decision_options

    def blocker_dict(self) -> dict[str, object]:
        if not self.meaning:
            return {}
        return {
            "meaning": self.meaning,
            "fix": list(self.fix),
            "forbidden": list(self.forbidden),
            "decisionOptions": list(self.decision_options),
        }


def resolve_authorization(request: AuthorizationRequest) -> AuthorizationDecision:
    """Resolve existing delegated authority as ALLOW, DENY, or ESCALATE.

    ALLOW means the active typed mode already delegates the capability for the
    requested scope. DENY is reserved for an explicitly forbidden operation.
    ESCALATE means the operation would expand or conflict with current authority.
    """
    if not isinstance(request, AuthorizationRequest):
        raise TypeError("request must be an AuthorizationRequest")

    capability = request.capability.strip()

    if request.explicitly_forbidden:
        return AuthorizationDecision(
            verdict=AuthorizationVerdict.DENY,
            capability=capability,
            rationale="Operation is explicitly forbidden by active policy.",
            meaning="Operation is explicitly forbidden by active policy.",
            fix=("Select an operation within allowed policy", "Review active task scope"),
            forbidden=("Do not execute forbidden operations", "Do not bypass governance"),
            decision_options=("Select allowed operation", "Update scope", "Ask user"),
        )

    if request.approval_granted:
        if not request.within_workspace_scope:
            return AuthorizationDecision(
                verdict=AuthorizationVerdict.ESCALATE,
                capability=capability,
                rationale="Approval cannot expand beyond the active workspace scope.",
                meaning="Approval cannot expand beyond the active workspace scope.",
                fix=("Confine operation to workspace scope", "Update task scope boundaries"),
                forbidden=("Do not execute operations outside workspace",),
                decision_options=("Confine to workspace", "Update scope", "Ask user"),
            )
        if request.intent_scope_conflict:
            return AuthorizationDecision(
                verdict=AuthorizationVerdict.ESCALATE,
                capability=capability,
                rationale="Approval cannot resolve an unresolved intent or scope conflict.",
                meaning="Unresolved intent or scope conflict.",
                fix=("Re-register intent to match scope", "Resolve intent scope mismatch"),
                forbidden=("Do not force proof with mismatched intent",),
                decision_options=("Re-register intent", "Update scope", "Ask user"),
            )
        return AuthorizationDecision(
            verdict=AuthorizationVerdict.ALLOW,
            capability=capability,
            rationale="Explicit Agent Wall approval authorizes this operation.",
        )

    if capability not in request.mode_decision.capabilities:
        return AuthorizationDecision(
            verdict=AuthorizationVerdict.ESCALATE,
            capability=capability,
            rationale=(
                f"Capability '{capability}' is not enabled by "
                f"{request.mode_decision.mode} mode policy."
            ),
            meaning=f"Capability not enabled in {request.mode_decision.mode} mode.",
            fix=(f"Switch to a mode enabling '{capability}'", "Select a permitted capability"),
            forbidden=("Do not bypass mode capabilities",),
            decision_options=("Switch mode", "Select permitted capability", "Ask user"),
        )

    if not request.within_workspace_scope:
        return AuthorizationDecision(
            verdict=AuthorizationVerdict.ESCALATE,
            capability=capability,
            rationale="Operation expands beyond the active workspace scope.",
            meaning="Files or operations outside allowed workspace scope.",
            fix=("Review changed files or targets", "Roll back or expand scope"),
            forbidden=("Do not mark clean", "Do not silently widen scope"),
            decision_options=("Roll back", "Expand scope", "Ask user"),
        )

    if request.intent_scope_conflict:
        return AuthorizationDecision(
            verdict=AuthorizationVerdict.ESCALATE,
            capability=capability,
            rationale="Operation has unresolved intent or scope conflict.",
            meaning="Intent scope mismatch.",
            fix=("Register intent covering target paths",),
            forbidden=("Do not change files without intent",),
            decision_options=("Register intent", "Update scope", "Ask user"),
        )

    if request.destructive and not request.destructive_authorized:
        return AuthorizationDecision(
            verdict=AuthorizationVerdict.ESCALATE,
            capability=capability,
            rationale="Destructive operation exceeds delegated authority.",
            meaning="Destructive command requires explicit approval.",
            fix=("Request explicit approval for destructive operation", "Use safe non-destructive command"),
            forbidden=("Do not run unapproved destructive commands",),
            decision_options=("Request approval", "Use safe command", "Ask user"),
        )

    if request.persistent_policy_change and not request.persistent_policy_authorized:
        return AuthorizationDecision(
            verdict=AuthorizationVerdict.ESCALATE,
            capability=capability,
            rationale="Persistent policy change is not already delegated.",
            meaning="Persistent policy change requires separate authority.",
            fix=("Request policy change authorization",),
            forbidden=("Do not silently mutate policy",),
            decision_options=("Request authorization", "Ask user"),
        )

    return AuthorizationDecision(
        verdict=AuthorizationVerdict.ALLOW,
        capability=capability,
        rationale="Capability is already authorized by the active runtime policy.",
    )
