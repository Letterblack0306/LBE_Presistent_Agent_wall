from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess

import agent
import pytest

from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge

# --- IDX-1 / IDX-2 / IDX-3: indexer traversal and governance revalidation ---


@pytest.fixture()
def _isolated_index_state(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setattr(agent, "STATE_DIR", state)
    monkeypatch.setattr(agent, "DATABASE_PATH", state / "workspace.db")
    monkeypatch.setattr(agent, "PROGRESS_PATH", state / "trace_progress.json")
    monkeypatch.setattr(agent, "SUMMARY_PATH", state / "workspace_trace.json")
    return state


def _index_context(workspace, governance):
    return agent.Context(
        config={"knowledge_roots": [{"name": "root", "path": str(workspace)}]},
        governance=governance,
        roots=(agent.KnowledgeRoot(name="root", path=workspace),),
        missing_roots=(),
    )


def _seed_index(database, workspace):
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
            ("root", f"root/{name}", str(workspace / name), 5, 1, "oldhash",
             "hashed", None, "2026-01-01T00:00:00+00:00",
             "2026-01-01T00:00:00+00:00", "run-old"),
        )
    connection.commit()
    connection.close()


def _indexed_paths(database):
    connection = sqlite3.connect(database)
    try:
        return {row[0] for row in connection.execute("SELECT path FROM files")}
    finally:
        connection.close()


def test_incomplete_walk_preserves_unreached_index_rows(
    _isolated_index_state, monkeypatch
):
    """IDX-1/IDX-2: a walk aborted mid-root must not prune unreached rows."""
    workspace = _isolated_index_state.parent / "ws"
    workspace.mkdir()
    (workspace / "file-a.txt").write_text("alpha\n", encoding="utf-8")
    (workspace / "file-b.txt").write_text("beta\n", encoding="utf-8")
    database = _isolated_index_state / "workspace.db"
    _seed_index(database, workspace)

    real_rglob = Path.rglob

    def failing_rglob(self, pattern):
        for index, item in enumerate(real_rglob(self, pattern)):
            if index >= 1:
                raise PermissionError(13, "simulated traversal failure")
            yield item

    monkeypatch.setattr(Path, "rglob", failing_rglob)

    summary = agent.trace_workspace(
        _index_context(workspace, {"forbidden_globs": [], "allowed_read_paths": ["."]})
    )

    assert "root/file-b.txt" in _indexed_paths(database), (
        "a row for a file the walk never reached must be preserved, not pruned"
    )
    assert summary["status"] == "finished_with_gaps"
    assert summary["statistics"]["reconciled"] is False
    assert summary["statistics"]["incomplete_roots_this_run"] == ["root"]
    assert summary["statistics"]["traversal_errors_this_run"] == 1


def test_complete_walk_still_prunes_genuinely_deleted_file(_isolated_index_state):
    """Pruning must still work after a complete walk with a real deletion."""
    workspace = _isolated_index_state.parent / "ws"
    workspace.mkdir()
    (workspace / "file-a.txt").write_text("alpha\n", encoding="utf-8")
    database = _isolated_index_state / "workspace.db"
    _seed_index(database, workspace)
    (workspace / "file-b.txt").unlink(missing_ok=True)

    summary = agent.trace_workspace(
        _index_context(workspace, {"forbidden_globs": [], "allowed_read_paths": ["."]})
    )

    assert "root/file-b.txt" not in _indexed_paths(database), (
        "a genuinely deleted file must still be pruned after a complete walk"
    )
    assert summary["status"] == "completed"
    assert summary["statistics"]["reconciled"] is True


def test_search_revalidates_current_policy_against_stale_index_rows(
    _isolated_index_state,
):
    """IDX-3: a row indexed under an older policy must not be searchable now."""
    workspace = _isolated_index_state.parent / "ws"
    workspace.mkdir()
    secret = workspace / "secret.txt"
    secret.write_text("classified needle\n", encoding="utf-8")
    database = _isolated_index_state / "workspace.db"
    _seed_index(database, workspace)
    connection = sqlite3.connect(database)
    connection.execute(
        "INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("root", "root/secret.txt", str(secret), 19, 1, "oldhash", "hashed", None,
         "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", "run-old"),
    )
    connection.commit()
    connection.close()

    permissive = _index_context(
        workspace, {"forbidden_globs": [], "allowed_read_paths": ["."]}
    )
    assert agent.search_workspace(permissive, "needle")["result_count"] == 1

    now_forbidden = _index_context(
        workspace, {"forbidden_globs": ["**/secret.txt"], "allowed_read_paths": ["."]}
    )
    result = agent.search_workspace(now_forbidden, "needle")

    assert result["result_count"] == 0, (
        "search must re-check the current policy, not trust the stored index row"
    )
    assert result["policy_blocked_files"] >= 1


# --- PROV-1: provider config model must follow the persisted session model ---


def _prov_runtime(tmp_path, *, provider_model, provider_id="openrouter"):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("governed evidence\n", encoding="utf-8")
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "state.sqlite",
        project_workspace_id="project-1",
        workspace_root=workspace,
        session_id="session-prov",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id=provider_id,
        provider_model=provider_model,
        reasoning_engine="cline",
    )


def test_provider_config_model_binds_to_persisted_session_model(tmp_path, monkeypatch):
    """PROV-1: an endpoint default model must not break the governed turn."""
    from lbe_guard_inspector.runtime.governed_coding import (
        _GovernedCodingControllerBase,
    )

    runtime = _prov_runtime(tmp_path, provider_model="qwen-selected")

    # Endpoint config carries a different default model than the session selected.
    controller = _GovernedCodingControllerBase(
        runtime=runtime,
        provider_id="openrouter",
        provider_config=ProviderConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            model="gemma-endpoint-default",
            timeout_seconds=5,
            api_key="test-key",
        ),
        engine_id="cline",
    )

    assert controller._provider_config.model == "qwen-selected", (
        "the persisted session is the model authority; the config must bind to it"
    )
    assert runtime.session_state.provider_model == "qwen-selected", (
        "binding must not mutate the persisted session selection"
    )


def test_provider_identity_mismatch_remains_fail_closed(tmp_path, monkeypatch):
    """PROV-1 must not weaken provider identity, which decides credential routing."""
    from lbe_guard_inspector.runtime.governed_coding import (
        _GovernedCodingControllerBase,
    )

    runtime = _prov_runtime(tmp_path, provider_model="qwen-selected")

    with pytest.raises(ValueError, match="provider identity does not match"):
        _GovernedCodingControllerBase(
            runtime=runtime,
            provider_id="some-other-provider",
            provider_config=ProviderConfig(
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                model="qwen-selected",
                timeout_seconds=5,
                api_key="test-key",
            ),
            engine_id="cline",
        )


def test_declared_config_provider_id_mismatch_fails_closed(tmp_path, monkeypatch):
    """A declared config provider_id that disagrees must not reach the turn."""
    from lbe_guard_inspector.runtime.governed_coding import (
        _GovernedCodingControllerBase,
    )

    runtime = _prov_runtime(tmp_path, provider_model="qwen-selected")

    # provider_id argument matches the session, but the config declares another
    # identity. The canonical helper must still refuse to route credentials.
    with pytest.raises(ValueError, match="identity does not match persisted session"):
        _GovernedCodingControllerBase(
            runtime=runtime,
            provider_id="openrouter",
            provider_config=ProviderConfig(
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                model="qwen-selected",
                timeout_seconds=5,
                api_key="test-key",
                provider_id="attacker-endpoint",
            ),
            engine_id="cline",
        )


def test_generic_compatible_config_binds_to_session_provider(tmp_path, monkeypatch):
    """A config with no provider_id binds to the persisted session provider."""
    from lbe_guard_inspector.runtime.governed_coding import (
        _GovernedCodingControllerBase,
    )

    runtime = _prov_runtime(tmp_path, provider_model="qwen-selected")

    controller = _GovernedCodingControllerBase(
        runtime=runtime,
        provider_id="openrouter",
        provider_config=ProviderConfig(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="qwen-selected",
            timeout_seconds=5,
            api_key="test-key",
        ),
        engine_id="cline",
    )

    # A native/undeclared-identity config is accepted: the controller routes under
    # the session provider it was constructed with. Binding a config's declared
    # provider_id is the product-entry config owner's job, not this layer.
    assert controller._provider_id == "openrouter"
    assert controller._provider_config.provider_id is None
    assert controller._provider_config.model == "qwen-selected"


def test_declared_matching_provider_id_is_preserved(tmp_path, monkeypatch):
    """A declared provider_id equal to the session survives construction."""
    from lbe_guard_inspector.runtime.governed_coding import (
        _GovernedCodingControllerBase,
    )

    runtime = _prov_runtime(tmp_path, provider_model="qwen-selected")

    controller = _GovernedCodingControllerBase(
        runtime=runtime,
        provider_id="openrouter",
        provider_config=ProviderConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            model="qwen-selected",
            timeout_seconds=5,
            api_key="test-key",
            provider_id="openrouter",
        ),
        engine_id="cline",
    )

    assert controller._provider_config.provider_id == "openrouter"


def test_native_transport_without_provider_id_is_accepted(tmp_path, monkeypatch):
    """Native transports carry no provider_id and must not be rejected here."""
    from lbe_guard_inspector.runtime.governed_coding import (
        _GovernedCodingControllerBase,
    )

    for index, endpoint in enumerate(
        (
            "https://api.anthropic.com/v1/messages",
            "https://generativelanguage.googleapis.com/v1beta/models/g:generateContent",
            "https://api.openai.com/v1/responses",
        )
    ):
        root = tmp_path / f"native-{index}"
        root.mkdir()
        runtime = SessionMemoryRuntimeBridge(
            database_path=root / "state.sqlite",
            project_workspace_id="project-native",
            workspace_root=root,
            session_id="session-native",
            mode="coding",
            permission="write_allowed",
            runtime_policy="permissive",
            provider_id="openrouter",
            provider_model="model-a",
            reasoning_engine="cline",
        )
        controller = _GovernedCodingControllerBase(
            runtime=runtime,
            provider_id="openrouter",
            provider_config=ProviderConfig(
                endpoint=endpoint,
                model="model-a",
                timeout_seconds=5,
                api_key="test-key",
            ),
            engine_id="cline",
        )
        assert controller._provider_config.endpoint == endpoint


def test_binding_preserves_endpoint_credentials_and_timeout(tmp_path, monkeypatch):
    """Only the model and provider identity may change; the rest is preserved."""
    from lbe_guard_inspector.runtime.governed_coding import (
        _GovernedCodingControllerBase,
    )

    runtime = _prov_runtime(tmp_path, provider_model="qwen-selected")

    controller = _GovernedCodingControllerBase(
        runtime=runtime,
        provider_id="openrouter",
        provider_config=ProviderConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            model="gemma-endpoint-default",
            timeout_seconds=17,
            api_key="test-key",
        ),
        engine_id="cline",
    )

    bound = controller._provider_config
    assert bound.model == "qwen-selected"
    assert bound.endpoint == "https://openrouter.ai/api/v1/chat/completions"
    assert bound.api_key == "test-key"
    assert bound.timeout_seconds == 17
    assert runtime.session_state.provider_model == "qwen-selected"
    assert runtime.session_state.provider_id == "openrouter"


def test_missing_persisted_model_is_rejected(tmp_path, monkeypatch):
    """An empty session model must not silently adopt the endpoint default."""
    from lbe_guard_inspector.runtime.governed_coding import (
        _GovernedCodingControllerBase,
    )

    runtime = _prov_runtime(tmp_path, provider_model="qwen-selected")
    object.__setattr__(runtime.session_state, "provider_model", "  ")

    with pytest.raises(ValueError, match="does not have a selected model"):
        _GovernedCodingControllerBase(
            runtime=runtime,
            provider_id="openrouter",
            provider_config=ProviderConfig(
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                model="gemma-endpoint-default",
                timeout_seconds=5,
                api_key="test-key",
            ),
            engine_id="cline",
        )


from lbe_guard_inspector.runtime.governed_coding import (
    _ReceiptTrackingOrchestrator,
    _provider_tool_definition,
    _tool_id_for_provider_name,
    build_git_commit_staged_handler,
    build_git_stage_paths_handler,
    build_process_run_registered_handler,
    build_workspace_create_candidate_text_handler,
    build_workspace_write_text_handler,
    git_commit_staged_spec,
    git_stage_paths_spec,
    process_run_registered_spec,
    workspace_create_candidate_text_spec,
    workspace_write_text_spec,
    build_workspace_patch_handler,
    workspace_patch_spec,
)
from lbe_guard_inspector.authority_ownership import (
    OwnerAuthorityAuthorization,
    OwnerAuthorityStatus,
)
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
)


def _configure_runtime_files(
    tmp_path: Path,
    monkeypatch,
    *,
    allowed_write_paths=(".",),
    forbidden_globs=(),
    max_changed_files=1,
    max_patch_bytes=4096,
) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = tmp_path / "config.json"
    governance = tmp_path / "governance.json"
    config.write_text(
        json.dumps({"knowledge_roots": [{"name": "project-1", "path": str(workspace)}]}),
        encoding="utf-8",
    )
    governance.write_text(
        json.dumps(
            {
                "allowed_read_paths": ["."],
                "allowed_write_paths": list(allowed_write_paths),
                "forbidden_globs": list(forbidden_globs),
                "max_changed_files": max_changed_files,
                "max_patch_bytes": max_patch_bytes,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(agent, "CONFIG_PATH", config)
    monkeypatch.setattr(agent, "GOVERNANCE_PATH", governance)
    return workspace


def _context(workspace: Path, *capabilities: str) -> ToolExecutionContext:
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode="coding",
            allowed_behaviors=("development_mode_capabilities",),
            capabilities=capabilities or ("test_candidate",),
            rationale="test",
        ),
        workspace_id="project-1",
        workspace_root=workspace,
        configured_root_id="project-1",
    )


def _orchestrator() -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    registry.register(workspace_create_candidate_text_spec(), build_workspace_create_candidate_text_handler())
    return GovernedToolOrchestrator(registry=registry)


def test_owner_authority_blocker_denies_unproven_write_before_handler(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    registry = ToolRegistry()
    registry.register(
        workspace_create_candidate_text_spec(),
        build_workspace_create_candidate_text_handler(),
    )
    authority: OwnerAuthorityAuthorization | None = None
    orchestrator = _ReceiptTrackingOrchestrator(
        registry=registry,
        owner_authority=lambda: authority,
    )
    request = ToolRequest(
        operation_id="owner-blocked",
        tool_id="workspace.create_candidate_text",
        arguments={"path": "candidate.txt", "content": "blocked\n"},
        context=_context(workspace),
    )

    blocked = orchestrator.invoke(request)
    assert blocked.status is ToolReceiptStatus.DENIED
    assert blocked.error_code == "OWNER_AUTHORITY_BLOCKER"
    assert not (workspace / "candidate.txt").exists()

    authority = OwnerAuthorityAuthorization(
        issue_id="BRD-00027",
        owner_file_or_module="owner.py",
        owner_reason="owner evidence traces the relevant effect",
        owner_evidence=("BRD-00027:E12",),
        owner_status=OwnerAuthorityStatus.OWNER_PROVEN,
        allowed_paths=("candidate.txt",),
        validation_command="pytest tests/test_governed_coding.py",
    )
    allowed = _ReceiptTrackingOrchestrator(
        registry=registry,
        owner_authority=lambda: authority,
    ).invoke(
        ToolRequest(
            operation_id="owner-allowed",
            tool_id="workspace.create_candidate_text",
            arguments={"path": "candidate.txt", "content": "allowed\n"},
            context=_context(workspace),
        )
    )
    assert allowed.status is ToolReceiptStatus.EXECUTED
    assert (workspace / "candidate.txt").read_text(encoding="utf-8") == "allowed\n"


def test_create_candidate_text_executes_once_and_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    orchestrator = _orchestrator()
    request = ToolRequest(
        operation_id="op-create-1",
        tool_id="workspace.create_candidate_text",
        arguments={"path": "candidate.txt", "content": "governed\n"},
        context=_context(workspace),
    )
    first = orchestrator.invoke(request)
    second = orchestrator.invoke(request)
    assert first.status is ToolReceiptStatus.EXECUTED
    assert second is first
    assert first.authorization is not None
    assert first.authorization.verdict.value == "ALLOW"
    assert first.output["created"] is True
    assert first.output["path"] == "candidate.txt"
    assert first.output["sha256"]
    assert (workspace / "candidate.txt").read_text(encoding="utf-8") == "governed\n"


def test_create_candidate_text_never_overwrites_existing_file(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    target = workspace / "candidate.txt"
    target.write_text("original", encoding="utf-8")
    receipt = _orchestrator().invoke(
        ToolRequest(
            operation_id="op-create-existing",
            tool_id="workspace.create_candidate_text",
            arguments={"path": "candidate.txt", "content": "replacement"},
            context=_context(workspace),
        )
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"
    assert "already exists" in receipt.error_message
    assert target.read_text(encoding="utf-8") == "original"


def test_create_candidate_text_respects_allowed_write_paths(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch, allowed_write_paths=())
    receipt = _orchestrator().invoke(
        ToolRequest(
            operation_id="op-denied-path",
            tool_id="workspace.create_candidate_text",
            arguments={"path": "candidate.txt", "content": "blocked"},
            context=_context(workspace),
        )
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"
    assert "write path is not allowed" in receipt.error_message
    assert not (workspace / "candidate.txt").exists()


def test_create_candidate_text_respects_patch_limit(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch, max_patch_bytes=3)
    receipt = _orchestrator().invoke(
        ToolRequest(
            operation_id="op-too-large",
            tool_id="workspace.create_candidate_text",
            arguments={"path": "candidate.txt", "content": "four"},
            context=_context(workspace),
        )
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"
    assert "max_patch_bytes" in receipt.error_message
    assert not (workspace / "candidate.txt").exists()


def test_provider_tool_schema_and_reverse_mapping_are_lbe_owned() -> None:
    spec = workspace_create_candidate_text_spec()
    definition = _provider_tool_definition(0, spec)
    assert definition["function"]["name"] == "lbe_0_workspace_create_candidate_text"
    assert _tool_id_for_provider_name(definition["function"]["name"], (spec,)) == spec.tool_id
    with pytest.raises(ValueError, match="unregistered tool"):
        _tool_id_for_provider_name("shell.execute", (spec,))


def _write_orchestrator() -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    registry.register(workspace_write_text_spec(), build_workspace_write_text_handler())
    return GovernedToolOrchestrator(registry=registry)


def test_workspace_write_text_creates_new_file_with_receipt(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    receipt = _write_orchestrator().invoke(
        ToolRequest(
            operation_id="write-new",
            tool_id="workspace.write_text",
            arguments={"path": "new.txt", "content": "new\n"},
            context=_context(workspace, "modify"),
        )
    )
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output["created"] is True
    assert receipt.output["updated"] is False
    assert (workspace / "new.txt").read_text(encoding="utf-8") == "new\n"
    assert receipt.evidence[0]["verified"] is True


def test_workspace_write_text_requires_current_hash_for_existing_file(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    target = workspace / "existing.txt"
    target.write_text("before", encoding="utf-8")
    receipt = _write_orchestrator().invoke(
        ToolRequest(
            operation_id="write-no-hash",
            tool_id="workspace.write_text",
            arguments={"path": "existing.txt", "content": "after"},
            context=_context(workspace, "modify"),
        )
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert "expected_sha256 is required" in receipt.error_message
    assert target.read_text(encoding="utf-8") == "before"


def test_workspace_write_text_denies_stale_overwrite_and_accepts_exact_hash(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    target = workspace / "existing.txt"
    target.write_text("before", encoding="utf-8")
    before_hash = hashlib.sha256(b"before").hexdigest()
    stale = _write_orchestrator().invoke(
        ToolRequest(
            operation_id="write-stale",
            tool_id="workspace.write_text",
            arguments={"path": "existing.txt", "content": "after", "expected_sha256": "0" * 64},
            context=_context(workspace, "modify"),
        )
    )
    assert stale.status is ToolReceiptStatus.FAILED
    assert "stale overwrite denied" in stale.error_message
    assert target.read_text(encoding="utf-8") == "before"

    exact = _write_orchestrator().invoke(
        ToolRequest(
            operation_id="write-exact",
            tool_id="workspace.write_text",
            arguments={"path": "existing.txt", "content": "after", "expected_sha256": before_hash},
            context=_context(workspace, "modify"),
        )
    )
    assert exact.status is ToolReceiptStatus.EXECUTED
    assert exact.output["updated"] is True
    assert exact.output["before_sha256"] == before_hash
    assert target.read_text(encoding="utf-8") == "after"


def _patch_orchestrator() -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    registry.register(workspace_patch_spec(), build_workspace_patch_handler())
    return GovernedToolOrchestrator(registry=registry)


def test_workspace_patch_requires_exact_hash_and_records_unified_diff(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    target = workspace / "existing.txt"
    target.write_text("before\n", encoding="utf-8")
    before_hash = hashlib.sha256(target.read_bytes()).hexdigest()

    stale = _patch_orchestrator().invoke(ToolRequest(
        operation_id="patch-stale",
        tool_id="workspace.patch",
        arguments={"path": "existing.txt", "content": "after\n", "expected_sha256": "0" * 64},
        context=_context(workspace, "modify"),
    ))
    assert stale.status is ToolReceiptStatus.FAILED
    assert "stale overwrite denied" in stale.error_message
    assert target.read_text(encoding="utf-8") == "before\n"

    applied = _patch_orchestrator().invoke(ToolRequest(
        operation_id="patch-exact",
        tool_id="workspace.patch",
        arguments={"path": "existing.txt", "content": "after\n", "expected_sha256": before_hash},
        context=_context(workspace, "modify"),
    ))
    assert applied.status is ToolReceiptStatus.EXECUTED
    assert applied.output["updated"] is True
    assert "-before" in applied.output["patch"]
    assert "+after" in applied.output["patch"]
    assert applied.evidence[0]["metadata"]["tool_id"] == "workspace.patch"


def test_workspace_patch_rejects_escape_before_preimage_read(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    outside = tmp_path / "outside.txt"
    outside.write_text("must remain", encoding="utf-8")
    receipt = _patch_orchestrator().invoke(ToolRequest(
        operation_id="patch-escape",
        tool_id="workspace.patch",
        arguments={"path": "../outside.txt", "content": "changed", "expected_sha256": "0" * 64},
        context=_context(workspace, "modify"),
    ))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert outside.read_text(encoding="utf-8") == "must remain"


def test_registered_process_catalog_rejects_arbitrary_shell(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register(process_run_registered_spec(), build_process_run_registered_handler())
    orchestrator = GovernedToolOrchestrator(registry=registry)
    allowed = orchestrator.invoke(
        ToolRequest(
            operation_id="process-version",
            tool_id="process.run_registered",
            arguments={"command_id": "python.version"},
            context=_context(tmp_path, "inspect"),
        )
    )
    assert allowed.status is ToolReceiptStatus.EXECUTED
    assert allowed.output["command_id"] == "python.version"
    assert allowed.output["argv"]

    denied = orchestrator.invoke(
        ToolRequest(
            operation_id="process-shell",
            tool_id="process.run_registered",
            arguments={"command_id": "shell.execute"},
            context=_context(tmp_path, "inspect"),
        )
    )
    assert denied.status is ToolReceiptStatus.FAILED
    assert "not registered" in denied.error_message


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _init_main_repo(workspace: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is unavailable")
    init = _git("init", "-b", "main", cwd=workspace)
    if init.returncode != 0:
        fallback = _git("init", cwd=workspace)
        assert fallback.returncode == 0
        branch = _git("checkout", "-b", "main", cwd=workspace)
        assert branch.returncode == 0
    assert _git("config", "user.name", "LBE Test", cwd=workspace).returncode == 0
    assert _git("config", "user.email", "lbe-test@example.invalid", cwd=workspace).returncode == 0


def test_git_mutation_is_main_only_and_limited_to_governed_paths(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    _init_main_repo(workspace)
    target = workspace / "tracked.txt"
    target.write_text("before", encoding="utf-8")
    assert _git("add", "tracked.txt", cwd=workspace).returncode == 0
    assert _git("commit", "-m", "baseline", cwd=workspace).returncode == 0

    governed_paths: set[str] = set()
    registry = ToolRegistry()
    registry.register(workspace_write_text_spec(), build_workspace_write_text_handler())
    registry.register(git_stage_paths_spec(), build_git_stage_paths_handler(lambda: frozenset(governed_paths)))
    registry.register(git_commit_staged_spec(), build_git_commit_staged_handler(lambda: frozenset(governed_paths)))
    orchestrator = GovernedToolOrchestrator(registry=registry)

    before_hash = hashlib.sha256(b"before").hexdigest()
    write_receipt = orchestrator.invoke(
        ToolRequest(
            operation_id="git-write",
            tool_id="workspace.write_text",
            arguments={"path": "tracked.txt", "content": "after", "expected_sha256": before_hash},
            context=_context(workspace, "modify"),
        )
    )
    assert write_receipt.status is ToolReceiptStatus.EXECUTED
    governed_paths.add("tracked.txt")

    foreign = workspace / "foreign.txt"
    foreign.write_text("do not stage", encoding="utf-8")
    foreign_stage = orchestrator.invoke(
        ToolRequest(
            operation_id="git-foreign-stage",
            tool_id="git.stage_paths",
            arguments={"paths_json": json.dumps(["foreign.txt"])},
            context=_context(workspace, "modify"),
        )
    )
    assert foreign_stage.status is ToolReceiptStatus.FAILED
    assert "limited to paths mutated" in foreign_stage.error_message

    stage = orchestrator.invoke(
        ToolRequest(
            operation_id="git-stage",
            tool_id="git.stage_paths",
            arguments={"paths_json": json.dumps(["tracked.txt"])},
            context=_context(workspace, "modify"),
        )
    )
    assert stage.status is ToolReceiptStatus.EXECUTED
    assert stage.output["staged_paths"] == ["tracked.txt"]

    commit = orchestrator.invoke(
        ToolRequest(
            operation_id="git-commit",
            tool_id="git.commit_staged",
            arguments={"message": "governed change"},
            context=_context(workspace, "modify"),
        )
    )
    assert commit.status is ToolReceiptStatus.EXECUTED
    assert len(commit.output["commit"]) == 40
    assert commit.output["committed_paths"] == ["tracked.txt"]


def test_git_mutation_rejects_non_main_branch(tmp_path: Path, monkeypatch) -> None:
    workspace = _configure_runtime_files(tmp_path, monkeypatch)
    _init_main_repo(workspace)
    assert _git("checkout", "-b", "feature", cwd=workspace).returncode == 0
    governed_paths = frozenset({"file.txt"})
    registry = ToolRegistry()
    registry.register(git_stage_paths_spec(), build_git_stage_paths_handler(lambda: governed_paths))
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        ToolRequest(
            operation_id="git-feature",
            tool_id="git.stage_paths",
            arguments={"paths_json": json.dumps(["file.txt"])},
            context=_context(workspace, "modify"),
        )
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert "canonical main" in receipt.error_message
