"""P5 typed professional capability backends over existing runtime owners.

This module does not create a dispatcher. It contributes registered ToolSpec/
handler pairs to the existing GovernedToolOrchestrator registry. Accepted
workspace mutation/read owners remain reused; additional workspace inspection
backends are bounded to the active workspace. Git reads are fixed, read-only
subprocess projections scoped to that same workspace.
"""
from __future__ import annotations

import fnmatch
import hashlib
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

_MAX_SCAN_FILE_BYTES = 2_000_000
_DEFAULT_SCAN_LIMIT = 50
_MAX_SCAN_LIMIT = 200


class ProfessionalCapabilityBackendError(RuntimeError):
    """Raised when a typed backend cannot produce truthful bounded output."""


def register_workspace_and_git_backends(
    *,
    registry: ToolRegistry,
    evidence_service: EvidenceService,
) -> tuple[ToolSpec, ...]:
    """Register bounded workspace/code and read-only Git backends.

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
        (workspace_search_spec(), build_workspace_search_handler()),
        (workspace_glob_spec(), build_workspace_glob_handler()),
        (workspace_inspect_spec(), build_workspace_inspect_handler()),
        (workspace_diff_spec(), build_workspace_diff_handler()),
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


def workspace_search_spec() -> ToolSpec:
    return _workspace_read_spec(
        "workspace.search",
        required=("query",),
        optional=("path", "max_results"),
        evidence=("bounded matching current-workspace paths and snippets",),
    )


def workspace_glob_spec() -> ToolSpec:
    return _workspace_read_spec(
        "workspace.glob",
        required=("pattern",),
        optional=("max_results",),
        evidence=("bounded current-workspace path inventory",),
    )


def workspace_inspect_spec() -> ToolSpec:
    return _workspace_read_spec(
        "workspace.inspect",
        required=("path",),
        optional=(),
        evidence=("current workspace file/directory metadata",),
    )


def workspace_diff_spec() -> ToolSpec:
    return _workspace_read_spec(
        "workspace.diff",
        required=(),
        optional=("path", "cached"),
        evidence=("bounded current workspace Git diff",),
        preconditions=("active workspace is a Git repository", "active workspace scope"),
    )


def build_workspace_search_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        query = request.arguments["query"]
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        needle = query.strip().casefold()
        root = _workspace_root(request)
        scope = request.arguments.get("path")
        scan_root = root if scope is None else _workspace_candidate(root, scope)
        if not scan_root.exists():
            raise FileNotFoundError("workspace.search path does not exist")
        limit = _bounded_limit(request.arguments.get("max_results", _DEFAULT_SCAN_LIMIT))

        matches: list[dict[str, object]] = []
        for path in _iter_workspace_files(root, scan_root):
            try:
                if path.stat().st_size > _MAX_SCAN_FILE_BYTES:
                    continue
                raw = path.read_bytes()
                text = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            relative = path.relative_to(root).as_posix()
            path_match = needle in relative.casefold()
            for line_number, line in enumerate(text.splitlines(), start=1):
                if needle in line.casefold() or path_match:
                    matches.append({
                        "path": relative,
                        "line": line_number if line else None,
                        "snippet": line[:400],
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    })
                    break
            if path_match and not text.splitlines():
                matches.append({
                    "path": relative,
                    "line": None,
                    "snippet": "",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                })
            if len(matches) >= limit:
                break

        output = {"query": query.strip(), "matches": matches, "match_count": len(matches)}
        return ToolExecutionResult(
            output=output,
            evidence=({"source_class": "current_workspace_search", "match_count": len(matches)},),
        )

    return handler


def build_workspace_glob_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        pattern = request.arguments["pattern"]
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError("pattern must be a non-empty string")
        normalized = pattern.replace("\\", "/").strip()
        if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
            raise ValueError("pattern must stay within the active workspace")
        limit = _bounded_limit(request.arguments.get("max_results", _DEFAULT_SCAN_LIMIT))
        root = _workspace_root(request)
        paths: list[str] = []
        for candidate in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if candidate.is_symlink():
                continue
            relative = candidate.relative_to(root).as_posix()
            if relative == ".git" or relative.startswith(".git/"):
                continue
            if fnmatch.fnmatchcase(relative, normalized):
                paths.append(relative)
                if len(paths) >= limit:
                    break
        output = {"pattern": normalized, "paths": paths, "match_count": len(paths)}
        return ToolExecutionResult(
            output=output,
            evidence=({"source_class": "current_workspace_glob", "match_count": len(paths)},),
        )

    return handler


def build_workspace_inspect_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        root = _workspace_root(request)
        candidate = _workspace_candidate(root, request.arguments["path"])
        if candidate.is_symlink():
            raise ValueError("workspace.inspect does not follow symlinks")
        if not candidate.exists():
            raise FileNotFoundError("workspace.inspect path does not exist")
        relative = candidate.relative_to(root).as_posix()
        stat = candidate.stat()
        output: dict[str, object] = {
            "path": relative,
            "kind": "directory" if candidate.is_dir() else "file",
            "size": int(stat.st_size),
            "modified_ns": int(stat.st_mtime_ns),
        }
        if candidate.is_file():
            raw = candidate.read_bytes()
            output["sha256"] = hashlib.sha256(raw).hexdigest()
            try:
                output["line_count"] = len(raw.decode("utf-8").splitlines())
                output["utf8_text"] = True
            except UnicodeDecodeError:
                output["line_count"] = None
                output["utf8_text"] = False
        else:
            output["entry_count"] = sum(1 for _ in candidate.iterdir())
        return ToolExecutionResult(
            output=output,
            evidence=({"source_class": "current_workspace_inspect", "path": relative, "kind": output["kind"]},),
        )

    return handler


def build_workspace_diff_handler() -> ToolHandler:
    git_handler = build_git_diff_handler()

    def handler(request: ToolRequest) -> ToolExecutionResult:
        result = git_handler(request)
        evidence = tuple(
            {**dict(item), "tool_id": "workspace.diff"}
            for item in result.evidence
        )
        return ToolExecutionResult(output=dict(result.output), evidence=evidence)

    return handler


def git_status_spec() -> ToolSpec:
    return _git_read_spec("git.status", required=(), optional=(), evidence=("current branch", "current HEAD", "working tree status"))


def git_diff_spec() -> ToolSpec:
    return _git_read_spec("git.diff", required=(), optional=("path", "cached"), evidence=("bounded current Git diff",))


def git_log_spec() -> ToolSpec:
    return _git_read_spec("git.log", required=(), optional=("max_count",), evidence=("bounded commit history",))


def git_show_spec() -> ToolSpec:
    return _git_read_spec("git.show", required=("revision",), optional=(), evidence=("requested Git object",))


def git_branch_spec() -> ToolSpec:
    return _git_read_spec("git.branch", required=(), optional=(), evidence=("local branch refs",))


def git_remote_spec() -> ToolSpec:
    return _git_read_spec("git.remote", required=(), optional=(), evidence=("configured remote names and URLs",))


def git_worktree_list_spec() -> ToolSpec:
    return _git_read_spec("git.worktree.list", required=(), optional=(), evidence=("current worktree inventory",))


def build_git_status_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        state = inspect_git_state(_workspace_root(request))
        output = {"branch": state["branch"], "head": state["head"], "status_short": list(state.get("status_short") or ())}
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
            args.extend(("--", _relative_path(path)))
        return _text_result("git.diff", _run_git(_workspace_root(request), args))
    return handler


def build_git_log_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        max_count = request.arguments.get("max_count", 20)
        if not isinstance(max_count, int) or isinstance(max_count, bool) or not 1 <= max_count <= 200:
            raise ValueError("max_count must be an integer between 1 and 200")
        text = _run_git(_workspace_root(request), ["log", f"--max-count={max_count}", "--date=iso-strict", "--pretty=format:%H%x09%ad%x09%an%x09%s"])
        return _text_result("git.log", text)
    return handler


def build_git_show_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        revision = _safe_revision(request.arguments["revision"])
        return _text_result("git.show", _run_git(_workspace_root(request), ["show", "--no-ext-diff", "--no-color", "--format=fuller", revision]))
    return handler


def build_git_branch_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        return _text_result("git.branch", _run_git(_workspace_root(request), ["for-each-ref", "--format=%(refname:short)%09%(objectname)%09%(HEAD)", "refs/heads"]))
    return handler


def build_git_remote_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        return _text_result("git.remote", _run_git(_workspace_root(request), ["remote", "-v"]))
    return handler


def build_git_worktree_list_handler() -> ToolHandler:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        return _text_result("git.worktree.list", _run_git(_workspace_root(request), ["worktree", "list", "--porcelain"]))
    return handler


def _workspace_read_spec(
    tool_id: str,
    *,
    required: Iterable[str],
    optional: Iterable[str],
    evidence: Iterable[str],
    preconditions: Iterable[str] = ("active workspace scope",),
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
        preconditions=tuple(preconditions),
        expected_evidence=tuple(evidence),
        failure_modes=("invalid argument", "workspace scope failure", "read failure", "authorization failure"),
    )


def _git_read_spec(tool_id: str, *, required: Iterable[str], optional: Iterable[str], evidence: Iterable[str]) -> ToolSpec:
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


def _workspace_candidate(root: Path, value: object) -> Path:
    relative = Path(_relative_path(value))
    unresolved = root / relative
    if unresolved.is_symlink():
        return unresolved
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path must stay within the active workspace") from exc
    return candidate


def _iter_workspace_files(root: Path, scan_root: Path):
    candidates = (scan_root,) if scan_root.is_file() else scan_root.rglob("*")
    for path in sorted(candidates, key=lambda item: item.as_posix().casefold()):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(root)
        except ValueError:
            continue
        normalized = relative.as_posix()
        if normalized == ".git" or normalized.startswith(".git/"):
            continue
        yield path


def _bounded_limit(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= _MAX_SCAN_LIMIT:
        raise ValueError(f"max_results must be an integer between 1 and {_MAX_SCAN_LIMIT}")
    return value


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
        completed = subprocess.run(["git", "-C", str(root), *args], check=False, capture_output=True, text=True, encoding="utf-8", timeout=30.0)
    except subprocess.TimeoutExpired as exc:
        raise ProfessionalCapabilityBackendError("Git read exceeded timeout") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"git exited {completed.returncode}"
        raise ProfessionalCapabilityBackendError(message)
    return completed.stdout


def _text_result(tool_id: str, text: str) -> ToolExecutionResult:
    output = {"text": text, "line_count": len(text.splitlines())}
    return ToolExecutionResult(output=output, evidence=({"source_class": "current_git_read", "tool_id": tool_id, "line_count": output["line_count"]},))
