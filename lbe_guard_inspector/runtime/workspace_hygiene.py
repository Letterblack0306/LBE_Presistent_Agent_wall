"""Governed deletion of already-classified disposable workspace material."""
from __future__ import annotations

import hashlib
import shutil
from enum import StrEnum
from pathlib import Path

from .tool_orchestration import (
    GovernedToolOrchestrator,
    ToolAccessClass,
    ToolExecutionResult,
    ToolNetworkBehavior,
    ToolRiskClass,
    ToolSpec,
    ToolRegistry,
)


class WorkspaceHygieneClassification(StrEnum):
    GENERATED_REGENERABLE = "GENERATED_REGENERABLE"
    CACHE = "CACHE"
    TEMPORARY = "TEMPORARY"
    OS_METADATA = "OS_METADATA"
    ABANDONED_AGENT_ARTIFACT = "ABANDONED_AGENT_ARTIFACT"
    SUPERSEDED = "SUPERSEDED"
    DUPLICATE = "DUPLICATE"


_DISPOSABLE = frozenset(item.value for item in WorkspaceHygieneClassification)
_PROTECTED_TOP_LEVEL = frozenset({".git", ".lbe", ".github"})


def workspace_delete_disposable_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.delete_disposable",
        capability="cleanup_disposable",
        required_arguments=("path", "classification", "expected_state"),
        optional_arguments=("expected_sha256",),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.HIGH,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=(
            "classified disposable path",
            "active workspace identity",
            "path containment",
            "expected state or hash matches",
            "not protected authority material",
        ),
        expected_evidence=("deletion receipt", "before hash or state", "post-delete absence"),
        failure_modes=(
            "invalid classification",
            "workspace escape",
            "symlink or alternate-path escape",
            "protected path",
            "state mismatch",
            "deletion failure",
        ),
    )


def build_workspace_delete_disposable_handler():
    """Return the only deletion adapter exposed to governed orchestration."""

    def handler(request) -> ToolExecutionResult:
        arguments = request.arguments
        classification = str(arguments["classification"]).strip().upper()
        if classification not in _DISPOSABLE:
            raise ValueError("path classification is not approved for deletion")

        expected_state = str(arguments["expected_state"]).strip().lower()
        if expected_state not in {"file", "directory"}:
            raise ValueError("expected_state must be file or directory")

        raw_path = arguments["path"]
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("path must be a non-empty relative path")
        relative_text = raw_path.replace("\\", "/").strip()
        relative = Path(relative_text)
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
            raise FileNotFoundError(f"disposable path does not exist: {relative_text}")
        if expected_state == "file" and not candidate.is_file():
            raise ValueError("expected file state does not match target")
        if expected_state == "directory" and not candidate.is_dir():
            raise ValueError("expected directory state does not match target")

        expected_hash = arguments.get("expected_sha256")
        before_hash = _file_sha256(candidate) if candidate.is_file() else None
        if expected_hash is not None:
            if not isinstance(expected_hash, str) or expected_hash.strip() != (before_hash or ""):
                raise ValueError("expected SHA-256 does not match current target")

        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()
        if candidate.exists() or candidate.is_symlink():
            raise OSError("deletion completed without proving target absence")

        return ToolExecutionResult(
            output={
                "path": relative.as_posix(),
                "deleted": True,
                "classification": classification,
                "expected_state": expected_state,
            },
            evidence=(
                {
                    "ref": f"workspace:{request.context.workspace_id}:{relative.as_posix()}",
                    "source_type": "workspace",
                    "workspace_id": request.context.workspace_id,
                    "path": str(candidate),
                    "classification": classification,
                    "before_sha256": before_hash,
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


def build_workspace_hygiene_orchestrator() -> GovernedToolOrchestrator:
    """Compose the bounded cleanup capability over the existing R6E owner."""
    registry = ToolRegistry()
    registry.register(workspace_delete_disposable_spec(), build_workspace_delete_disposable_handler())
    return GovernedToolOrchestrator(registry=registry)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
