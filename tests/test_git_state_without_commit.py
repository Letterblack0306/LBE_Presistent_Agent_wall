"""A project that has been `git init`-ed but never committed must not fail the turn."""
import subprocess

from lbe_guard_inspector.memory.context import inspect_git_state


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_repository_without_commits_reports_no_head(tmp_path) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    state = inspect_git_state(tmp_path)
    assert state["head"] is None
    assert state["status_short"] == ["?? a.txt"]


def test_repository_with_a_commit_still_reports_head(tmp_path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed")
    assert len(inspect_git_state(tmp_path)["head"]) == 40
