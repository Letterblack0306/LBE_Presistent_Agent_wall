"""Evidence traversal must prune heavy/generated trees instead of enumerating them."""
from pathlib import Path

import pytest

from lbe_guard_inspector import evidence_service as es


def _tree(root: Path) -> None:
    for rel in (
        "src/app.py",
        "docs/status.md",
        "node_modules/pkg/index.js",
        ".git/config",
        "dist/bundle.js",
        "build/out.py",
        "target/debug/x.rs",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")


def _rel(root: Path, paths) -> set[str]:
    return {p.relative_to(root).as_posix() for p in paths}


def test_search_walk_prunes_vendor_generated_and_vcs_directories(tmp_path: Path) -> None:
    _tree(tmp_path)
    seen = _rel(tmp_path, es._iter_workspace_files(tmp_path, include_excluded=False))
    assert seen == {"src/app.py", "docs/status.md"}


def test_include_excluded_keeps_classified_dirs_but_never_vcs_or_vendor_caches(tmp_path: Path) -> None:
    _tree(tmp_path)
    seen = _rel(tmp_path, es._iter_workspace_files(tmp_path, include_excluded=True))
    assert "dist/bundle.js" in seen and "build/out.py" in seen
    assert not any(p.startswith((".git/", "node_modules/", "target/")) for p in seen)


def test_exact_guard_paths_resolve_without_any_directory_walk(tmp_path: Path, monkeypatch) -> None:
    _tree(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("exact paths must not trigger a workspace walk")

    monkeypatch.setattr(es.os, "walk", forbidden)
    found = es._guard_candidate_paths(tmp_path, ["docs/status.md", "dist/bundle.js"])
    assert _rel(tmp_path, found) == {"docs/status.md", "dist/bundle.js"}


def test_wildcard_guard_pattern_reaches_explicitly_named_generated_dir(tmp_path: Path) -> None:
    _tree(tmp_path)
    found = _rel(tmp_path, es._guard_candidate_paths(tmp_path, ["dist/*.js"]))
    assert "dist/bundle.js" in found
    # a broad pattern still never descends into vendored/VCS trees
    broad = _rel(tmp_path, es._guard_candidate_paths(tmp_path, ["**/*.js"]))
    assert not any(p.startswith(("node_modules/", ".git/")) for p in broad)


def test_guard_paths_cannot_escape_the_workspace_root(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    (tmp_path / "secret.md").write_text("s", encoding="utf-8")
    assert es._guard_candidate_paths(root, ["../secret.md"]) == []
