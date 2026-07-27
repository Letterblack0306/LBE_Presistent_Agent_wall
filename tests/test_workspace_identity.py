from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.workspace_identity import (
    canonical_workspace_root,
    project_workspace_id,
)


def test_same_canonical_root_derives_same_id(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    assert project_workspace_id(root) == project_workspace_id(root)


def test_sibling_projects_under_one_configured_root_derive_different_ids(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "configured"
    parent.mkdir()
    a = parent / "a"
    b = parent / "b"
    a.mkdir()
    b.mkdir()
    assert project_workspace_id(a) != project_workspace_id(b)


def test_different_clone_roots_derive_different_ids_even_with_identical_basenames(
    tmp_path: Path,
) -> None:
    left = tmp_path / "left" / "project"
    right = tmp_path / "right" / "project"
    left.mkdir(parents=True)
    right.mkdir(parents=True)
    assert project_workspace_id(left) != project_workspace_id(right)


def test_canonical_workspace_root_rejects_nonexistent(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        canonical_workspace_root(tmp_path / "missing")


def test_canonical_workspace_root_rejects_file(tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    file.write_text("x", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        canonical_workspace_root(file)


def test_requested_id_is_used_as_prefix_only(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    derived = project_workspace_id(root, requested_id="custom")
    assert derived.startswith("custom-")
    assert len(derived) == len("custom-") + 16


def test_dotdot_traversal_is_resolved_and_not_identity(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    target = root / ".."

    with pytest.raises(FileNotFoundError):
        canonical_workspace_root(target)


def test_symlink_outside_project_is_rejected(tmp_path: Path) -> None:
    inside = tmp_path / "inside"
    outside = tmp_path / "outside"
    inside.mkdir()
    outside.mkdir()
    link = inside / "link"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")

    with pytest.raises(FileNotFoundError):
        canonical_workspace_root(link)
