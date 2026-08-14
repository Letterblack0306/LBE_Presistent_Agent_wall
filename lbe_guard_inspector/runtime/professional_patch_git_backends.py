"""Remaining bounded P5 workspace/Git backends.

This module composes the already-proven workspace.replace_text mutation owner
instead of introducing a second file-writing authority. ``workspace.apply_patch``
therefore represents one exact, stale-state-checkable text patch per invocation.
``git.blame`` is a fixed read-only Git projection scoped to the active workspace.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .tool_orchestration import (
    ToolAccessClass,
    ToolExecutionResult,
    ToolHandler,
    ToolNetworkBehavior,
    ToolRegistry,
    ToolRequest,
    ToolRiskClass,
    ToolSpec,
    build_workspace_replace_text_handler,
)


class ProfessionalPatchGitBackendError(RuntimeError):
    """Raised when a bounded patch/Git backend cannot produce truthful output."""


def register_patch_and_blame_backends(*, registry: ToolRegistry) -> tuple[ToolSpec, ...]:
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be ToolRegistry")
    entries: tuple[tuple[ToolSpec, ToolHandler], ...] = (
        (workspace_apply_patch_spec(), build_workspace_apply_patch_handler()),
        (git_blame_spec(), build_git_blame_handler()),
    )
    for spec, handler in entries:
        registry.register(spec, handler)
    return tuple(spec for spec, _ in entries)


def workspace_apply_patch_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.apply_patch",
        capability="modify",
        required_arguments=("path", "old_text", "new_text"),
        optional_arguments=("expected_before_sha256",),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.MEDIUM,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=(
            "relative workspace path",
            "existing regular UTF-8 file",
            "old_text occurs exactly once",
            "optional expected before hash matches current file",
            "active coding write authority",
        ),
        expected_evidence=("before content hash", "after content hash", "one exact bounded text patch"),
        failure_modes=(
            "invalid path",
            "missing file",
            "symlink target",
            "stale before hash",
            "ambiguous replacement",
            "decode failure",
            "authorization failure",
        ),
    )


def build_workspace_apply_patch_handler() -> ToolHandler:
    replace_handler = build_workspace_replace_text_handler()

    def handler(request: ToolRequest) -> ToolExecutionResult:
        expected = request.arguments.get("expected_before_sha256")
        if expected is not None:
            if not isinstance(expected, str) or len(expected) != 64:
                raise ValueError("expected_before_sha256 must be a 64-character SHA-256 hex string")
            try:
                int(expected, 16)
            except ValueError as exc:
                raise ValueError("expected_before_sha256 must be hexadecimal") from exc
            candidate = _workspace_file(request, request.arguments["path"])
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual.lower() != expected.lower():
                raise ValueError("workspace.apply_patch stale before hash")

        delegated = ToolRequest(
            operation_id=request.operation_id,
            tool_id="workspace.replace_text",
            arguments={
                "path": request.arguments["path"],
                "old_text": request.arguments["old_text"],
                "new_text": request.arguments["new_text"],
            },
            context=request.context,
        )
        result = replace_handler(delegated)
        output = dict(result.output)
        output["patch_kind"] = "exact_text_replacement"
        evidence = tuple(
            {**dict(item), "tool_id": "workspace.apply_patch", "patch_kind": "exact_text_replacement"}
            for item in result.evidence
        )
        return ToolExecutionResult(output=output, evidence=evidence)

    return handler


def git_blame_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="git.blame",
        capability="inspect",
        required_arguments=("path",),
        optional_arguments=("revision", "start_line", "end_line"),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=("active workspace is a Git repository", "active workspace scope"),
        expected_evidence=("bounded Git blame provenance",),
        failure_modes=("invalid path", "invalid revision", "invalid line range", "Git command failure", "authorization failure"),
    )


def build_git_blame_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        root = _workspace_root(request)
        path = _relative_path(request.arguments["path"])
        revision_raw = request.arguments.get("revision")
        revision = None if revision_raw is None else _safe_revision(revision_raw)
        line_range = _line_range(
            request.arguments.get("start_line"),
            request.arguments.get("end_line"),
        )
        args = ["git", "-C", str(root), "blame", "--line-porcelain"]
        if line_range is not None:
            args.extend(("-L", f"{line_range[0]},{line_range[1]}"))
        if revision is not None:
            args.append(revision)
        args.extend(("--", path))
        completed = subprocess.run(
            args,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30.0,
        )
        if completed.returncode != 0:
            raise ProfessionalPatchGitBackendError(
                f"git.blame failed with exit code {completed.returncode}: {completed.stderr.strip()}"
            )
        text = completed.stdout
        return ToolExecutionResult(
            output={
                "path": path,
                "revision": revision,
                "start_line": None if line_range is None else line_range[0],
                "end_line": None if line_range is None else line_range[1],
                "text": text,
            },
            evidence=({
                "source_class": "current_git_blame",
                "path": path,
                "revision": revision,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            },),
        )

    return handler


def _workspace_root(request: ToolRequest) -> Path:
    root = request.context.workspace_root.resolve()
    if not root.is_dir():
        raise ProfessionalPatchGitBackendError("active workspace root does not exist")
    return root


def _workspace_file(request: ToolRequest, value: object) -> Path:
    root = _workspace_root(request)
    relative = Path(_relative_path(value))
    unresolved = root / relative
    if unresolved.is_symlink():
        raise ValueError("workspace.apply_patch does not write through symlinks")
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path must stay within the active workspace") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"target file does not exist: {relative.as_posix()}")
    return candidate


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a non-empty string")
    candidate = Path(value.replace("\\", "/").strip())
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path must stay within the active workspace")
    normalized = candidate.as_posix()
    if normalized in {"", "."}:
        raise ValueError("path must identify a workspace file")
    return normalized


def _safe_revision(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("revision must be a non-empty string")
    revision = value.strip()
    if revision.startswith("-") or any(char.isspace() for char in revision):
        raise ValueError("revision must be one bounded Git revision token")
    return revision


def _line_range(start: object, end: object) -> tuple[int, int] | None:
    if start is None and end is None:
        return None
    if not isinstance(start, int) or isinstance(start, bool):
        raise ValueError("start_line must be an integer when a line range is requested")
    if end is None:
        end = start
    if not isinstance(end, int) or isinstance(end, bool):
        raise ValueError("end_line must be an integer")
    if start < 1 or end < start:
        raise ValueError("line range must satisfy 1 <= start_line <= end_line")
    if end - start + 1 > 500:
        raise ValueError("git.blame line range may contain at most 500 lines")
    return start, end
