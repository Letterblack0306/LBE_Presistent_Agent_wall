import hashlib
import json
from pathlib import Path

import pytest

import agent


def _configure_isolated_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, roots: list[dict]) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "knowledge_roots": roots,
        "max_file_bytes": 5_000_000,
        "progress_every_files": 1000,
        "checkpoint_every_files": 1000,
    }), encoding="utf-8")
    state = tmp_path / "state"
    monkeypatch.setattr(agent, "CONFIG_PATH", config_path)
    monkeypatch.setattr(agent, "STATE_DIR", state)
    monkeypatch.setattr(agent, "DATABASE_PATH", state / "workspace.db")
    monkeypatch.setattr(agent, "PROGRESS_PATH", state / "trace_progress.json")
    monkeypatch.setattr(agent, "SUMMARY_PATH", state / "workspace_trace.json")
    monkeypatch.setattr(agent, "LAST_SEARCH_PATH", state / "last_search.json")


def test_context_load_adds_portable_reference_root_and_workspace_class(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _configure_isolated_state(monkeypatch, tmp_path, [{"name": "work", "path": str(workspace)}])

    context = agent.Context.load()

    assert [(root.name, root.root_class) for root in context.roots] == [
        ("work", "workspace"),
        ("lbe-reference", "reference"),
    ]
    assert context.roots[-1].path == (agent.ROOT / "examples" / "reference").resolve()


def test_reserved_name_and_overlap_are_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "nested"
    nested.mkdir(parents=True)

    _configure_isolated_state(monkeypatch, tmp_path, [{"name": "lbe-reference", "path": str(workspace)}])
    with pytest.raises(agent.GovernanceError, match="reserved"):
        agent.Context.load()

    _configure_isolated_state(monkeypatch, tmp_path, [
        {"name": "first", "path": str(workspace)},
        {"name": "second", "path": str(nested)},
    ])
    with pytest.raises(agent.GovernanceError, match="Overlapping roots"):
        agent.Context.load()


def test_reference_indexing_retrieval_metadata_and_invalid_yaml_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _configure_isolated_state(monkeypatch, tmp_path, [{"name": "work", "path": str(workspace)}])
    canonical = agent.ROOT / "state" / "workspace.db"
    canonical_hash = hashlib.sha256(canonical.read_bytes()).hexdigest() if canonical.exists() else None

    summary = agent.trace_workspace(agent.Context.load())
    assert summary["database"] == str(tmp_path / "state" / "workspace.db")
    assert (tmp_path / "state" / "workspace.db").exists()

    for query in (
        "authority owner", "duplicate handler", "duplicate execution", "state owner",
        "persistence owner", "UI runtime disagreement",
    ):
        result = agent.search_workspace(agent.Context.load(), query, roots=["lbe-reference"])
        assert result["result_count"] >= 1, query
        record = next(item for item in result["results"] if item["gallery_metadata"].get("id") == "architecture.authority-ownership")
        assert record["root_class"] == "reference"
        assert record["source_class"] == "reference_pattern"
        assert record["metadata_parse_status"] == "parsed"
        assert set(record["gallery_metadata"]) >= {
            "id", "record_type", "source_class", "authority_level", "verification_status",
            "workspace_scope", "execution_status", "guard_binding",
        }

    for query in ("CEP manifest parsing", "dependency lockfile", "image rendering"):
        assert agent.search_workspace(agent.Context.load(), query, roots=["lbe-reference"])["result_count"] == 0

    fake_root = tmp_path / "fake-root"
    reference = fake_root / "examples" / "reference"
    reference.mkdir(parents=True)
    (reference / "invalid.yaml").write_text("id: [unterminated", encoding="utf-8")
    monkeypatch.setattr(agent, "ROOT", fake_root)
    agent.trace_workspace(agent.Context.load())
    invalid = agent.search_workspace(agent.Context.load(), "unterminated", roots=["lbe-reference"])
    assert invalid["result_count"] == 1
    assert invalid["results"][0]["metadata_parse_status"] == "invalid"
    assert invalid["results"][0]["gallery_metadata"] == {}
    assert (hashlib.sha256(canonical.read_bytes()).hexdigest() if canonical.exists() else None) == canonical_hash
