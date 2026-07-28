from __future__ import annotations

import subprocess
from pathlib import Path

from lbe_guard_inspector.authority_ownership_inspector import AuthorityOwnershipInspector
from lbe_guard_inspector.memory import ValidationStatus
from lbe_guard_inspector.runtime_confirmation import (
    RuntimeConfirmationAdapter,
    RuntimeObservationStatus,
)
from lbe_guard_inspector.runtime_slice import RuntimeSlice
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "proof@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Proof"], cwd=root, check=True)
    (root / "tracked.txt").write_text("one\n", encoding="utf-8", newline="")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    return root


def _item(ref: str, kind: str, detail: str) -> dict[str, str]:
    return {"ref": ref, "kind": kind, "detail": detail}


def test_phase_12_end_to_end_proof(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    memory = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
    )
    initial = memory.start_or_resume(task_id="task-1")
    assert initial["workspace"]["project_workspace_id"] == "project-1"

    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()
    runtime.request_started("POST /guard-run")
    snapshot = runtime.snapshot()
    modules = {item["id"]: item for item in snapshot["modules"]}
    assert modules["module.registry"]["loaded"] is True
    assert modules["agent.http-server"]["current_activity"]["detail"] == "POST /guard-run"

    fact_id = memory.adapter.record_file_hash(relative_path="tracked.txt", task_id="task-1")
    command_id = memory.ingest_command_result(
        command="python -m pytest -q",
        cwd=root,
        exit_code=1,
        stderr="1 failed",
        task_id="task-1",
    )
    assert memory.store.get(fact_id).validation_status is ValidationStatus.VERIFIED
    assert memory.store.get(command_id).validation_status is ValidationStatus.VERIFIED

    checkpoint_id = memory.checkpoint(
        compaction={
            "source_message_count": 5,
            "source_prefix_hash": "sha256:" + "a" * 64,
            "source_last_message_key": "id:msg-5",
            "messages": [],
        },
        active_constraints=["do not commit"],
    )
    (root / "tracked.txt").write_text("two\n", encoding="utf-8", newline="")

    resumed = memory.start_or_resume(task_id="task-1")
    assert resumed["checkpoint"]["checkpoint_id"] == checkpoint_id
    assert resumed["checkpoint"]["active_constraints"] == ["do not commit"]
    assert memory.store.get(fact_id).validation_status is ValidationStatus.STALE

    confirmation = RuntimeConfirmationAdapter(runtime.watcher).observe(
        operation_id="workspace.module-state.update",
        module_id="agent.http-server",
    )
    assert confirmation.status is RuntimeObservationStatus.CONFIRMED
    assert confirmation.operation_id == "workspace.module-state.update"
    assert all(receipt["module_id"] == "agent.http-server" for receipt in confirmation.receipts)

    request = {
        "request_id": "request-1",
        "workspace_id": "project-1",
        "operation_id": "workspace.module-state.update",
        "canonical_target": "workspace://project-1/module-state/agent.http-server",
        "ownership_sensitive": True,
        "requested_at": "2026-07-28T00:00:00+00:00",
    }
    evidence = {
        "request": {
            "operation_id": request["operation_id"],
            "canonical_target": request["canonical_target"],
        },
        "registry": [_item("registry:agent.http-server", "current_registry", "registered participant")],
        "lifecycle": [_item("receipt:agent.http-server", "runtime_receipt", "owner active")],
        "canonical_state": [_item("state:http", "current_source", "runtime registry state")],
        "owner_declarations": [_item("owner:app.launcher", "current_declaration", "owner=app.launcher")],
        "mutation_sites": [_item("mutation:launcher", "current_source", "mutator=app.launcher capability=module.state.write")],
        "call_paths": [_item("call:launcher-http", "current_source", "app.launcher -> agent.http-server")],
        "persistence": [_item("persistence:registry", "current_source", "in-memory runtime state")],
        "runtime_confirmation": [_item("runtime:http", "runtime_receipt", "owner confirmed")],
        "contradictions": [],
    }
    inspector = AuthorityOwnershipInspector(clock=lambda: "2026-07-28T01:00:00+00:00")
    first = inspector.inspect(request=request, evidence_package=evidence)
    second = inspector.inspect(request=request, evidence_package=evidence)

    assert first["finding"] == "SINGLE_OWNER_CONFIRMED"
    assert second["finding"] == first["finding"]
    assert second["summary"] == first["summary"]
    assert second["evidence_refs"] == first["evidence_refs"]
    assert first["pass_fail_authorized"] is False
    assert "PASS" not in first and "FAIL" not in first
    assert all(
        ref.startswith(("registry:", "receipt:", "state:", "owner:", "mutation:", "call:", "persistence:", "runtime:"))
        for ref in first["evidence_refs"]
    )

    correlation = memory.correlate_registry_receipt(
        module_id="agent.http-server",
        receipt_sequence=runtime.watcher.history[-1].sequence,
        task_id="task-1",
    )
    assert correlation["memory_evidence_stored"] is False
    runtime.request_finished()
    runtime.shutdown()
