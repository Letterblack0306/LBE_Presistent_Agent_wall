"""Fail-closed change-registration precondition for governed workspace mutations.

The checker is deliberately separate from R6C authorization. R6C answers whether
a capability is authorized; this module answers whether the current implementation
change has durable workspace/branch/worktree intent registered before mutation.

Repositories opt in with ``.ai/change-gate.json``. Read-only operations do not use
this gate. The gate is intended to run before any LBE-governed write handler.
"""
from __future__ import annotations

import fnmatch
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ChangeRegistrationCheck:
    allowed: bool
    code: str
    rationale: str
    change_id: str | None = None
    branch: str | None = None
    worktree_path: str | None = None


@dataclass(frozen=True)
class _GateConfig:
    canonical_branch: str
    require_intent_for_all_mutations: bool
    require_branch_and_worktree_outside_canonical: bool
    intent_file: str


@dataclass(frozen=True)
class _GitWorkspace:
    repo_root: Path
    branch: str
    primary_worktree: Path

    @property
    def is_detached(self) -> bool:
        return self.branch == "HEAD"


class ChangeRegistrationError(RuntimeError):
    """Raised only for internal registration/configuration parsing failures."""


def check_change_registration(
    workspace_root: str | Path,
    *,
    requested_path: str | None = None,
) -> ChangeRegistrationCheck:
    """Validate the active change declaration for one governed mutation.

    If the repository does not opt in with ``.ai/change-gate.json`` the check is
    neutral and returns ``allowed=True``. Once enabled, the gate fails closed.
    """

    root = Path(workspace_root).expanduser().resolve()
    config_result = _load_gate_config(root)
    if config_result is None:
        return ChangeRegistrationCheck(
            allowed=True,
            code="CHANGE_GATE_NOT_CONFIGURED",
            rationale="Repository does not enable the change-registration gate.",
        )
    config, config_error = config_result
    if config_error is not None:
        return ChangeRegistrationCheck(
            allowed=False,
            code="CHANGE_GATE_CONFIG_INVALID",
            rationale=config_error,
        )

    try:
        git = _inspect_git_workspace(root)
    except ChangeRegistrationError as exc:
        return ChangeRegistrationCheck(
            allowed=False,
            code="CHANGE_GATE_GIT_IDENTITY_UNRESOLVED",
            rationale=str(exc),
        )

    if git.is_detached:
        return ChangeRegistrationCheck(
            allowed=False,
            code="CHANGE_GATE_DETACHED_HEAD",
            rationale="Governed mutation is blocked on detached HEAD; register and use a named branch.",
            branch=git.branch,
            worktree_path=str(git.repo_root),
        )

    canonical = (
        git.branch == config.canonical_branch
        and _same_path(git.repo_root, git.primary_worktree)
    )

    intent_path = _safe_relative_file(root, config.intent_file)
    if config.require_intent_for_all_mutations and not intent_path.is_file():
        return ChangeRegistrationCheck(
            allowed=False,
            code="CHANGE_INTENT_REQUIRED",
            rationale=(
                f"Governed mutation requires an active change declaration at {config.intent_file}. "
                "Register the implementation intent before modifying the workspace."
            ),
            branch=git.branch,
            worktree_path=str(git.repo_root),
        )
    if not intent_path.is_file():
        return ChangeRegistrationCheck(
            allowed=True,
            code="CHANGE_INTENT_NOT_REQUIRED",
            rationale="Repository gate does not require an intent for this mutation.",
            branch=git.branch,
            worktree_path=str(git.repo_root),
        )

    try:
        intent = _load_json_object(intent_path)
    except ChangeRegistrationError as exc:
        return ChangeRegistrationCheck(
            allowed=False,
            code="CHANGE_INTENT_INVALID",
            rationale=str(exc),
            branch=git.branch,
            worktree_path=str(git.repo_root),
        )

    structural_error = _validate_intent_structure(intent)
    if structural_error is not None:
        return ChangeRegistrationCheck(
            allowed=False,
            code="CHANGE_INTENT_INVALID",
            rationale=structural_error,
            change_id=_optional_text(intent.get("changeId")),
            branch=git.branch,
            worktree_path=str(git.repo_root),
        )

    change_id = str(intent["changeId"]).strip()
    registered_branch = _optional_text(intent.get("branch"))
    registered_worktree = _optional_text(intent.get("worktreePath"))

    if registered_branch is not None and registered_branch != git.branch:
        return ChangeRegistrationCheck(
            allowed=False,
            code="CHANGE_INTENT_BRANCH_MISMATCH",
            rationale=(
                f"Active change intent is registered for branch '{registered_branch}', "
                f"but current branch is '{git.branch}'."
            ),
            change_id=change_id,
            branch=git.branch,
            worktree_path=str(git.repo_root),
        )

    if registered_worktree is not None:
        try:
            registered_path = Path(registered_worktree).expanduser().resolve()
        except (OSError, RuntimeError) as exc:
            return ChangeRegistrationCheck(
                allowed=False,
                code="CHANGE_INTENT_WORKTREE_INVALID",
                rationale=f"Registered worktreePath cannot be resolved: {exc}",
                change_id=change_id,
                branch=git.branch,
                worktree_path=str(git.repo_root),
            )
        if not _same_path(registered_path, git.repo_root):
            return ChangeRegistrationCheck(
                allowed=False,
                code="CHANGE_INTENT_WORKTREE_MISMATCH",
                rationale=(
                    f"Active change intent is registered for worktree '{registered_path}', "
                    f"but current worktree is '{git.repo_root}'."
                ),
                change_id=change_id,
                branch=git.branch,
                worktree_path=str(git.repo_root),
            )

    if not canonical and config.require_branch_and_worktree_outside_canonical:
        if registered_branch is None:
            return ChangeRegistrationCheck(
                allowed=False,
                code="CHANGE_INTENT_BRANCH_REQUIRED",
                rationale=(
                    "Current workspace is not the canonical main workspace; "
                    "the active intent must register the exact branch before mutation."
                ),
                change_id=change_id,
                branch=git.branch,
                worktree_path=str(git.repo_root),
            )
        if registered_worktree is None:
            return ChangeRegistrationCheck(
                allowed=False,
                code="CHANGE_INTENT_WORKTREE_REQUIRED",
                rationale=(
                    "Current workspace is not the canonical main workspace; "
                    "the active intent must register the exact worktreePath before mutation."
                ),
                change_id=change_id,
                branch=git.branch,
                worktree_path=str(git.repo_root),
            )

    if requested_path is not None:
        scope_error = _validate_requested_path(intent, requested_path)
        if scope_error is not None:
            return ChangeRegistrationCheck(
                allowed=False,
                code=scope_error[0],
                rationale=scope_error[1],
                change_id=change_id,
                branch=git.branch,
                worktree_path=str(git.repo_root),
            )

    return ChangeRegistrationCheck(
        allowed=True,
        code="CHANGE_INTENT_ACTIVE",
        rationale="Active change intent matches the current workspace/branch/worktree registration.",
        change_id=change_id,
        branch=git.branch,
        worktree_path=str(git.repo_root),
    )


def _load_gate_config(root: Path) -> tuple[_GateConfig, str | None] | None:
    path = root / ".ai" / "change-gate.json"
    if not path.is_file():
        return None
    try:
        raw = _load_json_object(path)
    except ChangeRegistrationError as exc:
        return (
            _GateConfig("main", True, True, ".ai/intent.json"),
            str(exc),
        )

    enabled = raw.get("enabled")
    if enabled is False:
        return None
    if enabled is not True:
        return (
            _GateConfig("main", True, True, ".ai/intent.json"),
            "change-gate.json must set enabled to true or false",
        )

    canonical = raw.get("canonicalBranch", "main")
    intent_file = raw.get("intentFile", ".ai/intent.json")
    require_all = raw.get("requireIntentForAllMutations", True)
    require_alt = raw.get("requireBranchAndWorktreeRegistrationOutsideCanonical", True)
    if not isinstance(canonical, str) or not canonical.strip():
        error = "canonicalBranch must be a non-empty string"
    elif not isinstance(intent_file, str) or not intent_file.strip():
        error = "intentFile must be a non-empty relative path"
    elif not isinstance(require_all, bool) or not isinstance(require_alt, bool):
        error = "change-gate boolean options must be true/false"
    else:
        error = None
    return (
        _GateConfig(
            canonical_branch=str(canonical).strip(),
            require_intent_for_all_mutations=bool(require_all),
            require_branch_and_worktree_outside_canonical=bool(require_alt),
            intent_file=str(intent_file).strip(),
        ),
        error,
    )


def _inspect_git_workspace(root: Path) -> _GitWorkspace:
    top = _run_git(root, "rev-parse", "--show-toplevel")
    repo_root = Path(top).expanduser().resolve()
    if not _same_path(repo_root, root):
        raise ChangeRegistrationError(
            f"active workspace root '{root}' is not the Git toplevel '{repo_root}'"
        )
    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    worktrees = _run_git(root, "worktree", "list", "--porcelain")
    primary = _parse_primary_worktree(worktrees)
    return _GitWorkspace(
        repo_root=repo_root,
        branch=branch.strip(),
        primary_worktree=primary,
    )


def _run_git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10.0,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ChangeRegistrationError(f"Git workspace identity check failed: {exc}") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown Git error"
        raise ChangeRegistrationError(f"Git workspace identity check failed: {message}")
    return completed.stdout.strip()


def _parse_primary_worktree(text: str) -> Path:
    for line in text.splitlines():
        if line.startswith("worktree "):
            raw = line[len("worktree ") :].strip()
            if raw:
                return Path(raw).expanduser().resolve()
    raise ChangeRegistrationError("git worktree list returned no primary worktree")


def _validate_intent_structure(intent: Mapping[str, Any]) -> str | None:
    if intent.get("schemaVersion") != 1:
        return "intent.json schemaVersion must equal 1"
    for key in ("changeId", "intent"):
        value = intent.get(key)
        if not isinstance(value, str) or not value.strip():
            return f"intent.json {key} must be a non-empty string"
    if intent.get("status") != "active":
        return "intent.json status must be 'active' before governed mutation"
    for key in ("allowedPaths", "explicitExclusions"):
        value = intent.get(key)
        if value is not None and (
            not isinstance(value, list)
            or any(not isinstance(item, str) or not item.strip() for item in value)
        ):
            return f"intent.json {key} must be an array of non-empty path patterns"
    return None


def _validate_requested_path(
    intent: Mapping[str, Any],
    requested_path: str,
) -> tuple[str, str] | None:
    normalized = _normalize_relative_path(requested_path)
    exclusions = tuple(str(item).strip() for item in intent.get("explicitExclusions", ()) or ())
    if any(_path_matches(normalized, pattern) for pattern in exclusions):
        return (
            "CHANGE_INTENT_EXCLUSION",
            f"Requested mutation path '{normalized}' is explicitly excluded by the active change intent.",
        )
    allowed = tuple(str(item).strip() for item in intent.get("allowedPaths", ()) or ())
    if allowed and not any(_path_matches(normalized, pattern) for pattern in allowed):
        return (
            "CHANGE_INTENT_SCOPE_MISMATCH",
            f"Requested mutation path '{normalized}' is outside the active intent allowedPaths.",
        )
    return None


def _normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChangeRegistrationError("requested mutation path must be a non-empty string")
    candidate = Path(value.replace("\\", "/").strip())
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ChangeRegistrationError("requested mutation path must stay inside the active workspace")
    return candidate.as_posix()


def _path_matches(path: str, pattern: str) -> bool:
    if os.name == "nt":
        path = path.casefold()
        pattern = pattern.replace("\\", "/").casefold()
    else:
        pattern = pattern.replace("\\", "/")
    return fnmatch.fnmatchcase(path, pattern)


def _safe_relative_file(root: Path, relative_value: str) -> Path:
    candidate = Path(relative_value.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ChangeRegistrationError("intentFile must stay inside the active workspace")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ChangeRegistrationError("intentFile must stay inside the active workspace") from exc
    return resolved


def _load_json_object(path: Path) -> Mapping[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ChangeRegistrationError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ChangeRegistrationError(f"{path} must contain a JSON object")
    return raw


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _same_path(left: Path, right: Path) -> bool:
    if os.name == "nt":
        return os.path.normcase(str(left)) == os.path.normcase(str(right))
    return left == right
