"""P5 typed professional capability backends over existing runtime owners.

This module does not create a dispatcher. It contributes registered ToolSpec/
handler pairs to the existing GovernedToolOrchestrator registry. Workspace
capabilities reuse the accepted tool_orchestration owners; Git reads are fixed,
read-only subprocess projections scoped to the active workspace.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

from ..evidence_service import EvidenceService
from ..memory.context import inspect_git_state
from .tool_orchestration import (
    ToolAccessClass,
    ToolExecutionResult,
    ToolHandler,
    ToolNetworkBehavior,
    ToolRegistry,
    ToolRequest,
    ToolRiskClass,
    ToolSpec,
    build_workspace_read_handler,
    build_workspace_replace_text_handler,
    workspace_read_spec,
    workspace_replace_text_spec,
)


class ProfessionalCapabilityBackendError(RuntimeError):
    """Raised when a typed backend cannot produce truthful bounded output."""


def register_workspace_and_git_backends(
    *,
    registry: ToolRegistry,
    evidence_service: EvidenceService,
) -> tuple[ToolSpec, ...]:
    """Register the first P5 workspace/code and read-only Git backends.

    The supplied registry remains the sole dispatcher registry owner. This
    function only registers typed capabilities; it never authorizes or invokes
    them.
    """
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be ToolRegistry")
    if not isinstance(evidence_service, EvidenceService):
        raise TypeError("evidence_service must be EvidenceService")

    entries: tuple[tuple[ToolSpec, ToolHandler], ...] = (
        (workspace_read_spec(), build_workspace_read_handler(evidence_service)),
        (workspace_replace_text_spec(), build_workspace_replace_text_handler()),
        (git_status_spec(), build_git_status_handler()),
        (git_diff_spec(), build_git_diff_handler()),
        (git_log_spec(), build_git_log_handler()),
        (git_show_spec(), build_git_show_handler()),
        (git_branch_spec(), build_git_branch_handler()),
        (git_remote_spec(), build_git_remote_handler()),
        (git_worktree_list_spec(), build_git_worktree_list_handler()),
    )
    for spec, handler in entries:
        registry.register(spec, handler)
    return tuple(spec for spec, _ in entries)


def git_status_spec() -> ToolSpec:
    return _git_read_spec(
        "git.status",
        required=(),
        optional=(),
        evidence=("current branch", "current HEAD", "working tree status"),
    )


def git_diff_spec() -> ToolSpec:
    return _git_read_spec(
        "git.diff",
        required=(),
        optional=("path", "cached"),
        evidence=("bounded current Git diff",),
    )


def git_log_spec() -> ToolSpec:
    return _git_read_spec(
        "git.log",
        required=(),
        optional=("max_count",),
        evidence=("bounded commit history",),
    )


def git_show_spec() -> ToolSpec:
    return _git_read_spec(
        "git.show",
        required=("revision",),
        optional=(),
        evidence=("requested Git object",),
    )


def git_branch_spec() -> ToolSpec:
    return _git_read_spec(
        "git.branch",
        required=(),
        optional=(),
        evidence=("local branch refs",),
    )


def git_remote_spec() -> ToolSpec:
    return _git_read_spec(
        "git.remote",
        required=(),
        optional=(),
        evidence=("configured remote names and URLs",),
    )


def git_worktree_list_spec() -> ToolSpec:
    return _git_read_spec(
        "git.worktree.list",
        required=(),
        optional=(),
        evidence=("current worktree inventory",),
    )


def build_git_status_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        state = inspect_git_state(_workspace_root(request))
        output = {
            "branch": state["branch"],
            "head": state["head"],
            "status_short": list(state.get("status_short") or ()),
        }
        return ToolExecutionResult(output=output, evidence=({"source_class": "current_git_state", **output},))

    return handler


def build_git_diff_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        args = ["diff", "--no-ext-diff", "--no-color"]
        cached = request.arguments.get("cached", False)
        if not isinstance(cached, bool):
            raise ValueError("cached must be bool")
        if cached:
            args.append("--cached")
        path = request.arguments.get("path")
        if path is not None:
            clean_path = _relative_path(path)
            args.extend(("--", clean_path))
        text = _run_git(_workspace_root(request), args)
        return _text_result("git.diff", text)

    return handler


def build_git_log_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        max_count = request.arguments.get("max_count", 20)
        if not isinstance(max_count, int) or isinstance(max_count, bool) or not 1 <= max_count <= 200:
            raise ValueError("max_count must be an integer between 1 and 200")
        text = _run_git(
            _workspace_root(request),
            ["log", f"--max-count={max_count}", "--date=iso-strict", "--pretty=format:%H%x09%ad%x09%an%x09%s"],
        )
        return _text_result("git.log", text)

    return handler


def build_git_show_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        revision = _safe_revision(request.arguments["revision"])
        text = _run_git(
            _workspace_root(request),
            ["show", "--no-ext-diff", "--no-color", "--format=fuller", revision],
        )
        return _text_result("git.show", text)

    return handler


def build_git_branch_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        text = _run_git(
            _workspace_root(request),
            ["for-each-ref", "--format=%(refname:short)%09%(objectname)%09%(HEAD)", "refs/heads"],
        )
        return _text_result("git.branch", text)

    return handler


def build_git_remote_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        text = _run_git(_workspace_root(request), ["remote", "-v"])
        return _text_result("git.remote", text)

    return handler


def build_git_worktree_list_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        text = _run_git(_workspace_root(request), ["worktree", "list", "--porcelain"])
        return _text_result("git.worktree.list", text)

    return handler


def _git_read_spec(
    tool_id: str,
    *,
    required: Iterable[str],
    optional: Iterable[str],
    evidence: Iterable[str],
) -> ToolSpec:
    return ToolSpec(
        tool_id=tool_id,
        capability="inspect",
        required_arguments=tuple(required),
        optional_arguments=tuple(optional),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=("active workspace is a Git repository", "active workspace scope"),
        expected_evidence=tuple(evidence),
        failure_modes=("not a Git repository", "invalid argument", "Git command failure", "authorization failure"),
    )


def _workspace_root(request: ToolRequest) -> Path:
    root = request.context.workspace_root.resolve()
    if not root.is_dir():
        raise ProfessionalCapabilityBackendError("active workspace root does not exist")
    return root


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a non-empty string")
    candidate = Path(value.replace("\\", "/").strip())
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path must stay within the active workspace")
    return candidate.as_posix()


def _safe_revision(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("revision must be a non-empty string")
    revision = value.strip()
    if revision.startswith("-") or any(char.isspace() for char in revision):
        raise ValueError("revision must be a single Git revision token")
    return revision


def _run_git(root: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30.0,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProfessionalCapabilityBackendError("Git read exceeded timeout") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"git exited {completed.returncode}"
        raise ProfessionalCapabilityBackendError(message)
    return completed.stdout


def _text_result(tool_id: str, text: str) -> ToolExecutionResult:
    output = {"text": text, "line_count": len(text.splitlines())}
    return ToolExecutionResult(
        output=output,
        evidence=({"source_class": "current_git_read", "tool_id": tool_id, "line_count": output["line_count"]},),
    )
