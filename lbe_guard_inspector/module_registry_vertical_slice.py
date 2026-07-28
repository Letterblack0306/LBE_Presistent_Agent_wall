from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from agent import Context, GovernanceError

from .guard_runner import GuardRunner

MODULE_REGISTRY_PROBLEM = "Loaded module receipt has no matching declaration"
MODULE_REGISTRY_PACK_ID = "module_registry"
MODULE_REGISTRY_RULE_ID = "module_registry.loaded_module_registration"


class ModuleRegistryGuardRunner(GuardRunner):
    """GuardRunner specialization for the fixed registry finding contract."""

    @staticmethod
    def _rule_support_paths(rule_result: Any) -> set[str]:
        evidence = (
            rule_result.get("evidence", {})
            if isinstance(rule_result, Mapping)
            else getattr(rule_result, "evidence", {}) or {}
        )
        paths: set[str] = set()
        for finding in evidence.get("supporting_findings") or []:
            path = finding.get("path") if isinstance(finding, Mapping) else None
            if isinstance(path, str) and path:
                paths.add(path.replace("\\", "/"))
        return paths


class ModuleRegistryVerticalSlice:
    """Read-only orchestration for loaded modules missing registry declarations."""

    def __init__(
        self,
        *,
        runner: GuardRunner | None = None,
        context_loader: Callable[[], Context] | None = None,
    ) -> None:
        self.runner = runner or ModuleRegistryGuardRunner()
        self.context_loader = context_loader or Context.load

    def run(
        self,
        *,
        workspace_root: str,
        workspace_id: str | None = None,
        reason: str = MODULE_REGISTRY_PROBLEM,
        max_results: int = 10,
    ) -> dict[str, Any]:
        root, root_name = self._resolve_exact_workspace(workspace_root)
        before = self._workspace_fingerprint(root)

        decision = self.runner.run(
            problem="loaded",
            workspace_root=str(root),
            workspace_id=workspace_id or root_name,
            pack_id=MODULE_REGISTRY_PACK_ID,
            rule_id=MODULE_REGISTRY_RULE_ID,
            guard_id=MODULE_REGISTRY_RULE_ID,
            roots=[root_name],
            extensions=[".json"],
            max_results=max_results,
            reason=reason,
        )

        after = self._workspace_fingerprint(root)
        if before != after:
            raise RuntimeError("Read-only module registry inspection changed the target workspace")

        guard_result = decision["guard_result"]
        authorization = {
            "mode": "inspect",
            "write_allowed": False,
            "workspace_root": str(root),
            "configured_root": root_name,
            "guard_id": MODULE_REGISTRY_RULE_ID,
            "governance_state": guard_result["governance_state"],
            "authorized": guard_result["governance_state"] in {"READ_ONLY", "INCOMPLETE"},
        }

        explanation = self._explain(guard_result, decision["evidence_package"])
        semantic_result = {
            "workspace_root": str(root),
            "configured_root": root_name,
            "guard_id": MODULE_REGISTRY_RULE_ID,
            "verdict": guard_result["verdict"],
            "summary": guard_result["summary"],
            "findings": list(guard_result["findings"]),
            "evidence_refs": list(guard_result["evidence_refs"]),
            "validation_refs": list(guard_result["validation_refs"]),
            "governance_state": guard_result["governance_state"],
        }
        decision_fingerprint = hashlib.sha256(
            json.dumps(semantic_result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        return {
            "request": {
                "problem": MODULE_REGISTRY_PROBLEM,
                "workspace_root": str(root),
                "workspace_id": workspace_id or root_name,
                "requested_mode": "inspect",
            },
            "authorization": authorization,
            "decision": decision,
            "explanation": explanation,
            "decision_fingerprint": decision_fingerprint,
            "workspace_unchanged": True,
        }

    def _resolve_exact_workspace(self, workspace_root: str) -> tuple[Path, str]:
        if not isinstance(workspace_root, str) or not workspace_root.strip():
            raise ValueError("workspace_root must be a non-empty string")
        target = Path(workspace_root).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            raise FileNotFoundError(f"Workspace root does not exist or is not a directory: {target}")

        matches: list[str] = []
        for configured in self.context_loader().roots:
            configured_path = configured.path.expanduser().resolve()
            if target == configured_path:
                matches.append(configured.name)
        if not matches:
            raise GovernanceError(f"Workspace root is not an exact configured knowledge root: {target}")
        if len(matches) > 1:
            raise GovernanceError(
                f"Workspace root resolves ambiguously to configured roots: {sorted(matches)}"
            )
        return target, matches[0]

    @staticmethod
    def _workspace_fingerprint(root: Path) -> str:
        digest = hashlib.sha256()
        excluded = {".git", "node_modules", "dist", "build", "coverage", "__pycache__"}
        files: list[Path] = []
        for path in root.rglob("*"):
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            if any(part in excluded for part in relative.parts):
                continue
            if path.is_file() and not path.is_symlink():
                files.append(path)
        for path in sorted(files, key=lambda item: item.relative_to(root).as_posix().lower()):
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            try:
                digest.update(path.read_bytes())
            except OSError as exc:
                digest.update(f"UNREADABLE:{type(exc).__name__}:{exc}".encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    @staticmethod
    def _explain(
        guard_result: Mapping[str, Any], evidence_package: Mapping[str, Any]
    ) -> dict[str, Any]:
        allowed_refs = set(guard_result.get("evidence_refs") or []) | set(
            guard_result.get("validation_refs") or []
        )
        evidence_by_ref: dict[str, Mapping[str, Any]] = {}
        for key in ("current_workspace_evidence", "validation_evidence"):
            for item in evidence_package.get(key) or []:
                ref = item.get("ref")
                if isinstance(ref, str) and ref in allowed_refs:
                    evidence_by_ref[ref] = item

        citations = []
        for ref in sorted(allowed_refs):
            item = evidence_by_ref.get(ref)
            if item is None:
                continue
            metadata = item.get("metadata") or {}
            citations.append(
                {
                    "ref": ref,
                    "path": metadata.get("virtual_path") or item.get("path"),
                    "hash": item.get("hash"),
                    "line_start": item.get("line_start"),
                    "line_end": item.get("line_end"),
                    "snippet": item.get("snippet"),
                    "source_type": item.get("source_type"),
                }
            )

        return {
            "verdict": guard_result["verdict"],
            "summary": guard_result["summary"],
            "findings": list(guard_result.get("findings") or []),
            "citations": citations,
        }
