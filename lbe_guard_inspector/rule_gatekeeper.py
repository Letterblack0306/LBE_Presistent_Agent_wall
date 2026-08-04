"""Read-only, evidence-bound rule proposal and revalidation boundary."""
from __future__ import annotations

import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from agent import Context
from audit_controller import AuditError, resolve_rule

from .contracts import ContractValidationError, validate_contract
from .workspace_identity import WorkspaceIdentity, resolve_workspace_identity


STATUS_APPLICABLE = "APPLICABLE"
STATUS_PROPOSAL_READY = "PROPOSAL_READY"
STATUS_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
STATUS_APPLIED = "APPLIED"
STATUS_ACTIVATION_FAILED = "ACTIVATION_FAILED"


class RuleGatekeeper:
    """Construct read-only proposals from current registered-guard evidence."""

    def __init__(
        self,
        *,
        context: Context,
        rule_resolver: Callable[[str, str], Any] = resolve_rule,
        clock: Callable[[], datetime] | None = None,
        authorization_checker: Callable[[Mapping[str, Any], Mapping[str, Any]], bool] | None = None,
    ) -> None:
        self._context = context
        self._rule_resolver = rule_resolver
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._authorization_checker = authorization_checker

    def inspect(
        self,
        *,
        workspace_root: str | Path,
        pack_id: str,
        guard_result: Mapping[str, Any],
        evidence_package: Mapping[str, Any],
        governance_state: str,
    ) -> dict[str, Any]:
        """Report applicability and evidence gaps without issuing a verdict."""
        identity = resolve_workspace_identity(self._context, workspace_root)
        missing = self._validate_inputs(
            identity, pack_id, guard_result, evidence_package, governance_state
        )
        return {
            "mode": "inspect",
            "workspace_id": identity.workspace_id,
            "workspace_root": str(identity.target_project_root),
            "pack_id": _text(pack_id, "pack_id"),
            "guard_id": str(guard_result.get("guard_id", "")),
            "status": STATUS_APPLICABLE if not missing else STATUS_INSUFFICIENT_EVIDENCE,
            "missing_evidence": missing,
            "governance_state": governance_state,
            **_read_only_report(),
        }

    def propose_rule(
        self,
        *,
        workspace_root: str | Path,
        pack_id: str,
        guard_result: Mapping[str, Any],
        evidence_package: Mapping[str, Any],
        governance_state: str,
        target_profile_path: str | Path,
        trigger: str,
        rationale: str,
        scope: Sequence[str],
        required_action: str,
        severity: str,
        exceptions: Sequence[str],
        equivalent_rule_result: Mapping[str, Any] | str | None,
        contradiction_result: Mapping[str, Any] | str | None,
        validation_plan: Sequence[str],
        rollback_plan: Sequence[str],
        provenance: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Produce a deterministic proposal; no profile, index, or rule is written."""
        identity = resolve_workspace_identity(self._context, workspace_root)
        missing = self._validate_inputs(
            identity, pack_id, guard_result, evidence_package, governance_state
        )
        if missing:
            return self._insufficient(identity, pack_id, guard_result, missing)
        target, target_error = _profile_target(identity.target_project_root, target_profile_path)
        if target_error:
            return self._insufficient(identity, pack_id, guard_result, [target_error])
        normalized_scope = _scope(scope)
        evidence = _current_workspace_evidence(
            evidence_package, identity.workspace_id, identity.target_project_root
        )
        if not evidence:
            return self._insufficient(identity, pack_id, guard_result, [
                "No verified current-workspace evidence is bound to the target workspace."
            ])
        if equivalent_rule_result is None or contradiction_result is None:
            return self._insufficient(identity, pack_id, guard_result, [
                "Equivalent-rule and contradiction results must be explicit; provenance is not inferred."
            ])
        if not isinstance(provenance, Mapping) or not provenance:
            return self._insufficient(identity, pack_id, guard_result, [
                "Proposal provenance must be explicit and non-empty."
            ])

        rule_id = _text(guard_result.get("guard_id"), "guard_result.guard_id")
        target_relative = target.relative_to(identity.target_project_root)
        current_profile = _load_profile(target)
        proposed_rule = _proposed_rule(
            rule_id=rule_id,
            trigger=trigger,
            required_action=required_action,
            severity=severity,
            scope=normalized_scope,
            exceptions=exceptions,
        )
        computed_equivalent = _check_equivalent_rule(current_profile, proposed_rule)
        exact_diff = _profile_diff(current_profile, proposed_rule, target_relative)
        source_hashes = sorted(item["hash"] for item in evidence)
        profile_ref = _workspace_ref(identity.workspace_id, target_relative, _sha256(target))
        refs = sorted({*(item["ref"] for item in evidence), profile_ref})
        enriched_provenance = {
            **dict(provenance),
            "generator": "lbe_guard_inspector.rule_gatekeeper",
            "workspace_root": str(identity.target_project_root),
            "source_guard_id": rule_id,
            "source_guard_result_hash": _stable_hash(dict(guard_result)),
            "source_hashes": source_hashes,
            "target_profile_hash": _sha256(target),
            "target_profile_evidence_ref": profile_ref,
        }
        proposal = {
            "proposal_id": _proposal_id(
                workspace_id=identity.workspace_id,
                pack_id=pack_id,
                rule_id=rule_id,
                target_profile_path=target_relative.as_posix(),
                scope=normalized_scope,
                evidence_refs=refs,
                source_hashes=source_hashes,
            ),
            "workspace_id": identity.workspace_id,
            "rule_id": rule_id,
            "pack_id": _text(pack_id, "pack_id"),
            "target_profile_path": target_relative.as_posix(),
            "trigger": _text(trigger, "trigger"),
            "rationale": _text(rationale, "rationale"),
            "scope": normalized_scope,
            "required_action": _text(required_action, "required_action"),
            "severity": _text(severity, "severity"),
            "exceptions": _text_list(exceptions, "exceptions", allow_empty=True),
            "equivalent_rule_checked": True,
            "equivalent_rule_result": computed_equivalent,
            "contradiction_result": _json_value(contradiction_result, "contradiction_result"),
            "evidence_refs": refs,
            "source_hashes": source_hashes,
            "diff": exact_diff,
            "validation_plan": _text_list(validation_plan, "validation_plan"),
            "rollback_plan": _text_list(rollback_plan, "rollback_plan"),
            "provenance": enriched_provenance,
            "approval_required": True,
            "created_at": _timestamp(self._clock()),
        }
        validate_contract("rule_proposal", proposal)
        return {
            "mode": "propose_rule", "status": STATUS_PROPOSAL_READY,
            "workspace_id": identity.workspace_id, "proposal": proposal,
            "missing_evidence": [], **_read_only_report(),
        }

    def revalidate_proposal(
        self, *, workspace_root: str | Path, proposal: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Fail closed when workspace identity, hashes, or guard registration drift."""
        try:
            validated = validate_contract("rule_proposal", proposal)
        except ContractValidationError as exc:
            return {
                "mode": "revalidate_proposal", "status": STATUS_INSUFFICIENT_EVIDENCE,
                "proposal": None, "reasons": list(exc.errors), **_read_only_report(),
            }
        identity = resolve_workspace_identity(self._context, workspace_root)
        reasons: list[str] = []
        if validated["workspace_id"] != identity.workspace_id:
            reasons.append("Workspace identity changed after proposal generation.")
        provenance = validated.get("provenance")
        if not isinstance(provenance, Mapping):
            reasons.append("Proposal provenance is missing.")
        else:
            try:
                self._rule_resolver(str(validated.get("pack_id", "")), validated["rule_id"])
            except (AuditError, OSError, ValueError) as exc:
                reasons.append(f"Source guard is unavailable or superseded: {exc}")
            target, error = _profile_target(identity.target_project_root, validated.get("target_profile_path", ""))
            if error:
                reasons.append(error)
            elif provenance.get("target_profile_hash") != _sha256(target):
                reasons.append("Target profile content changed after proposal generation.")
            for ref in validated.get("evidence_refs", []):
                error = _validate_ref(identity, ref)
                if error:
                    reasons.append(error)
        return {
            "mode": "revalidate_proposal",
            "status": STATUS_PROPOSAL_READY if not reasons else STATUS_INSUFFICIENT_EVIDENCE,
            "workspace_id": identity.workspace_id,
            "proposal": validated if not reasons else None,
            "reasons": sorted(set(reasons)), **_read_only_report(),
        }

    def record_decision(
        self,
        *,
        workspace_root: str | Path,
        proposal: Mapping[str, Any],
        decision: str,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        """Record a schema-validated decision without persisting or applying it."""
        validate_contract("rule_proposal", proposal)
        revalidation = self.revalidate_proposal(
            workspace_root=workspace_root,
            proposal=proposal,
        )
        if revalidation.get("status") != STATUS_PROPOSAL_READY:
            raise ValueError("Proposal is not currently eligible for a governance decision.")

        normalized_decision = _text(decision, "decision").upper()
        if normalized_decision not in {"APPROVED", "REJECTED"}:
            raise ValueError("decision must be APPROVED or REJECTED.")

        normalized_actor = _text(actor, "actor")
        normalized_reason = _text(reason, "reason")
        decided_at = _timestamp(self._clock())
        decision_basis = {
            "proposal_id": proposal["proposal_id"],
            "workspace_id": proposal["workspace_id"],
            "decision": normalized_decision,
            "actor": normalized_actor,
            "reason": normalized_reason,
            "decided_at": decided_at,
        }
        record = {
            "decision_id": "rpd_" + _stable_hash(decision_basis)[:24],
            **decision_basis,
            "proposal_hash": _stable_hash(dict(proposal)),
            "proposal_status": STATUS_PROPOSAL_READY,
            "authority_owner": "LBE_GOVERNANCE",
        }
        validate_contract("rule_proposal_decision", record)
        return {
            "mode": "record_decision",
            "workspace_id": proposal["workspace_id"],
            "decision_record": record,
            "proposal_revalidation": revalidation,
            **_read_only_report(),
        }

    def apply_proposal(self, proposal: Mapping[str, Any]) -> None:
        """Application is intentionally unavailable and performs no write."""
        validate_contract("rule_proposal", proposal)
        raise PermissionError("RuleGatekeeper is read-only: proposal application is blocked.")

    def apply_approved_proposal(
        self,
        *,
        workspace_root: str | Path,
        proposal: Mapping[str, Any],
        decision_record: Mapping[str, Any],
        activation_validator: Callable[[Path, Mapping[str, Any]], bool],
    ) -> dict[str, Any]:
        """Apply one explicitly approved profile diff and validate activation.

        This is the narrow governed write boundary. It does not create rollback
        artifacts, persist provenance, or attempt repair beyond the profile diff.
        """
        validated_proposal = validate_contract("rule_proposal", proposal)
        validated_decision = validate_contract("rule_proposal_decision", decision_record)
        if validated_decision["decision"] != "APPROVED":
            raise PermissionError("Only an APPROVED governance decision may apply a proposal.")
        if validated_decision["proposal_id"] != validated_proposal["proposal_id"]:
            raise ValueError("Governance decision does not match the proposal.")
        if validated_decision["workspace_id"] != validated_proposal["workspace_id"]:
            raise ValueError("Governance decision does not match the proposal workspace.")
        if validated_decision["proposal_hash"] != _stable_hash(validated_proposal):
            raise ValueError("Governance decision does not match the proposal hash.")
        if self._authorization_checker is None:
            raise PermissionError("LBE authorization checker is required for profile application.")
        if not self._authorization_checker(validated_proposal, validated_decision):
            raise PermissionError("LBE authorization denied profile application.")

        revalidation = self.revalidate_proposal(
            workspace_root=workspace_root, proposal=validated_proposal
        )
        if revalidation.get("status") != STATUS_PROPOSAL_READY:
            raise ValueError("Proposal is stale or otherwise ineligible for application.")
        identity = resolve_workspace_identity(self._context, workspace_root)
        target, target_error = _profile_target(
            identity.target_project_root, validated_proposal["target_profile_path"]
        )
        if target_error or target is None:
            raise ValueError(target_error or "Target profile is unavailable.")
        current_profile = _load_profile(target)
        proposed_rule = _proposed_rule(
            rule_id=validated_proposal["rule_id"],
            trigger=validated_proposal["trigger"],
            required_action=validated_proposal["required_action"],
            severity=validated_proposal["severity"],
            scope=validated_proposal["scope"],
            exceptions=validated_proposal["exceptions"],
        )
        target_relative = target.relative_to(identity.target_project_root)
        if _profile_diff(current_profile, proposed_rule, target_relative) != validated_proposal["diff"]:
            raise ValueError("Current profile no longer matches the approved exact diff.")
        updated_profile = _updated_profile(current_profile, proposed_rule)
        target.write_text(
            json.dumps(updated_profile, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        activated = bool(activation_validator(target, validated_proposal))
        status = STATUS_APPLIED if activated else STATUS_ACTIVATION_FAILED
        return {
            "mode": "apply_proposal",
            "status": status,
            "workspace_id": identity.workspace_id,
            "proposal_id": validated_proposal["proposal_id"],
            "decision_id": validated_decision["decision_id"],
            "activation_validated": activated,
            "runtime_mutations_performed": True,
            "target_workspace_changed": True,
            "target_profile_changed": True,
            "rule_registry_changed": False,
            "index_changed": False,
        }

    def _validate_inputs(
        self, identity: WorkspaceIdentity, pack_id: str, guard_result: Mapping[str, Any],
        evidence_package: Mapping[str, Any], governance_state: str,
    ) -> list[str]:
        try:
            guard = validate_contract("guard_result", guard_result)
            evidence = validate_contract("evidence_package", evidence_package)
        except ContractValidationError as exc:
            return list(exc.errors)
        reasons: list[str] = []
        if guard.get("workspace_id") != identity.workspace_id:
            reasons.append("Guard result is not bound to the target workspace identity.")
        if evidence.get("workspace_id") != identity.workspace_id:
            reasons.append("Evidence package is not bound to the target workspace identity.")
        if governance_state != "READ_ONLY" or guard.get("governance_state") != "READ_ONLY":
            reasons.append("Gatekeeper requires explicit READ_ONLY governance state.")
        if not evidence.get("current_workspace_evidence"):
            reasons.append("Reference-only evidence cannot satisfy current-workspace evidence requirements.")
        try:
            self._rule_resolver(_text(pack_id, "pack_id"), _text(guard.get("guard_id"), "guard_result.guard_id"))
        except (AuditError, OSError, ValueError) as exc:
            reasons.append(f"Source guard is not registered: {exc}")
        return reasons

    @staticmethod
    def _insufficient(identity: WorkspaceIdentity, pack_id: str, guard: Mapping[str, Any], reasons: list[str]) -> dict[str, Any]:
        return {
            "mode": "propose_rule", "status": STATUS_INSUFFICIENT_EVIDENCE,
            "workspace_id": identity.workspace_id, "pack_id": str(pack_id),
            "guard_id": str(guard.get("guard_id", "")), "proposal": None,
            "missing_evidence": sorted(set(reasons)), **_read_only_report(),
        }


def _current_workspace_evidence(package: Mapping[str, Any], workspace_id: str, root: Path) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in package.get("current_workspace_evidence", []):
        if not isinstance(item, Mapping) or item.get("source_type") != "workspace" or item.get("workspace_id") != workspace_id:
            continue
        path, digest = item.get("path"), item.get("hash")
        if not isinstance(path, str) or not isinstance(digest, str) or len(digest) != 64:
            continue
        candidate = Path(path).expanduser().resolve()
        try:
            relative = candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_file() and not candidate.is_symlink() and _sha256(candidate) == digest:
            result.append({"ref": _workspace_ref(workspace_id, relative, digest), "hash": digest})
    return result


def _load_profile(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Target profile is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Target profile must contain a JSON object.")
    return value


def _proposed_rule(*, rule_id: str, trigger: str, required_action: str,
                   severity: str, scope: Sequence[str], exceptions: Sequence[str]) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "trigger": _text(trigger, "trigger"),
        "required_action": _text(required_action, "required_action"),
        "severity": _text(severity, "severity"),
        "scope": sorted(set(_text_list(scope, "scope"))),
        "exceptions": sorted(set(_text_list(exceptions, "exceptions", allow_empty=True))),
    }


def _check_equivalent_rule(profile: Mapping[str, Any], proposed: Mapping[str, Any]) -> dict[str, Any]:
    rules = profile.get("rules", {})
    if not isinstance(rules, Mapping):
        return {"status": "NONE", "matches": []}
    canonical = _canonical_rule(proposed)
    matches = sorted(
        str(rule_id) for rule_id, value in rules.items()
        if isinstance(value, Mapping) and _canonical_rule(value) == canonical
    )
    return {"status": "EQUIVALENT" if matches else "NONE", "matches": matches}


def _canonical_rule(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = ("trigger", "required_action", "severity", "scope", "exceptions")
    return {
        field: sorted(value.get(field, [])) if field in {"scope", "exceptions"} else value.get(field)
        for field in fields
    }


def _profile_diff(profile: Mapping[str, Any], proposed: Mapping[str, Any], target: Path) -> str:
    updated = _updated_profile(profile, proposed)
    before = json.dumps(profile, indent=2, sort_keys=True) + "\n"
    after = json.dumps(updated, indent=2, sort_keys=True) + "\n"
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{target.as_posix()}", tofile=f"b/{target.as_posix()}"
    )) or "No profile change: equivalent rule already exists."


def _updated_profile(profile: Mapping[str, Any], proposed: Mapping[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(profile))
    rules = updated.setdefault("rules", {})
    if not isinstance(rules, dict):
        raise ValueError("Target profile 'rules' must be a JSON object.")
    rules[str(proposed["rule_id"])] = dict(proposed)
    return updated


def _profile_target(root: Path, value: str | Path) -> tuple[Path | None, str | None]:
    if not str(value).strip():
        return None, "A concrete target profile path is required."
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, "Target profile path must be workspace-relative without traversal."
    target = root / candidate
    if target.is_symlink() or not target.is_file():
        return None, "Target profile must be an existing regular file in the workspace."
    resolved = target.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None, "Target profile path escapes the workspace."
    return resolved, None


def _scope(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in _text_list(values, "scope"):
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("scope paths must be workspace-relative without traversal")
        result.append(path.as_posix())
    return sorted(set(result))


def _validate_ref(identity: WorkspaceIdentity, ref: Any) -> str | None:
    if not isinstance(ref, str):
        return "Proposal contains a non-string evidence reference."
    prefix = f"workspace:{identity.workspace_id}:"
    if not ref.startswith(prefix):
        return f"Evidence reference is not bound to the current workspace: {ref}"
    relative, marker, digest = ref[len(prefix):].rpartition("#sha256:")
    if not marker or len(digest) != 64:
        return f"Evidence reference has no valid source hash: {ref}"
    candidate = identity.target_project_root / Path(relative)
    if candidate.is_symlink() or not candidate.is_file():
        return f"Evidence is missing, non-regular, or superseded: {relative}"
    try:
        candidate.resolve().relative_to(identity.target_project_root)
    except ValueError:
        return f"Evidence escapes the workspace: {relative}"
    if _sha256(candidate) != digest:
        return f"Evidence hash changed after proposal generation: {relative}"
    return None


def _workspace_ref(workspace_id: str, relative: Path, digest: str) -> str:
    return f"workspace:{workspace_id}:{relative.as_posix()}#sha256:{digest}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _proposal_id(**value: Any) -> str:
    return "prop-" + _stable_hash(value)[:24]


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _text_list(values: Sequence[str], name: str, *, allow_empty: bool = False) -> list[str]:
    result = [_text(value, name) for value in values]
    if not allow_empty and not result:
        raise ValueError(f"{name} must contain at least one item")
    return result


def _json_value(value: Mapping[str, Any] | str, name: str) -> Mapping[str, Any] | str:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"{name} must be a non-empty string or object")


def _read_only_report() -> dict[str, bool]:
    return {
        "runtime_mutations_performed": False,
        "target_workspace_changed": False,
        "target_profile_changed": False,
        "rule_registry_changed": False,
        "index_changed": False,
    }
