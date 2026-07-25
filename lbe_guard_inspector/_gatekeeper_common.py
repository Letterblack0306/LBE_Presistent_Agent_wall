from __future__ import annotations

from pathlib import Path
from typing import Any


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def canonical_root(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if any(part == ".." for part in path.parts):
        raise ValueError("workspace_root must not contain '..' traversal")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise NotADirectoryError(str(resolved))
    return resolved


def normalize_relative_path(value: str | Path) -> str:
    text = str(value).replace("\\", "/").strip("/")
    if not text or text == ".":
        return ""
    candidate = Path(text)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise ValueError(f"Path must be workspace-relative: {value}")
    return candidate.as_posix()


def read_only_mutation_report() -> dict[str, bool]:
    return {
        "runtime_mutations_performed": False,
        "target_workspace_changed": False,
        "target_profile_changed": False,
        "rule_registry_changed": False,
        "index_changed": False,
    }
