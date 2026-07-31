"""
Public Behavior Contracts â€” LLM-facing vocabulary.

This is the ONLY interface the LLM sees. It defines abstract behaviors
without exposing private LBE Core implementation details (guard names,
gate IDs, enforcement algorithms, proprietary architecture).

The LLM reasons using these contracts. The Controller maps intent to
allowed behaviors. The private Translator resolves to actual guards/gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Mode = Literal["audit", "development"]
EvidenceType = Literal["workspace", "validation", "reference"]

BEHAVIOR_CONTRACT_VERSION = "1.0"


@dataclass(frozen=True)
class BehaviorContract:
    """
    Abstract behavior the LLM can understand and reason with.

    No private Core references: no guard names, no gate IDs, no
    enforcement algorithms, no proprietary boundaries.
    """
    name: str
    description: str
    modes: tuple[Mode, ...]
    requires_evidence: tuple[EvidenceType, ...]
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    authority: str  # Abstract: "deterministic_guards", "independent_verification", etc.


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PUBLIC BEHAVIOR VOCABULARY
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

BEHAVIOR_CONTRACTS: dict[str, BehaviorContract] = {
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Evidence & Truth
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "require_current_workspace_evidence": BehaviorContract(
        name="require_current_workspace_evidence",
        description=(
            "Any claim about the current workspace state must be backed by "
            "live, bounded inspection evidence. Reference knowledge and history "
            "may inform but cannot prove current state."
        ),
        modes=("audit", "development"),
        requires_evidence=("workspace", "validation"),
        allowed_actions=("inspect", "search", "compare", "verify"),
        forbidden_actions=(
            "assume_from_history",
            "assume_from_reference",
            "assume_from_index",
            "extrapolate_from_past",
        ),
        authority="deterministic_guards",
    ),

    "validation_before_acceptance": BehaviorContract(
        name="validation_before_acceptance",
        description=(
            "No change, finding, or conclusion is accepted without independent "
            "validation. The validator must be separate from the producer."
        ),
        modes=("audit", "development"),
        requires_evidence=("validation",),
        allowed_actions=("validate", "verify", "corroborate", "cross_check"),
        forbidden_actions=(
            "accept_unvalidated",
            "skip_validation",
            "self_validate",
            "assume_correctness",
        ),
        authority="independent_verification",
    ),

    "evidence_boundary_enforcement": BehaviorContract(
        name="evidence_boundary_enforcement",
        description=(
            "Evidence layers are distinct and ordered: "
            "reference informs â†’ workspace proves â†’ guards detect â†’ validation confirms. "
            "No layer substitutes for another."
        ),
        modes=("audit", "development"),
        requires_evidence=("reference", "workspace", "validation"),
        allowed_actions=(
            "reference_inform",
            "workspace_prove",
            "guard_detect",
            "validation_confirm",
        ),
        forbidden_actions=(
            "reference_prove",
            "assume_guard_result",
            "skip_validation",
            "collapse_layers",
        ),
        authority="layered_evidence",
    ),

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Mode Constraints
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "audit_mode_constraints": BehaviorContract(
        name="audit_mode_constraints",
        description=(
            "Audit mode is read-only. Only existing, approved guards execute. "
            "Output is evidence and findings â€” never modifications, proposals, "
            "or memory promotions."
        ),
        modes=("audit",),
        requires_evidence=("workspace", "validation", "reference"),
        allowed_actions=(
            "inspect",
            "collect_evidence",
            "run_existing_guards",
            "report_findings",
            "register_finding",
        ),
        forbidden_actions=(
            "modify",
            "propose_rules",
            "promote_memory",
            "execute_changes",
            "create_guards",
            "bypass_guards",
        ),
        authority="existing_guards_only",
    ),

    "development_mode_capabilities": BehaviorContract(
        name="development_mode_capabilities",
        description=(
            "Development mode allows discovery, proposal, and testing. "
            "All proposals must pass validation before promotion. "
            "Evidence boundary still applies."
        ),
        modes=("development",),
        requires_evidence=("workspace", "validation", "reference"),
        allowed_actions=(
            "discover",
            "propose",
            "test_candidate",
            "validate_proposal",
            "promote_after_validation",
        ),
        forbidden_actions=(
            "bypass_validation",
            "assume_correctness",
            "skip_evidence",
            "promote_without_proof",
        ),
        authority="proposed_rules_require_validation",
    ),

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Finding & Memory
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "finding_review_required": BehaviorContract(
        name="finding_review_required",
        description=(
            "Audit findings are not truth â€” they are candidates for review. "
            "Current workspace verification is required before any finding "
            "becomes validated memory or enhancement."
        ),
        modes=("audit", "development"),
        requires_evidence=("workspace", "validation"),
        allowed_actions=(
            "record_finding",
            "request_review",
            "verify_against_current",
            "categorize_finding",
        ),
        forbidden_actions=(
            "auto_promote_finding",
            "create_guard_from_finding",
            "assume_finding_is_truth",
            "skip_review",
        ),
        authority="review_register",
    ),

    "memory_is_historical_context": BehaviorContract(
        name="memory_is_historical_context",
        description=(
            "Session history, compaction, and promoted memory are historical "
            "context only. They never override live workspace evidence or "
            "current validation."
        ),
        modes=("audit", "development"),
        requires_evidence=("workspace", "validation"),
        allowed_actions=(
            "read_memory",
            "use_as_context",
            "correlate_with_current",
        ),
        forbidden_actions=(
            "treat_memory_as_truth",
            "override_workspace_with_memory",
            "promote_without_validation",
        ),
        authority="live_workspace_authoritative",
    ),

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Guard & Rule Discipline
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "use_only_approved_guards": BehaviorContract(
        name="use_only_approved_guards",
        description=(
            "Only guards from the approved catalog for the current profile "
            "may execute. No ad-hoc guard selection, no invented rules, "
            "no bypassing the catalog."
        ),
        modes=("audit", "development"),
        requires_evidence=("workspace", "validation"),
        allowed_actions=(
            "list_approved_guards",
            "execute_approved_guard",
            "request_guard_execution",
        ),
        forbidden_actions=(
            "invent_guard",
            "select_unapproved_guard",
            "bypass_catalog",
            "modify_guard_behavior",
        ),
        authority="approved_catalog_only",
    ),

    "proposed_rules_require_validation": BehaviorContract(
        name="proposed_rules_require_validation",
        description=(
            "Any proposed rule or guard must pass validation against current "
            "workspace evidence and independent corroboration before it can "
            "enter the approved catalog."
        ),
        modes=("development",),
        requires_evidence=("workspace", "validation"),
        allowed_actions=(
            "propose_rule",
            "test_proposal",
            "validate_proposal",
            "submit_for_approval",
        ),
        forbidden_actions=(
            "auto_approve_proposal",
            "skip_proposal_validation",
            "promote_unvalidated_rule",
        ),
        authority="validation_gate",
    ),
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MODE PROTOCOL (Public)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

MODE_BEHAVIOR_MAP: dict[Mode, tuple[str, ...]] = {
    "audit": (
        "require_current_workspace_evidence",
        "validation_before_acceptance",
        "evidence_boundary_enforcement",
        "audit_mode_constraints",
        "finding_review_required",
        "memory_is_historical_context",
        "use_only_approved_guards",
    ),
    "development": (
        "require_current_workspace_evidence",
        "validation_before_acceptance",
        "evidence_boundary_enforcement",
        "development_mode_capabilities",
        "finding_review_required",
        "memory_is_historical_context",
        "use_only_approved_guards",
        "proposed_rules_require_validation",
    ),
}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PUBLIC QUERY API
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_behavior(name: str) -> BehaviorContract:
    """Get a behavior contract by name. Raises KeyError if unknown."""
    if name not in BEHAVIOR_CONTRACTS:
        raise KeyError(f"Unknown behavior: {name}. Available: {sorted(BEHAVIOR_CONTRACTS)}")
    return BEHAVIOR_CONTRACTS[name]


def get_behaviors_for_mode(mode: Mode) -> tuple[BehaviorContract, ...]:
    """Get all behaviors applicable to a mode."""
    names = MODE_BEHAVIOR_MAP[mode]
    return tuple(BEHAVIOR_CONTRACTS[name] for name in names)


def get_all_behaviors() -> tuple[BehaviorContract, ...]:
    """Get all defined behaviors."""
    return tuple(BEHAVIOR_CONTRACTS.values())


def get_behavior_names() -> tuple[str, ...]:
    """Get all behavior names."""
    return tuple(sorted(BEHAVIOR_CONTRACTS.keys()))


def validate_mode_behavior(mode: Mode, behavior_name: str) -> bool:
    """Check if a behavior is allowed in a mode."""
    return behavior_name in MODE_BEHAVIOR_MAP[mode]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# INTENT â†’ BEHAVIOR MAPPING (Public Contract)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

INTENT_BEHAVIOR_MAP: dict[str, tuple[str, ...]] = {
    # Audit intents
    "inspect_workspace": (
        "require_current_workspace_evidence",
        "evidence_boundary_enforcement",
        "use_only_approved_guards",
    ),
    "verify_compliance": (
        "require_current_workspace_evidence",
        "validation_before_acceptance",
        "use_only_approved_guards",
    ),
    "audit_workspace": (
        "require_current_workspace_evidence",
        "evidence_boundary_enforcement",
        "audit_mode_constraints",
        "finding_review_required",
        "use_only_approved_guards",
    ),
    "check_finding": (
        "finding_review_required",
        "require_current_workspace_evidence",
        "validation_before_acceptance",
    ),
    "review_memory": (
        "memory_is_historical_context",
        "require_current_workspace_evidence",
    ),

    # Development intents
    "fix_issue": (
        "development_mode_capabilities",
        "require_current_workspace_evidence",
        "validation_before_acceptance",
        "proposed_rules_require_validation",
    ),
    "propose_rule": (
        "proposed_rules_require_validation",
        "development_mode_capabilities",
        "validation_before_acceptance",
    ),
    "discover_patterns": (
        "development_mode_capabilities",
        "require_current_workspace_evidence",
        "evidence_boundary_enforcement",
    ),
    "test_candidate": (
        "development_mode_capabilities",
        "validation_before_acceptance",
        "require_current_workspace_evidence",
    ),
}


def get_behaviors_for_intent(intent: str) -> tuple[str, ...]:
    """Map LLM intent to allowed behaviors. Returns empty if intent unknown."""
    return INTENT_BEHAVIOR_MAP.get(intent, ())


def get_supported_intents() -> tuple[str, ...]:
    """Get all supported intent names."""
    return tuple(sorted(INTENT_BEHAVIOR_MAP.keys()))
