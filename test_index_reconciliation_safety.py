"""Regression coverage for indexer traversal and reconciliation safety.

IDX-1/IDX-2: a walk that aborts partway must not be treated as complete, and
must not cause the pruning step to delete index rows for files the walk never
reached.
"""

from __future__ import annotations

import sqlite3

import pytest

import agent


@pytest.fixture()
def isolated_runtime(tmp_path, monkeypatch):
    """Point every runtime path at a temp state dir for the duration of a test."""
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setattr(agent, "STATE_DIR", state)
    monkeypatch.setattr(agent, "DATABASE_PATH", state / "workspace.db")
    monkeypatch.setattr(agent, "PROGRESS_PATH", state / "trace_progress.json")
    monkeypatch.setattr(agent, "SUMMARY_PATH", state / "workspace_trace.json")
    return state


def _context(workspace):
    return agent.Context(
        config={"knowledge_roots": [{"name": "root", "path": str(workspace)}]},
        governance={"forbidden_globs": [], "allowed_read_paths": ["."]},
        roots=(agent.KnowledgeRoot(name="root", path=workspace),),
        missing_roots=(),
    )


def _seed(database, workspace) -> None:
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS files (
            root TEXT NOT NULL, path TEXT NOT NULL, physical_path TEXT NOT NULL,
            size INTEGER NOT NULL, modified_ns INTEGER NOT NULL, sha256 TEXT,
            hash_status TEXT, error TEXT, first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL, last_seen_run TEXT NOT NULL,
            PRIMARY KEY (root, path)
        );
        """
    )
    for name in ("file-a.txt", "file-b.txt"):
        connection.execute(
            "INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                "root",
                f"root/{name}",
                str(workspace / name),
                5,
                1,
                "oldhash",
                "hashed",
                None,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "run-old",
            ),
        )
    connection.commit()
    connection.close()


def _indexed_paths(database) -> set[str]:
    connection = sqlite3.connect(database)
    try:
        return {row[0] for row in connection.execute("SELECT path FROM files")}
    finally:
        connection.close()
