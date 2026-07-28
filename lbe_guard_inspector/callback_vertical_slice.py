from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from agent import Context, GovernanceError

from .guard_runner import GuardRunner

CALLBACK_PROBLEM = "Provided callback is not a function"
CALLBACK_PACK_ID = "cep_callback"
CALLBACK_RULE_ID = "cep.callback_contract"


class CallbackVerticalSlice:
    """Read-only orchestration for the first complete Guard Inspector case.

    The service fixes guard selection to the registered CEP callback contract,
    resolves one exact configured workspace, delegates evidence collection and
    deterministic execution to ``GuardRunner``, then emits an explicit LBE
    authorization envelope and an evidence-bound explanation.
    """

    def __init__(
        self,
        *,
        runner: GuardRunner | None = None,
        context_loader: Callable[[], Context] | None = None,
    ) -> None:
        self.runner = runner or GuardRunner()
        self.context_loader = context_loader or Context.load

    def run(
        self,
        *,
        workspace_root: str,
        workspace_id: str | None = None,
        reason: str = CALLBACK_PROBLEM,
        max_results: int = 10,
    ) -> dict[str, Any]:
        root, root_name = self._resolve_exact_workspace(workspace_root)
        before = self._workspace_fingerprint(root)

        decision = self.runner.run(
            problem=CALLBACK_PROBLEM,
            workspace_root=str(root),
            workspace_id=workspace_id or root_name,
            pack_id=CALLBACK_PACK_ID,
            rule_id=CALLBACK_RULE_ID,
            guard_id=CALLBACK_RULE_ID,
            roots=[root_name],
            extensions=[".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
            max_results=max_results,
            reason=reason,
        )

        after = self._workspace_fingerprint(root)
        if before != after:
            raise RuntimeError("Read-only callback inspection changed the target workspace")

        guard_result = decision["guard_result"]
        authorization = {
            "mode": "inspect",
            "write_allowed": False,
            "workspace_root": str(root),
            "configured_root": root_name,
            "guard_id": CALLBACK_RULE_ID,
            "governance_state": guard_result["governance_state"],
            "authorized": guard_result["governance_state"] in {"READ_ONLY", "INCOMPLETE"},
        }

        explanation = self._explain(guard_result, decision["evidence_package"])
        semantic_result = {
            "workspace_root": str(root),
            "configured_root": root_name,
            "guard_id": CALLBACK_RULE_ID,
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
                "problem": CALLBACK_PROBLEM,
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
            try:
                target.relative_to(configured_path)
                matches.append(configured.name)
            except ValueError:
                if target == configured_path:
                    matches.append(configured.name)
        if not matches:
            raise GovernanceError(f"Workspace root is outside configured knowledge roots: {target}")
        if len(matches) > 1:
            raise GovernanceError(
                f"Workspace root resolves ambiguously to configured roots: {sorted(matches)}"
            )
        return target, matches[0]

    @staticmethod
    def _workspace_fingerprint(root: Path) -> str:
        digest = hashlib.sha256()
        excluded = {".git", ".lbe", "node_modules", "dist", "build", "coverage", "__pycache__"}
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
            citations.append(
                {
                    "ref": ref,
                    "path": item.get("path"),
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
