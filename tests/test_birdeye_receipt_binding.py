"""BirdEye receipt binding must preserve LBE completion authority."""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from lbe_guard_inspector.runtime.completion_runtime import CodingCompletionRuntime
from lbe_guard_inspector.runtime.completion_gate import CompletionVerdict, evaluate_completion
from lbe_guard_inspector.runtime.task_completion_policy import DEFAULT_TASK_COMPLETION_POLICY_CATALOG
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


def _runtime(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1", workspace_root=root,
        session_id="session-1", mode="coding",
        permission="write_allowed", runtime_policy="permissive",
    )
    policy = DEFAULT_TASK_COMPLETION_POLICY_CATALOG.find(
        operation_id="reasoning.inspect", task_class="coding_fix", mode="coding"
    )
    coordinator = CodingCompletionRuntime(runtime=runtime)
    coordinator.persist_contract(task_id="task-1", contract=policy.contract())
    return coordinator


def _receipt(tmp_path, *, task_id="task-1", requirement_id="focused-tests"):
    execution_id = "bird-test-abc"
    root = tmp_path / "state" / "executions" / execution_id
    root.mkdir(parents=True)
    path = root / "receipt.json"
    data = {
        "task_id": task_id, "requirement_id": requirement_id,
        "execution_id": execution_id, "workspace": "test",
        "execution_evidence_sha256": "a" * 64, "exit_code": 0,
    }
    data["receipt_sha256"] = hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf8")
    ).hexdigest()
    path.write_text(json.dumps(data), encoding="utf8")
    return path


def test_valid_receipt_is_durable_but_not_completion_pass(tmp_path):
    runtime = _runtime(tmp_path)
    record = runtime.bind_birdeye_receipt(
        task_id="task-1", requirement_id="focused-tests",
        receipt_path=str(_receipt(tmp_path))
    )
    assert record.status == "STALE"
    assert record.details["requirement_id"] == "focused-tests"
    assert runtime.load_evidence(task_id="task-1")[0].status.value == "STALE"
    decision = evaluate_completion(contract=runtime.load_contract(task_id="task-1"), evidence=runtime.load_evidence(task_id="task-1"), claimed_complete=True)
    assert decision.verdict is not CompletionVerdict.READY


def test_tampering_and_mismatched_requirement_fail_closed(tmp_path):
    runtime = _runtime(tmp_path)
    path = _receipt(tmp_path)
    data = json.loads(path.read_text(encoding="utf8"))
    data["exit_code"] = 9
    path.write_text(json.dumps(data), encoding="utf8")
    with pytest.raises(ValueError, match="hash verification"):
        runtime.bind_birdeye_receipt(task_id="task-1", requirement_id="focused-tests", receipt_path=str(path))
    with pytest.raises(ValueError, match="not declared"):
        runtime.bind_birdeye_receipt(task_id="task-1", requirement_id="unknown", receipt_path=str(path))
