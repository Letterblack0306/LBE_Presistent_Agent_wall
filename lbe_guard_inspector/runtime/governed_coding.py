"""Provider-neutral governed coding over existing LBE authorities.

Providers receive only LBE-generated tool definitions. LBE alone authorizes,
executes, and records receipts. Session/task persistence and completion truth
remain with their existing owners.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import difflib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Mapping
from uuid import uuid4

from agent import Context, GovernanceError, matches_any, path_allowed

from ..evidence_service import EvidenceService
from ..openai_compatible_event_adapter import OpenAICompatibleEventAdapter
from ..professional_provider_events import ModelEventType, NormalizedModelEvent
from ..reasoning_contracts import LBERequest, LBEResponse, OrchestrationError
from ..reasoning_provider import ProviderConfig
from ..session_memory_runtime import SessionMemoryRuntimeBridge
from .mode_controller import ModeRequest, resolve_mode
from .agent_guidance import AgentGuidance, build_agent_guidance
from .tool_orchestration import (
    GovernedToolOrchestrator,
    ToolAccessClass,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolNetworkBehavior,
    ToolReceipt,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRiskClass,
    ToolRequest,
    ToolSpec,
    build_workspace_read_handler,
    workspace_read_spec,
)

_MAX_CREATE_BYTES = 1_000_000
_MAX_WRITE_BYTES = 1_000_000
_MAX_PROCESS_OUTPUT = 128_000
_MAX_GIT_PATHS = 64

_REGISTERED_PROCESS_COMMANDS: dict[str, tuple[str, ...]] = {
    "python.version": (sys.executable, "--version"),
    "repository.git_diff_check": ("git", "diff", "--check"),
    "repository.git_status": ("git", "status", "--short", "--branch"),
}


def _resolve_workspace_policy(root: Path, relative_to_root: str) -> tuple[Context, object]:
    ctx = Context.load()
    configured_root = next((item for item in ctx.roots if item.path.resolve() == root), None)
    if configured_root is None:
        raise GovernanceError("active workspace is not a configured knowledge root")

    governance = ctx.governance
    forbidden = list(governance.get("forbidden_globs", []))
    virtual = f"{configured_root.name}/{relative_to_root}"
    if matches_any(virtual, forbidden) or matches_any(relative_to_root, forbidden):
        raise GovernanceError(f"write path is explicitly forbidden: {relative_to_root}")

    allowed_write_paths = list(governance.get("allowed_write_paths", []))
    if not path_allowed(relative_to_root, allowed_write_paths):
        raise GovernanceError(f"write path is not allowed: {relative_to_root}")

    _enforce_ui_implementation_authority(governance, relative_to_root, None)
    return ctx, configured_root


_UI_CONFLICT_MESSAGE = "UI technology conflict"


def _enforce_ui_implementation_authority(
    governance: Mapping[str, object], relative_to_root: str, content: str | None
) -> None:
    """Machine-enforced UI_IMPLEMENTATION_AUTHORITY at the pre-write boundary.

    Agents never choose the UI technology. Product UI is HTML/CSS/JavaScript
    only; Python TUI authorities remain legacy/reference-only and are never
    mutated. Section absent: inactive here because this runtime also serves
    installed workspaces; the canonical repository machine gate
    (scripts/check-implementation-gate.py) fail-closes when it is missing.
    Malformed or disabled section: denied (fail closed).
    """
    section = governance.get("ui_implementation_authority")
    if section is None:
        return
    if (
        not isinstance(section, dict)
        or section.get("enabled") is not True
        or section.get("fail_closed") is not True
    ):
        raise GovernanceError(
            f"{_UI_CONFLICT_MESSAGE}: invalid ui_implementation_authority state (fail closed)"
        )
    denied = str(section.get("denied_message") or _UI_CONFLICT_MESSAGE)
    normalized = relative_to_root.replace("\\", "/").lower()

    if normalized in tuple(
        str(p).replace("\\", "/").strip().lower()
        for p in section.get("legacy_reference_only_paths", [])
    ):
        raise GovernanceError(
            f"{denied}: legacy/reference-only Python TUI path may not be mutated: "
            f"{relative_to_root}"
        )

    prefixes = tuple(
        str(p).replace("\\", "/").strip().lower().rstrip("*")
        for p in section.get("product_ui_prefixes", [])
    )
    if not any(normalized.startswith(prefix) for prefix in prefixes):
        return
    if normalized.endswith(".py"):
        raise GovernanceError(
            f"{denied}: Python is not an authorized product-UI technology: {relative_to_root}"
        )
    if content is None:
        return
    lowered = content.lower()
    for token in (
        str(t).strip().lower() for t in section.get("forbidden_ui_framework_tokens", [])
    ):
        if token and re.search(rf"\b{re.escape(token)}\b", lowered):
            raise GovernanceError(
                f"{denied}: forbidden UI framework token '{token}' introduced: "
                f"{relative_to_root}"
            )


def _bounded_workspace_path(request: ToolRequest, raw_path: object) -> tuple[Path, str]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("path must be a non-empty string")
    relative = Path(raw_path.replace("\\", "/").strip())
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("path must stay within the active workspace")
    root = Path(request.context.workspace_root).resolve()
    candidate = (root / relative).resolve()
    try:
        relative_to_root = candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("path escapes the active workspace") from exc
    return candidate, relative_to_root


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_create_candidate_text_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="workspace.create_candidate_text",
        capability="test_candidate",
        required_arguments=("path", "content"),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.MEDIUM,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=(
            "relative workspace path",
            "target does not already exist",
            "parent directory already exists",
            "active governance allows the write path",
            "active governance allows at least one changed file and the patch size",
        ),
        expected_evidence=("created workspace file", "sha256"),
        failure_modes=(
            "invalid path",
            "forbidden path",
            "write path not allowed",
            "target already exists",
            "patch limit exceeded",
            "write failure",
            "authorization failure",
        ),
    )


def build_workspace_create_candidate_text_handler() -> object:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        candidate, relative_to_root = _bounded_workspace_path(request, request.arguments["path"])
        content = request.arguments["content"]
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        root = Path(request.context.workspace_root).resolve()
        ctx, _configured_root = _resolve_workspace_policy(root, relative_to_root)
        governance = ctx.governance
        _enforce_ui_implementation_authority(governance, relative_to_root, content)

        raw = content.encode("utf-8")
        if len(raw) > _MAX_CREATE_BYTES:
            raise ValueError(f"content exceeds bounded create limit of {_MAX_CREATE_BYTES} bytes")
        if int(governance.get("max_changed_files", 0)) < 1:
            raise GovernanceError("active governance allows zero changed files")
        max_patch_bytes = int(governance.get("max_patch_bytes", 0))
        if max_patch_bytes < len(raw):
            raise GovernanceError(f"content exceeds active max_patch_bytes ({max_patch_bytes})")
        if not candidate.parent.is_dir():
            raise FileNotFoundError(f"parent directory does not exist: {candidate.parent}")
        if candidate.exists():
            raise FileExistsError(f"create-only target already exists: {relative_to_root}")

        with candidate.open("xb") as handle:
            handle.write(raw)
            handle.flush()
        digest = _sha256_bytes(raw)
        return ToolExecutionResult(
            output={"path": relative_to_root, "created": True, "bytes": len(raw), "sha256": digest},
            evidence=({
                "ref": f"workspace:{request.context.workspace_id}:{relative_to_root}",
                "source_type": "workspace",
                "workspace_id": request.context.workspace_id,
                "path": str(candidate),
                "hash": digest,
                "verified": True,
                "classification": "current_workspace_mutation",
                "metadata": {"relative_path": relative_to_root, "operation_id": request.operation_id, "tool_id": request.tool_id},
            },),
        )

    return handler


def workspace_write_text_spec() -> ToolSpec:
    """Bounded create/update with optimistic concurrency for existing files."""
    return ToolSpec(
        tool_id="workspace.write_text",
        capability="modify",
        required_arguments=("path", "content"),
        optional_arguments=("expected_sha256",),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.MEDIUM,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=(
            "relative workspace path",
            "active governance allows the write path",
            "parent directory already exists",
            "existing files require exact expected_sha256",
            "symlink targets are denied",
            "patch size remains bounded",
        ),
        expected_evidence=("before hash or missing state", "after sha256", "atomic replace"),
        failure_modes=("workspace escape", "forbidden path", "stale write", "symlink target", "patch limit", "write failure"),
    )


def build_workspace_write_text_handler() -> object:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        candidate, relative_to_root = _bounded_workspace_path(request, request.arguments["path"])
        content = request.arguments["content"]
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        root = Path(request.context.workspace_root).resolve()
        ctx, _configured_root = _resolve_workspace_policy(root, relative_to_root)
        governance = ctx.governance
        _enforce_ui_implementation_authority(governance, relative_to_root, content)

        raw = content.encode("utf-8")
        if len(raw) > _MAX_WRITE_BYTES:
            raise ValueError(f"content exceeds bounded write limit of {_MAX_WRITE_BYTES} bytes")
        if int(governance.get("max_changed_files", 0)) < 1:
            raise GovernanceError("active governance allows zero changed files")
        max_patch_bytes = int(governance.get("max_patch_bytes", 0))
        if max_patch_bytes < len(raw):
            raise GovernanceError(f"content exceeds active max_patch_bytes ({max_patch_bytes})")
        if not candidate.parent.is_dir():
            raise FileNotFoundError(f"parent directory does not exist: {candidate.parent}")
        if candidate.is_symlink():
            raise PermissionError("symlink targets cannot be written")
        if candidate.exists() and not candidate.is_file():
            raise ValueError("workspace.write_text target must be a regular file")

        before_exists = candidate.exists()
        before_sha256 = _sha256_file(candidate) if before_exists else None
        expected = request.arguments.get("expected_sha256")
        expected_text = str(expected).strip().lower() if expected is not None else ""
        if before_exists:
            if not expected_text:
                raise GovernanceError("expected_sha256 is required when updating an existing file")
            if expected_text != before_sha256:
                raise ValueError("expected_sha256 does not match current file; stale overwrite denied")
        elif expected_text:
            raise ValueError("expected_sha256 must be omitted when creating a new file")

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(candidate.parent),
                prefix=".lbe-write-",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            if before_exists:
                try:
                    os.chmod(temp_path, candidate.stat().st_mode)
                except OSError:
                    pass
            os.replace(temp_path, candidate)
            temp_path = None
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

        after_sha256 = _sha256_bytes(raw)
        return ToolExecutionResult(
            output={
                "path": relative_to_root,
                "created": not before_exists,
                "updated": before_exists,
                "bytes": len(raw),
                "before_sha256": before_sha256,
                "sha256": after_sha256,
            },
            evidence=({
                "ref": f"workspace:{request.context.workspace_id}:{relative_to_root}",
                "source_type": "workspace",
                "workspace_id": request.context.workspace_id,
                "path": str(candidate),
                "before_sha256": before_sha256,
                "after_sha256": after_sha256,
                "verified": candidate.is_file() and _sha256_file(candidate) == after_sha256,
                "classification": "current_workspace_mutation",
                "metadata": {"relative_path": relative_to_root, "operation_id": request.operation_id, "tool_id": request.tool_id},
            },),
        )

    return handler


def workspace_patch_spec() -> ToolSpec:
    """Bounded single-file replacement patch with optimistic concurrency."""
    return ToolSpec(
        tool_id="workspace.patch",
        capability="modify",
        required_arguments=("path", "content", "expected_sha256"),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.MEDIUM,
        timeout_seconds=30.0,
        retry_policy="none",
        preconditions=(
            "relative workspace path",
            "active governance allows the write path",
            "existing target has an exact expected_sha256",
            "patch is one bounded UTF-8 file replacement",
        ),
        expected_evidence=("before hash", "after hash", "unified diff", "atomic replace"),
        failure_modes=("workspace escape", "forbidden path", "stale write", "patch limit", "write failure"),
    )


def build_workspace_patch_handler() -> object:
    write_handler = build_workspace_write_text_handler()

    def handler(request: ToolRequest) -> ToolExecutionResult:
        path = request.arguments["path"]
        content = request.arguments["content"]
        expected = request.arguments["expected_sha256"]
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path must be a non-empty relative path")
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError("expected_sha256 is required for workspace.patch")

        target, relative_to_root = _bounded_workspace_path(request, path)
        if not target.exists() or not target.is_file() or target.is_symlink():
            raise ValueError("workspace.patch target must be an existing regular file")
        before = target.read_text(encoding="utf-8")
        diff = "".join(difflib.unified_diff(
            before.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=relative_to_root,
            tofile=relative_to_root,
        ))
        result = write_handler(ToolRequest(
            operation_id=request.operation_id,
            tool_id="workspace.write_text",
            arguments={"path": path, "content": content, "expected_sha256": expected},
            context=request.context,
        ))
        output = dict(result.output)
        output["patch"] = diff
        evidence = tuple(dict(item) for item in result.evidence)
        if evidence:
            evidence[0]["patch"] = diff
            evidence[0]["metadata"]["tool_id"] = request.tool_id
        return ToolExecutionResult(output=output, evidence=evidence)

    return handler


def process_run_registered_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="process.run_registered",
        capability="inspect",
        required_arguments=("command_id",),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=300.0,
        retry_policy="none",
        preconditions=("command id exists in LBE-owned catalog", "shell=false", "cwd is canonical workspace"),
        expected_evidence=("argv", "exit code", "bounded stdout/stderr"),
        failure_modes=("unregistered command", "process timeout", "process spawn failure"),
    )


def build_process_run_registered_handler() -> object:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        command_id = str(request.arguments["command_id"]).strip()
        argv = _REGISTERED_PROCESS_COMMANDS.get(command_id)
        if argv is None:
            raise GovernanceError(f"process command is not registered: {command_id}")
        executable = argv[0]
        if executable == "git" and shutil.which("git") is None:
            raise FileNotFoundError("git executable is unavailable")
        completed = subprocess.run(
            list(argv),
            cwd=Path(request.context.workspace_root).resolve(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
            shell=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        stdout = completed.stdout[-_MAX_PROCESS_OUTPUT:]
        stderr = completed.stderr[-_MAX_PROCESS_OUTPUT:]
        return ToolExecutionResult(
            output={"command_id": command_id, "argv": list(argv), "exit_code": completed.returncode, "stdout": stdout, "stderr": stderr},
            evidence=({
                "ref": f"process:{request.operation_id}",
                "source_type": "runtime",
                "verified": True,
                "command_id": command_id,
                "argv": list(argv),
                "exit_code": completed.returncode,
                "metadata": {"operation_id": request.operation_id, "tool_id": request.tool_id, "shell": False},
            },),
        )

    return handler


def git_status_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="git.status",
        capability="inspect",
        required_arguments=(),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        expected_evidence=("primary repository root", "branch", "porcelain status"),
        failure_modes=("git unavailable", "not primary repository", "not main branch"),
    )


def git_stage_paths_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="git.stage_paths",
        capability="modify",
        required_arguments=("paths_json",),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.MEDIUM,
        preconditions=("primary .git directory", "branch main", "paths were mutated by governed LBE tools in current turn"),
        expected_evidence=("staged paths", "branch main"),
        failure_modes=("worktree/branch mismatch", "path not governed this turn", "git add failure"),
    )


def git_commit_staged_spec() -> ToolSpec:
    return ToolSpec(
        tool_id="git.commit_staged",
        capability="modify",
        required_arguments=("message",),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.HIGH,
        preconditions=("primary .git directory", "branch main", "all staged paths were governed mutations in current turn", "hooks disabled for deterministic execution"),
        expected_evidence=("commit sha", "staged path set"),
        failure_modes=("worktree/branch mismatch", "foreign staged path", "empty staged set", "commit failure"),
    )


def _run_git(root: Path, *args: str, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    if shutil.which("git") is None:
        raise FileNotFoundError("git executable is unavailable")
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )


def _require_primary_main_git(root: Path) -> None:
    if not (root / ".git").is_dir():
        raise GovernanceError("Git mutation requires the primary repository workspace; linked worktrees are denied")
    top = _run_git(root, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root:
        raise GovernanceError("active workspace is not the primary Git repository root")
    branch = _run_git(root, "branch", "--show-current")
    if branch.returncode != 0 or branch.stdout.strip() != "main":
        raise GovernanceError("Git mutation is allowed only on canonical main")


def build_git_status_handler() -> object:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        root = Path(request.context.workspace_root).resolve()
        _require_primary_main_git(root)
        status = _run_git(root, "status", "--short", "--branch")
        if status.returncode != 0:
            raise RuntimeError(status.stderr.strip() or "git status failed")
        return ToolExecutionResult(
            output={"branch": "main", "status": status.stdout},
            evidence=({"ref": f"git:{request.operation_id}:status", "source_type": "runtime", "verified": True, "branch": "main", "status": status.stdout, "metadata": {"operation_id": request.operation_id, "tool_id": request.tool_id}},),
        )
    return handler


def _parse_paths_json(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, str):
        raise ValueError("paths_json must be a JSON string array")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("paths_json must be valid JSON") from exc
    if not isinstance(value, list) or not value or len(value) > _MAX_GIT_PATHS:
        raise ValueError(f"paths_json must contain between 1 and {_MAX_GIT_PATHS} paths")
    paths: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("git paths must be non-empty strings")
        relative = Path(item.replace("\\", "/").strip())
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError("git paths must stay within the active workspace")
        paths.append(relative.as_posix())
    if len(set(paths)) != len(paths):
        raise ValueError("git paths must be unique")
    return tuple(paths)


def build_git_stage_paths_handler(allowed_paths: Callable[[], frozenset[str]]) -> object:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        root = Path(request.context.workspace_root).resolve()
        _require_primary_main_git(root)
        paths = _parse_paths_json(request.arguments["paths_json"])
        permitted = allowed_paths()
        unexpected = tuple(path for path in paths if path not in permitted)
        if unexpected:
            raise GovernanceError("git staging is limited to paths mutated by governed LBE tools in this turn: " + ", ".join(unexpected))
        result = _run_git(root, "add", "--", *paths)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "git add failed")
        staged = _run_git(root, "diff", "--cached", "--name-only", "--", *paths)
        if staged.returncode != 0:
            raise RuntimeError(staged.stderr.strip() or "git staged-path inspection failed")
        staged_paths = tuple(line.strip().replace("\\", "/") for line in staged.stdout.splitlines() if line.strip())
        return ToolExecutionResult(
            output={"branch": "main", "staged_paths": list(staged_paths)},
            evidence=({"ref": f"git:{request.operation_id}:stage", "source_type": "runtime", "verified": set(staged_paths).issubset(permitted), "branch": "main", "staged_paths": list(staged_paths), "metadata": {"operation_id": request.operation_id, "tool_id": request.tool_id}},),
        )
    return handler


def _run_implementation_gate(root: Path) -> tuple[bool, str]:
    """Every sanctioned LBE runtime commit must pass the canonical machine gate.

    Canonical repository workspaces carry scripts/check-implementation-gate.py
    (wired into .githooks/pre-commit for interactive commits); the governed
    commit tool enforces the same verdict here instead of silently neutering
    hooks. Installed runtime workspaces carry no gate file and are documented
    limitations, not escape hatches.
    """
    gate = root / "scripts" / "check-implementation-gate.py"
    if not gate.is_file():
        return True, "gate absent from workspace"
    result = subprocess.run(
        [sys.executable, str(gate)],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120.0,
        check=False,
    )
    detail = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
    return result.returncode == 0, detail


def build_git_commit_staged_handler(allowed_paths: Callable[[], frozenset[str]]) -> object:
    def handler(request: ToolRequest) -> ToolExecutionResult:
        root = Path(request.context.workspace_root).resolve()
        _require_primary_main_git(root)
        message = str(request.arguments["message"]).strip()
        if not message or len(message) > 200 or "\n" in message or "\r" in message:
            raise ValueError("commit message must be one non-empty line of at most 200 characters")
        staged = _run_git(root, "diff", "--cached", "--name-only")
        if staged.returncode != 0:
            raise RuntimeError(staged.stderr.strip() or "git staged-path inspection failed")
        staged_paths = tuple(line.strip().replace("\\", "/") for line in staged.stdout.splitlines() if line.strip())
        if not staged_paths:
            raise GovernanceError("no staged changes are available for commit")
        permitted = allowed_paths()
        foreign = tuple(path for path in staged_paths if path not in permitted)
        if foreign:
            raise GovernanceError("refusing to commit paths not mutated by governed LBE tools in this turn: " + ", ".join(foreign))
        gate_ok, gate_detail = _run_implementation_gate(root)
        if not gate_ok:
            raise GovernanceError(f"implementation gate blocked commit: {gate_detail}")
        with tempfile.TemporaryDirectory(prefix="lbe-empty-git-hooks-") as hooks_dir:
            commit = _run_git(root, "-c", f"core.hooksPath={hooks_dir}", "commit", "-m", message, timeout=120.0)
        if commit.returncode != 0:
            raise RuntimeError(commit.stderr.strip() or commit.stdout.strip() or "git commit failed")
        head = _run_git(root, "rev-parse", "HEAD")
        if head.returncode != 0:
            raise RuntimeError(head.stderr.strip() or "cannot resolve committed HEAD")
        sha = head.stdout.strip()
        return ToolExecutionResult(
            output={"branch": "main", "commit": sha, "committed_paths": list(staged_paths)},
            evidence=({"ref": f"git:{request.operation_id}:commit:{sha}", "source_type": "runtime", "verified": True, "branch": "main", "commit": sha, "committed_paths": list(staged_paths), "metadata": {"operation_id": request.operation_id, "tool_id": request.tool_id, "hooks_neutered": True, "implementation_gate": "PASS" if gate_ok else "ABSENT"}},),
        )
    return handler


class _ReceiptTrackingOrchestrator(GovernedToolOrchestrator):
    def __init__(self, *, registry: ToolRegistry) -> None:
        super().__init__(registry=registry)
        self._observed_receipts: list[ToolReceipt] = []
        self._observed_receipt_ids: set[str] = set()

    @property
    def observed_receipts(self) -> tuple[ToolReceipt, ...]:
        return tuple(self._observed_receipts)

    def invoke(self, request: ToolRequest) -> ToolReceipt:
        receipt = super().invoke(request)
        if receipt.receipt_id not in self._observed_receipt_ids:
            self._observed_receipt_ids.add(receipt.receipt_id)
            self._observed_receipts.append(receipt)
        return receipt


class GovernedProviderReasoningController:
    """Bounded provider tool loop composed over the existing LBE tool owner."""

    def __init__(self, *, runtime: SessionMemoryRuntimeBridge, provider_id: str, provider_config: ProviderConfig) -> None:
        if not isinstance(runtime, SessionMemoryRuntimeBridge):
            raise TypeError("runtime must be SessionMemoryRuntimeBridge")
        if not isinstance(provider_config, ProviderConfig):
            raise TypeError("provider_config must be ProviderConfig")
        clean_provider = str(provider_id).strip()
        if not clean_provider:
            raise ValueError("provider_id must be non-empty")
        if runtime.session_state.provider_id != clean_provider:
            raise ValueError("provider identity does not match persisted session")
        if runtime.session_state.provider_model != provider_config.model.strip():
            raise ValueError("provider model does not match persisted session")

        state = runtime.session_state
        decision = resolve_mode(ModeRequest(
            intent="fix_issue",
            permission=state.permission or "read_only",
            runtime_policy=state.runtime_policy or "audit",
            workspace_root=str(runtime.workspace_root),
        ))
        if decision.mode != "coding":
            raise ValueError("governed coding controller requires resolved coding mode")

        self._runtime = runtime
        self._provider_id = clean_provider
        self._provider_config = provider_config
        self._context = ToolExecutionContext(
            mode_decision=decision,
            workspace_id=runtime.project_workspace_id,
            workspace_root=runtime.workspace_root,
            configured_root_id=runtime.project_workspace_id,
        )
        self._governed_mutation_paths: set[str] = set()
        registry = ToolRegistry()
        registry.register(workspace_read_spec(), build_workspace_read_handler(EvidenceService()))
        registry.register(workspace_create_candidate_text_spec(), build_workspace_create_candidate_text_handler())
        registry.register(workspace_write_text_spec(), build_workspace_write_text_handler())
        registry.register(process_run_registered_spec(), build_process_run_registered_handler())
        registry.register(git_status_spec(), build_git_status_handler())
        registry.register(git_stage_paths_spec(), build_git_stage_paths_handler(lambda: frozenset(self._governed_mutation_paths)))
        registry.register(git_commit_staged_spec(), build_git_commit_staged_handler(lambda: frozenset(self._governed_mutation_paths)))
        self._registry = registry
        self._guidance: AgentGuidance = build_agent_guidance(mode_decision=decision, workspace_root=runtime.workspace_root, tools=registry.specs())
        self._orchestrator = _ReceiptTrackingOrchestrator(registry=registry)
        self._adapter = OpenAICompatibleEventAdapter(config=provider_config)

    def run(self, request: LBERequest) -> LBEResponse:
        task_id = str(request.task_id or "").strip()
        if not task_id:
            raise ValueError("governed coding requires a task_id")

        turn_id = f"turn-{uuid4().hex}"
        messages: list[dict[str, object]] = [
            {"role": "system", "content": self._guidance.prompt},
            {"role": "user", "content": request.problem.strip()},
        ]
        provider_output = ""
        terminal_error: OrchestrationError | None = None
        try:
            for _iteration in range(8):
                call_ids: dict[str, str] = {}
                events = self._adapter.complete(
                    messages=tuple(messages),
                    provider_id=self._provider_id,
                    lbe_call_id_for_provider_tool_call=lambda provider_call_id: call_ids.setdefault(provider_call_id, f"lbe-{turn_id}-{len(call_ids) + 1}"),
                    tools=tuple(_provider_tool_definition(index, spec) for index, spec in enumerate(self._registry.specs())),
                )
                terminal_error = _provider_event_error(events)
                if terminal_error is not None:
                    break
                provider_output = _message_text(events) or provider_output
                calls = tuple(event for event in events if event.event_type is ModelEventType.TOOL_CALL_COMPLETED)
                if not calls:
                    if any(event.event_type is ModelEventType.TURN_COMPLETED for event in events):
                        break
                    terminal_error = OrchestrationError(code="PROVIDER_TURN_INCOMPLETE", message="provider returned neither a completed turn nor an executable tool call")
                    break
                messages.append(_assistant_tool_message(provider_output, calls))
                for event in calls:
                    assert event.provider_tool_call_id is not None
                    assert event.tool_name is not None
                    tool_id = _tool_id_for_provider_name(event.tool_name, self._registry.specs())
                    receipt = self._orchestrator.invoke(ToolRequest(
                        operation_id=f"{turn_id}:{event.lbe_call_id}",
                        tool_id=tool_id,
                        arguments=dict(event.tool_arguments or {}),
                        context=self._context,
                    ))
                    if receipt.status is ToolReceiptStatus.EXECUTED and receipt.tool_id in {"workspace.create_candidate_text", "workspace.write_text"}:
                        path = str((receipt.output or {}).get("path", "")).strip()
                        if path:
                            self._governed_mutation_paths.add(path.replace("\\", "/"))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": event.provider_tool_call_id,
                        "content": json.dumps(_receipt_payload(receipt), ensure_ascii=False, sort_keys=True),
                    })
            else:
                terminal_error = OrchestrationError(code="PROVIDER_TOOL_ITERATION_LIMIT", message="provider exceeded the bounded eight-iteration tool loop")
        except Exception as exc:
            terminal_error = OrchestrationError(code="GOVERNED_PROVIDER_RUNTIME_ERROR", message=f"{type(exc).__name__}: {exc}")

        receipts = self._orchestrator.observed_receipts
        receipt_payload = [_receipt_payload(receipt) for receipt in receipts]
        mutated = any(
            receipt.status is ToolReceiptStatus.EXECUTED
            and (registered := self._registry.get(receipt.tool_id)) is not None
            and registered.spec.access_class is ToolAccessClass.WRITE
            for receipt in receipts
        )
        deterministic_result = {
            "runtime": "governed_provider",
            "turn_id": turn_id,
            "provider_id": self._provider_id,
            "provider_model": self._provider_config.model.strip(),
            "governed_tool_receipts": receipt_payload,
            "provider_output": provider_output,
            "agent_guidance": self._guidance.audit_payload(),
            "governed_mutation_paths": sorted(self._governed_mutation_paths),
            "direct_native_mutation_tools_exposed": False,
            "lbe_completion_truth": False,
        }

        if terminal_error is not None:
            return self._response(task_id=task_id, deterministic_result=deterministic_result, outcome="ORCHESTRATION_ERROR", read_only=not mutated, error=terminal_error)
        return self._response(task_id=task_id, deterministic_result=deterministic_result, outcome="COMPLETED", read_only=not mutated, error=None)

    def _response(self, *, task_id: str, deterministic_result: Mapping[str, object], outcome: str, read_only: bool, error: OrchestrationError | None) -> LBEResponse:
        return LBEResponse(
            task_id=task_id,
            workspace_identity={
                "workspace_id": self._runtime.project_workspace_id,
                "configured_root_id": self._runtime.project_workspace_id,
                "target_project_root": str(self._runtime.workspace_root),
            },
            workspace_profile={
                "mode": "coding",
                "provider_id": self._provider_id,
                "governed_tools": [spec.tool_id for spec in self._registry.specs()],
                "native_mutation_tools": [],
            },
            plan=None,
            deterministic_result=dict(deterministic_result),
            explanation=None,
            outcome=outcome,
            proposal=None,
            error=error,
            read_only=read_only,
        )


def _provider_tool_definition(index: int, spec: ToolSpec) -> dict[str, object]:
    properties = {name: {"type": "string"} for name in (*spec.required_arguments, *spec.optional_arguments)}
    descriptions = {
        "workspace.read": "Read current workspace evidence through the LBE evidence owner.",
        "workspace.create_candidate_text": "Create one new UTF-8 text file inside an existing allowed workspace directory. Fails if the file already exists.",
        "workspace.write_text": "Create or update one UTF-8 text file through LBE. Updating an existing file requires its current SHA-256 to prevent stale overwrite.",
        "process.run_registered": "Run one command from the LBE-owned process catalog. Arbitrary shell commands are not accepted.",
        "git.status": "Inspect the primary canonical main Git workspace.",
        "git.stage_paths": "Stage only paths mutated by governed LBE tools during this turn. paths_json must be a JSON string array.",
        "git.commit_staged": "Commit only the governed paths staged in this turn on canonical main; deterministic execution requires the implementation gate to pass before committing.",
    }
    return {
        "type": "function",
        "function": {
            "name": f"lbe_{index}_{spec.tool_id.replace('.', '_')}",
            "description": descriptions.get(spec.tool_id, f"LBE governed tool {spec.tool_id}"),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(spec.required_arguments),
                "additionalProperties": False,
            },
        },
    }


def _receipt_payload(receipt: ToolReceipt) -> dict[str, object]:
    authorization = receipt.authorization
    return {
        "receipt_id": receipt.receipt_id,
        "operation_id": receipt.operation_id,
        "tool_id": receipt.tool_id,
        "status": receipt.status.value,
        "authorization": None if authorization is None else {"verdict": authorization.verdict.value, "rationale": authorization.rationale},
        "output": dict(receipt.output or {}),
        "evidence": [dict(item) for item in receipt.evidence],
        "error_code": receipt.error_code,
        "error_message": receipt.error_message,
    }


def _tool_id_for_provider_name(name: str, specs: tuple[ToolSpec, ...]) -> str:
    for index, spec in enumerate(specs):
        if name == f"lbe_{index}_{spec.tool_id.replace('.', '_')}":
            return spec.tool_id
    raise ValueError(f"provider requested an unregistered tool: {name}")


def _assistant_tool_message(text: str, calls: tuple[NormalizedModelEvent, ...]) -> dict[str, object]:
    return {
        "role": "assistant",
        "content": text or None,
        "tool_calls": [
            {
                "id": event.provider_tool_call_id,
                "type": "function",
                "function": {"name": event.tool_name, "arguments": json.dumps(dict(event.tool_arguments or {}), ensure_ascii=False, sort_keys=True)},
            }
            for event in calls
        ],
    }


def _provider_event_error(events: tuple[NormalizedModelEvent, ...]) -> OrchestrationError | None:
    error = next((event for event in events if event.event_type is ModelEventType.ERROR), None)
    if error is None:
        return None
    return OrchestrationError(code=error.error_code or "PROVIDER_RESPONSE_ERROR", message="provider returned an error event")


def _message_text(events: tuple[NormalizedModelEvent, ...]) -> str:
    return "".join(event.text or "" for event in events if event.event_type is ModelEventType.MESSAGE_COMPLETED)
