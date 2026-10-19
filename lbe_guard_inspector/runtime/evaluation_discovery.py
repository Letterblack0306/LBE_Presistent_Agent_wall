"""Read-only, repository-owned evaluation discovery; not an execution authority.

Matching evaluation recipes are hints for task validation, not evidence of PASS.
Only persisted completion contracts and their registered producers determine
whether a governed LBE task can claim completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import Iterable


@dataclass(frozen=True)
class EvaluationRecipe:
    eval_id: str
    path_prefixes: tuple[str, ...]
    commands: tuple[tuple[str, ...], ...]
    evidence_level: str
    success_criterion: str
    task_kinds: tuple[str, ...] = ()
    manual: bool = False


# These commands are explicitly descriptive. They must never be executed by
# this selector or promoted to a completion producer without an owner policy.
EVALUATION_RECIPES = (
    EvaluationRecipe(
        eval_id="lbe.tui.bridge-contract.v1",
        path_prefixes=("apps/lbe-terminal/", "lbe_guard_inspector/tui_bridge.py"),
        commands=(("py", "-3.13", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_tui_bridge.py"),),
        evidence_level="source/integration tests only",
        success_criterion="Bridge protocol tests pass; does not establish live UI behavior.",
        task_kinds=("tui", "bridge"),
    ),
    EvaluationRecipe(
        eval_id="lbe.tui.rust-regression.v1",
        path_prefixes=("apps/lbe-terminal/",),
        commands=(("cargo", "test", "--manifest-path", "apps/lbe-terminal/Cargo.toml"),),
        evidence_level="Rust test harness only",
        success_criterion="Rust cockpit tests pass; installed interactive acceptance remains separate.",
        task_kinds=("tui",),
    ),
    EvaluationRecipe(
        eval_id="lbe.tui.installed-interaction.v1",
        path_prefixes=("apps/lbe-terminal/", "lbe_guard_inspector/terminal_ui.py", "lbe_guard_inspector/tui_bridge.py"),
        commands=(),
        evidence_level="installed live terminal",
        success_criterion="Launch exact installed binary in PTY/ConPTY; observe typed message, reply or explicit failure, control keys, approval and correlated receipt where applicable.",
        task_kinds=("tui", "bridge"),
        manual=True,
    ),
    EvaluationRecipe(
        eval_id="lbe.tui.visual-board.v1",
        path_prefixes=("apps/lbe-terminal/",),
        commands=(),
        evidence_level="interactive visual comparison",
        success_criterion="Capture verified running binary and compare wide/compact/short layout to the authorized UI boards; image hashes only identify the captured frames.",
        task_kinds=("tui",),
        manual=True,
    ),
    EvaluationRecipe(
        eval_id="lbe.completion.policy-regression.v1",
        path_prefixes=("lbe_guard_inspector/runtime/completion_", "lbe_guard_inspector/runtime/task_completion_policy.py", "lbe_guard_inspector/runtime/validation_command_policy.py"),
        commands=(("py", "-3.13", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_completion_gate.py", "tests/test_completion_evidence_producers.py", "tests/test_task_completion_policy.py"),),
        evidence_level="completion policy tests only",
        success_criterion="Existing completion requirements and evidence producers retain their passing and fail-closed behavior.",
        task_kinds=("completion",),
    ),
)


def discover_evaluations(*, changed_paths: Iterable[str] = (), task_kind: str = "") -> tuple[EvaluationRecipe, ...]:
    """Return matching recipes without invoking tools, changing policy, or persisting state."""
    paths: list[str] = []
    for raw in changed_paths:
        if not isinstance(raw, str):
            raise TypeError("changed paths must be strings")
        path = raw.replace("\\", "/").removeprefix("./")
        if not path or PurePosixPath(path).is_absolute() or ".." in path.split("/"):
            raise ValueError("changed paths must be nonempty workspace-relative paths")
        paths.append(path)
    kind = task_kind.strip().lower()
    return tuple(recipe for recipe in EVALUATION_RECIPES if (
        (kind and kind in recipe.task_kinds)
        or any(path.startswith(prefix) for path in paths for prefix in recipe.path_prefixes)
    ))
