"""Full vertical-slice Guard Runner.

Wires the existing deterministic rule-execution infrastructure
(``audit_controller`` + ``rules/``) to the evidence-bound Guard Inspector
evaluation layer so that a single *original problem request* flows through the
Phase 2 vertical slice:

```text
user problem
        ↓
search  (agent.search_workspace)
        ↓
evidence package  (EvidenceService)
        ↓
guard selection  (audit_controller.resolve_rule)
        ↓
guard execution against the workspace  (audit_controller.run_rule)
        ↓
validation  (independent inspect_file corroboration)
        ↓
LBE decision context  (GuardInspector.evaluate)
        ↓
verdict  (PASS / FAIL / INSUFFICIENT_EVIDENCE / NOT_APPLICABLE)
```

Unlike ``POST /guard-result`` (which accepts a supplied ``rule_result``), the
runner *selects* a registered guard by ``pack_id`` + ``rule_id``, *executes*
it against the workspace, *runs validation*, and *produces the verdict* from
the original problem request.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from agent import Context, GovernanceError, inspect_file
from audit_controller import RuleResult, run_rule

from .contracts import validate_contract
from .evidence_service import EvidenceService
from .guard_inspector import GuardInspector
from .workspace_identity import (
    canonical_workspace_root,
    project_workspace_id,
)


_GUARD_EVIDENCE_REQUIREMENTS = {
    "cep.manifest_exists": {
        "path_patterns": ["CSXS/manifest.xml"],
        "extensions": [".xml"],
        "content_search": False,
    },
    "cep.host_version": {
        "path_patterns": ["CSXS/manifest.xml"],
        "extensions": [".xml"],
        "content_search": False,
    },
    "cep.menubar_extension": {
        "path_patterns": ["CSXS/manifest.xml"],
        "extensions": [".xml"],
        "content_search": False,
    },
    "cep.symlink_free": {
        "path_patterns": [],
        "extensions": [],
        "content_search": False,
    },
}

#: Stop words excluded from validation term matching (extends the search
#: backend's set with weak negation terms that would otherwise produce false
#: substring matches such as "not" inside "nothing").
_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "of", "on", "or", "return",
    "returns", "that", "the", "this", "to", "was", "were", "with",
    "after", "before", "not", "no", "nor", "but", "so", "if", "then",
})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_rule_runner(
    pack_id: str, rule_id: str, ctx: Context, params: dict[str, Any]
) -> RuleResult:
    """Default rule runner: delegate to ``audit_controller.run_rule``."""
    return run_rule(pack_id, rule_id, ctx, params)


class GuardRunner:
    """Orchestrates the full evidence-bound guard vertical slice."""

    def __init__(
        self,
        *,
        evidence_service: EvidenceService | None = None,
        inspector: GuardInspector | None = None,
        context_loader: Callable[[], Context] | None = None,
        rule_runner: Callable[[str, str, Context, dict[str, Any]], RuleResult] | None = None,
        file_inspector: Callable[[Context, str], dict[str, Any]] | None = None,
    ) -> None:
        self.evidence_service = evidence_service or EvidenceService()
        self.inspector = inspector or GuardInspector()
        self.context_loader = context_loader or Context.load
        self.rule_runner = rule_runner or _default_rule_runner
        self.file_inspector = file_inspector or inspect_file

    def run(
        self,
        *,
        problem: str,
        workspace_root: str | None = None,
        pack_id: str,
        rule_id: str,
        workspace_id: str | None = None,
        guard_id: str | None = None,
        guard_version: str | None = None,
        extensions: list[str] | None = None,
        roots: list[str] | None = None,
        max_results: int = 10,
        reason: str = "",
        retrieval_mode: str = "diagnostic",
        path_patterns: list[str] | None = None,
        content_search: bool = True,
    ) -> dict[str, Any]:
        """Run the full vertical slice and return the decision context."""
        problem = (problem or "").strip()
        if not problem:
            raise ValueError("problem must not be empty")
        if not pack_id or not rule_id:
            raise ValueError("pack_id and rule_id are required")
        if retrieval_mode not in {"diagnostic", "guard", "investigation"}:
            raise ValueError(f"invalid retrieval_mode: {retrieval_mode}")

        ctx = self.context_loader()
        resolved_root = self._resolve_root_name(ctx, workspace_root, roots)
        ev_roots = roots or ([resolved_root] if resolved_root else None)
        project_type = self._project_type_for(pack_id)

        guard_requirements = (
            _GUARD_EVIDENCE_REQUIREMENTS.get(rule_id)
            if retrieval_mode == "guard"
            else None
        )

        effective_extensions = (
            list(guard_requirements["extensions"])
            if guard_requirements is not None
            else extensions
        )
        effective_path_patterns = (
            list(guard_requirements["path_patterns"])
            if guard_requirements is not None
            else path_patterns
        )
        effective_content_search = (
            bool(guard_requirements["content_search"])
            if guard_requirements is not None
            else content_search
        )

        canonical_root: Path | None = None
        effective_workspace_id = workspace_id

        if workspace_root:
            canonical_root = canonical_workspace_root(workspace_root)
            effective_workspace_id = project_workspace_id(
                canonical_root,
                workspace_id,
            )

        task = {
            "task_id": f"task-{uuid.uuid4()}",
            "problem": problem,
            "workspace_id": effective_workspace_id,
            "workspace_root": (
                str(canonical_root)
                if canonical_root is not None
                else None
            ),
            "mode": "inspect",
            "write_allowed": False,
            "constraints": [],
            "created_at": _utc_now(),
        }
        validate_contract("task_record", task)

        package = self.evidence_service.build_evidence_package(
            task_id=task["task_id"],
            query=problem,
            workspace_id=effective_workspace_id,
            workspace_root=(
                str(canonical_root)
                if canonical_root is not None
                else None
            ),
            max_results=max_results,
            extensions=effective_extensions,
            roots=ev_roots,
            retrieval_mode=retrieval_mode,
            path_patterns=effective_path_patterns,
            content_search=effective_content_search,
        )

        # Execute the registered guard against the workspace.
        rule_result = self.rule_runner(
            pack_id,
            rule_id,
            ctx,
            {
                "roots": ev_roots or [],
                "workspace_root": (
                    str(canonical_root)
                    if canonical_root is not None
                    else None
                ),
                "workspace_id": effective_workspace_id,
                "project_type": project_type,
                "inventory": {},
            },
        )

        # Run validation: independent re-read corroborating the workspace
        # evidence against the original problem.
        validation = self._run_validation(
            ctx, problem, package["current_workspace_evidence"]
        )
        package = {**package, "validation_evidence": validation}

        guard_result = self.inspector.evaluate(
            rule_result=rule_result,
            evidence_package=package,
            guard_id=guard_id or rule_id,
            guard_version=guard_version,
            workspace_id=(
                effective_workspace_id
                or package.get("workspace_id")
            ),
            reason=reason or f"Vertical slice for {pack_id}.{rule_id}",
        )

        return {
            "task": task,
            "evidence_package": package,
            "rule_result": _rule_result_to_dict(rule_result),
            "guard_result": guard_result,
        }

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _resolve_root_name(
        ctx: Context, workspace_root: str | None, roots: list[str] | None
    ) -> str | None:
        if roots:
            return roots[0]
        if not workspace_root:
            return None
        target = Path(workspace_root).expanduser().resolve()
        for root in ctx.roots:
            try:
                target.relative_to(root.path)
                return root.name
            except ValueError:
                pass
            if root.path == target:
                return root.name
        return None

    @staticmethod
    def _project_type_for(pack_id: str) -> str:
        return pack_id.strip().lower() or "generic"

    def _run_validation(
        self,
        ctx: Context,
        query: str,
        workspace_evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Independently re-read the top workspace evidence to corroborate it.

        Produces a ``validation`` evidence item only when the live file content
        contains the original problem phrase or one of its meaningful terms.
        Missing corroboration yields no validation evidence, which keeps a
        passed rule at ``INSUFFICIENT_EVIDENCE`` rather than ``PASS``.
        """
        if not workspace_evidence:
            return []
        top = workspace_evidence[0]
        metadata = top.get("metadata") or {}
        configured_root = metadata.get("configured_root")
        relative = metadata.get("relative_path")
        if not configured_root or not relative:
            return []
        virtual = f"{configured_root}/{relative}"

        try:
            inspected = self.file_inspector(ctx, virtual) or {}
        except (GovernanceError, FileNotFoundError, OSError):
            return []

        content = inspected.get("content") or ""
        query_lower = query.lower()
        content_lower = content.lower()
        raw_terms = re.findall(r"[a-z0-9_.$/-]+", query_lower)
        meaningful = [t for t in raw_terms if len(t) > 2 and t not in _STOP_WORDS]
        phrase_match = query_lower in content_lower

        def _has(term: str) -> bool:
            pattern = r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])"
            return re.search(pattern, content_lower) is not None

        matched_terms = [term for term in meaningful if _has(term)]
        required = 2 if len(meaningful) >= 2 else 1
        corroborated = phrase_match or len(matched_terms) >= required
        if not corroborated:
            return []

        return [
            {
                "ref": f"validation:workspace_corroboration:{virtual}",
                "source_type": "validation",
                "record_id": None,
                "workspace_id": top.get("workspace_id"),
                "path": virtual,
                "hash": inspected.get("sha256"),
                "line_start": None,
                "line_end": None,
                "snippet": (content[:400] or None),
                "score": None,
                "matched_terms": matched_terms,
                "exact_phrase": phrase_match,
                "authority": 5,
                "verified": True,
                "classification": "workspace_corroboration",
                "metadata": {
                    "retrieval_source": "agent.inspect_file",
                    "read_only": True,
                    "corroborated_workspace_ref": top.get("ref"),
                },
            }
        ]


def _rule_result_to_dict(rule_result: Any) -> dict[str, Any]:
    if isinstance(rule_result, Mapping):
        return dict(rule_result)
    return {
        "rule_id": getattr(rule_result, "rule_id", ""),
        "status": getattr(rule_result, "status", ""),
        "message": getattr(rule_result, "message", ""),
        "evidence": getattr(rule_result, "evidence", {}) or {},
        "severity": getattr(rule_result, "severity", "error"),
        "required": getattr(rule_result, "required", True),
        "fast_fail": getattr(rule_result, "fast_fail", False),
    }
