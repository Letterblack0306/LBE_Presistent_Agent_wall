"""Trusted live-repository completion-evidence producers for C2.

The producers observe current Git state and persist their own classifications.
They run a validation command only when fixed LBE policy selects it. They do
not accept provider claims or evaluate task completion.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..memory.completion_evidence import (
    StoredCompletionEvidence,
    TaskCompletionEvidencePersistence,
)
from ..memory.context import inspect_git_state
from ..memory.models import MemoryType
from ..session_memory_runtime import SessionMemoryRuntimeBridge
from .completion_runtime import CodingCompletionRuntime
from .validation_command_policy import (
    DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG,
    ValidationCommandPolicyCatalog,
)


SOURCE_CHANGE_PRODUCER_ID = "lbe.completion.source_change.v1"
GIT_STATUS_PRODUCER_ID = "lbe.completion.git_status.v1"
FOCUSED_TEST_PRODUCER_ID = "lbe.completion.focused_test.v1"
_SOURCE_CHANGE_KIND = "source_change"
_GIT_STATUS_KIND = "git_status"
_FOCUSED_TEST_KIND = "focused_test"
_SUPPORTED_OPERATION_ID = "reasoning.inspect"


@dataclass(frozen=True)
class LiveRepositorySnapshot:
    """Trusted repository observation made at the governed task boundary."""

    branch: str
    head: str
    status_entries: tuple[str, ...]


class CompletionEvidenceProducers:
    """Emit only C2-A evidence from current bounded workspace state."""

    def __init__(
        self,
        *,
        runtime: SessionMemoryRuntimeBridge,
        validation_command_catalog: ValidationCommandPolicyCatalog = DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG,
    ) -> None:
        if not isinstance(runtime, SessionMemoryRuntimeBridge):
            raise TypeError("runtime must be SessionMemoryRuntimeBridge")
        if not isinstance(validation_command_catalog, ValidationCommandPolicyCatalog):
            raise TypeError("validation_command_catalog must be ValidationCommandPolicyCatalog")
        self._runtime = runtime
        self._persistence = TaskCompletionEvidencePersistence(runtime.store)
        self._validation_command_catalog = validation_command_catalog

    def capture_workspace_snapshot(self) -> LiveRepositorySnapshot:
        """Capture the bounded workspace state before governed task execution."""
        state = _live_git_state(self._runtime.workspace_root)
        return LiveRepositorySnapshot(
            branch=state["branch"],
            head=state["head"],
            status_entries=tuple(state["status_entries"]),
        )

    def produce_source_change(
        self,
        *,
        task_id: str,
        operation_id: str,
        baseline: LiveRepositorySnapshot,
    ) -> StoredCompletionEvidence:
        self._require_declared_requirement(
            task_id=task_id,
            operation_id=operation_id,
            evidence_kind=_SOURCE_CHANGE_KIND,
        )
        state = _live_git_state(self._runtime.workspace_root)
        receipt = self._executed_replace_receipt(task_id=task_id, operation_id=operation_id)
        task_status_entries: tuple[str, ...] = ()
        details: dict[str, Any] = {
            **state,
            "baseline": {
                "branch": baseline.branch,
                "head": baseline.head,
                "status_entries": list(baseline.status_entries),
            },
        }
        if receipt is None:
            status = "FAIL"
            reason = "No successful task-bound workspace.replace_text receipt exists."
        else:
            path, before_hash, after_hash, receipt_details = receipt
            target = (self._runtime.workspace_root / path).resolve()
            try:
                target.relative_to(self._runtime.workspace_root.resolve())
            except ValueError:
                status = "FAIL"
                reason = "Governed mutation receipt path escapes the current workspace."
                live_hash = None
            else:
                live_hash = _sha256_path(target) if target.is_file() else None
                task_status_entries = tuple(
                    entry for entry in state["status_entries"] if _changed_path(entry) == path
                )
                if live_hash == after_hash:
                    status = "PASS"
                    reason = "Current file hash matches the successful task-bound workspace.replace_text receipt."
                else:
                    status = "STALE"
                    reason = "Current file is missing or no longer matches the successful task-bound workspace.replace_text receipt."
            details.update({
                "tool_receipt_memory_id": receipt_details["memory_id"],
                "tool_operation_id": receipt_details["operation_id"],
                "receipt_path": path,
                "before_sha256": before_hash,
                "after_sha256": after_hash,
                "live_after_sha256": live_hash,
                "replacement_count": receipt_details["replacement_count"],
            })
        details.update({
            "task_status_entries": list(task_status_entries),
            "task_changed_paths": [_changed_path(entry) for entry in task_status_entries],
            "classification_reason": reason,
        })
        return self._persist(
            task_id=task_id,
            operation_id=operation_id,
            kind=_SOURCE_CHANGE_KIND,
            status=status,
            producer_id=SOURCE_CHANGE_PRODUCER_ID,
            details=details,
        )

    def produce_git_status(
        self,
        *,
        task_id: str,
        operation_id: str,
    ) -> StoredCompletionEvidence:
        self._require_declared_requirement(
            task_id=task_id,
            operation_id=operation_id,
            evidence_kind=_GIT_STATUS_KIND,
        )
        state = _live_git_state(self._runtime.workspace_root)
        source_change = self._latest_source_change_pass(
            task_id=task_id,
            operation_id=operation_id,
        )
        if source_change is None:
            status = "FAIL"
            reason = "No passing task-bound source_change evidence exists to reconcile."
            expected_entries: tuple[str, ...] = ()
            unexpected_entries = state["status_entries"]
        else:
            expected_entries = tuple(source_change.details.get("task_status_entries", ()))
            observed_entries = state["status_entries"]
            unexpected_entries = tuple(sorted(set(observed_entries) - set(expected_entries)))
            missing_entries = tuple(sorted(set(expected_entries) - set(observed_entries)))
            if unexpected_entries:
                status = "FAIL"
                reason = "Current live repository state contains unaccounted-for changes."
            elif missing_entries or state["head"] != source_change.details.get("head"):
                status = "STALE"
                reason = "Current live repository state no longer matches the task-bound source snapshot."
            else:
                status = "PASS"
                reason = "Current live Git state matches the task-bound source snapshot."
        details = {
            **state,
            "expected_source_evidence_id": source_change.evidence_id if source_change else None,
            "expected_status_entries": list(expected_entries),
            "observed_status_entries": list(state["status_entries"]),
            "unexpected_status_entries": list(unexpected_entries),
            "classification_reason": reason,
        }
        return self._persist(
            task_id=task_id,
            operation_id=operation_id,
            kind=_GIT_STATUS_KIND,
            status=status,
            producer_id=GIT_STATUS_PRODUCER_ID,
            details=details,
        )

    def produce_focused_test(
        self,
        *,
        task_id: str,
        operation_id: str,
    ) -> StoredCompletionEvidence:
        """Run only the policy-selected validation command for this contract."""
        self._require_declared_requirement(
            task_id=task_id,
            operation_id=operation_id,
            evidence_kind=_FOCUSED_TEST_KIND,
        )
        policy = self._validation_command_catalog.find(
            operation_id=operation_id,
            mode=self._runtime.session_state.mode,
            evidence_kind=_FOCUSED_TEST_KIND,
        )
        if policy is None:
            raise ValueError("no LBE validation command policy applies to focused_test")
        state_before = _live_git_state(self._runtime.workspace_root)
        try:
            completed = _run_validation_command(
                command=policy.command,
                workspace_root=self._runtime.workspace_root,
                timeout_seconds=policy.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            status = "FAIL"
            exit_code: int | None = None
            stdout = _text(error.stdout)
            stderr = _text(error.stderr)
            reason = "The registered focused validation command exceeded its policy timeout."
        else:
            status = "PASS" if completed.returncode == 0 else "FAIL"
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            reason = (
                "The registered focused validation command completed successfully."
                if status == "PASS"
                else "The registered focused validation command failed."
            )
        details = {
            "validation_policy_id": policy.policy_id,
            "command": list(policy.command),
            "timeout_seconds": policy.timeout_seconds,
            "workspace_state_before": state_before,
            "workspace_state_after": _live_git_state(self._runtime.workspace_root),
            "exit_code": exit_code,
            "stdout_sha256": _sha256_text(stdout),
            "stderr_sha256": _sha256_text(stderr),
            "classification_reason": reason,
        }
        return self._persist(
            task_id=task_id,
            operation_id=operation_id,
            kind=_FOCUSED_TEST_KIND,
            status=status,
            producer_id=FOCUSED_TEST_PRODUCER_ID,
            details=details,
        )

    def _require_declared_requirement(
        self,
        *,
        task_id: str,
        operation_id: str,
        evidence_kind: str,
    ) -> None:
        if operation_id != _SUPPORTED_OPERATION_ID:
            raise ValueError("completion evidence producer operation is not supported")
        contract = CodingCompletionRuntime(runtime=self._runtime).load_contract(task_id=task_id)
        if contract is None or evidence_kind not in {
            item.evidence_kind for item in contract.requirements
        }:
            raise ValueError("completion evidence kind is not declared by the persisted task contract")

    def _latest_source_change_pass(
        self,
        *,
        task_id: str,
        operation_id: str,
    ) -> StoredCompletionEvidence | None:
        records = self._persistence.load(
            session_id=self._runtime.session_id,
            task_id=task_id,
            project_workspace_id=self._runtime.project_workspace_id,
        )
        for record in reversed(records):
            if (
                record.kind == _SOURCE_CHANGE_KIND
                and record.status == "PASS"
                and record.producer_id == SOURCE_CHANGE_PRODUCER_ID
                and record.operation_id == operation_id
            ):
                return record
        return None

    def _executed_replace_receipt(
        self, *, task_id: str, operation_id: str
    ) -> tuple[str, str, str, dict[str, Any]] | None:
        records = self._runtime.store.query(
            project_workspace_id=self._runtime.project_workspace_id,
            task_id=task_id,
            memory_types=(MemoryType.VALIDATION_RESULT,),
        )
        for record in records:
            if record.subject != "workspace.replace_text" or record.predicate != "tool_result":
                continue
            value = record.value if isinstance(record.value, dict) else {}
            result = value.get("result") if isinstance(value.get("result"), dict) else {}
            output = result.get("output") if isinstance(result.get("output"), dict) else {}
            receipt_operation_id = result.get("operation_id")
            if (
                value.get("success") is not True
                or result.get("status") != "executed"
                or not isinstance(receipt_operation_id, str)
                or not receipt_operation_id.startswith(f"{operation_id}:")
            ):
                continue
            path = output.get("path")
            before_hash = output.get("before_sha256")
            after_hash = output.get("after_sha256")
            replacement_count = output.get("replacement_count")
            if (
                not isinstance(path, str)
                or not isinstance(before_hash, str)
                or not isinstance(after_hash, str)
                or replacement_count != 1
            ):
                continue
            return path, before_hash, after_hash, {
                "memory_id": record.memory_id,
                "operation_id": receipt_operation_id,
                "replacement_count": replacement_count,
            }
        return None

    def _persist(
        self,
        *,
        task_id: str,
        operation_id: str,
        kind: str,
        status: str,
        producer_id: str,
        details: dict[str, Any],
    ) -> StoredCompletionEvidence:
        evidence_id = _evidence_id(
            task_id=task_id,
            operation_id=operation_id,
            kind=kind,
            status=status,
            producer_id=producer_id,
            details=details,
        )
        return self._persistence.save(
            session_id=self._runtime.session_id,
            task_id=task_id,
            project_workspace_id=self._runtime.project_workspace_id,
            canonical_workspace_root=str(self._runtime.workspace_root),
            evidence_id=evidence_id,
            kind=kind,
            status=status,
            source="lbe.live_repository",
            producer_id=producer_id,
            operation_id=operation_id,
            details=details,
        )


def _live_git_state(workspace_root: object) -> dict[str, Any]:
    state = inspect_git_state(workspace_root)
    entries = tuple(sorted(str(item) for item in state.get("status_short", ())))
    return {
        "branch": str(state.get("branch") or ""),
        "head": str(state.get("head") or ""),
        "status_entries": list(entries),
        "changed_paths": [_changed_path(entry) for entry in entries],
    }


def _changed_path(entry: str) -> str:
    if len(entry) > 2 and entry[1] == " ":
        value = entry[2:].strip()
    elif len(entry) > 3 and entry[2] == " ":
        value = entry[3:].strip()
    else:
        value = entry.strip()
    return value.rsplit(" -> ", 1)[-1].strip()


def _require_snapshot(value: object) -> None:
    if not isinstance(value, LiveRepositorySnapshot):
        raise TypeError("baseline must be a LiveRepositorySnapshot")


def _evidence_id(
    *,
    task_id: str,
    operation_id: str,
    kind: str,
    status: str,
    producer_id: str,
    details: dict[str, Any],
) -> str:
    payload = json.dumps(
        {
            "task_id": task_id,
            "operation_id": operation_id,
            "kind": kind,
            "status": status,
            "producer_id": producer_id,
            "details": details,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"evidence-{kind}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_validation_command(
    *,
    command: tuple[str, ...],
    workspace_root: object,
    timeout_seconds: float,
) -> subprocess.CompletedProcess[str]:
    """Execute a command already selected by fixed LBE validation policy."""
    return subprocess.run(
        command,
        cwd=workspace_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
