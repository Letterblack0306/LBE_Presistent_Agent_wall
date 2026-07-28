from __future__ import annotations

from lbe_guard_inspector.module_registry import LifecycleReceipt, ModuleWatcher, ReceiptType
from lbe_guard_inspector.runtime_confirmation import (
    RuntimeConfirmationAdapter,
    RuntimeObservationStatus,
)


def receipt(
    module_id: str,
    receipt_type: ReceiptType,
    timestamp: str,
    *,
    action: str | None = None,
    detail: str | None = None,
) -> LifecycleReceipt:
    return LifecycleReceipt(
        module_id=module_id,
        type=receipt_type,
        timestamp=timestamp,
        instance_id="instance-1" if receipt_type is ReceiptType.LOADED else None,
        action=action,
        detail=detail,
    )


def test_confirms_existing_lifecycle_with_exact_operation_and_module_identity() -> None:
    watcher = ModuleWatcher()
    watcher.publish_receipt(
        receipt("module.registry", ReceiptType.LOADED, "2026-07-28T00:00:00+00:00")
    )
    watcher.publish_receipt(
        receipt("module.registry", ReceiptType.STARTED, "2026-07-28T00:00:01+00:00")
    )

    result = RuntimeConfirmationAdapter(watcher).observe(
        operation_id="workspace.module-state.update",
        module_id="module.registry",
    )

    assert result.status is RuntimeObservationStatus.CONFIRMED
    assert result.operation_id == "workspace.module-state.update"
    assert result.module_id == "module.registry"
    assert result.observed_at == "2026-07-28T00:00:01+00:00"
    assert all(
        item["operation_id"] == "workspace.module-state.update"
        for item in result.receipts
    )
    assert all(item["module_id"] == "module.registry" for item in result.receipts)
    assert result.provenance == "module.watcher.history"


def test_observation_window_is_bounded_to_latest_receipts() -> None:
    watcher = ModuleWatcher()
    for index in range(5):
        watcher.publish_receipt(
            receipt(
                "module.registry",
                ReceiptType.ACTIVITY,
                f"2026-07-28T00:00:0{index}+00:00",
                action="state.update",
                detail=f"update {index}",
            )
        )

    result = RuntimeConfirmationAdapter(watcher, max_receipts=2).observe(
        operation_id="workspace.module-state.update",
        module_id="module.registry",
    )

    assert len(result.receipts) == 2
    assert result.receipts[0]["detail"] == "update 3"
    assert result.receipts[1]["detail"] == "update 4"


def test_active_persistence_can_be_confirmed_when_observed() -> None:
    watcher = ModuleWatcher()
    watcher.publish_receipt(
        receipt(
            "module.registry",
            ReceiptType.ACTIVITY,
            "2026-07-28T00:00:02+00:00",
            action="persist state",
            detail="persist .lbe/module-registry.json",
        )
    )

    result = RuntimeConfirmationAdapter(watcher).observe(
        operation_id="workspace.module-state.update",
        module_id="module.registry",
        require_persistence_activity=True,
    )

    assert result.status is RuntimeObservationStatus.CONFIRMED


def test_missing_persistence_receipt_is_unavailable_not_guessed() -> None:
    watcher = ModuleWatcher()
    watcher.publish_receipt(
        receipt(
            "module.registry",
            ReceiptType.ACTIVITY,
            "2026-07-28T00:00:02+00:00",
            action="state update",
            detail="in-memory update",
        )
    )

    result = RuntimeConfirmationAdapter(watcher).observe(
        operation_id="workspace.module-state.update",
        module_id="module.registry",
        require_persistence_activity=True,
    )

    assert result.status is RuntimeObservationStatus.UNAVAILABLE
    assert "not observed" in result.detail


def test_unavailable_watcher_is_explicit() -> None:
    result = RuntimeConfirmationAdapter(None).observe(
        operation_id="workspace.module-state.update",
        module_id="module.registry",
    )

    assert result.status is RuntimeObservationStatus.UNAVAILABLE
    assert result.receipts == ()


def test_unsafe_observation_does_not_read_history() -> None:
    watcher = ModuleWatcher()
    watcher.publish_receipt(
        receipt("module.registry", ReceiptType.STARTED, "2026-07-28T00:00:00+00:00")
    )
    before = watcher.history

    result = RuntimeConfirmationAdapter(watcher).observe(
        operation_id="workspace.module-state.update",
        module_id="module.registry",
        safe_to_observe=False,
    )

    assert result.status is RuntimeObservationStatus.UNSAFE
    assert result.receipts == ()
    assert watcher.history == before


def test_other_module_receipts_are_not_mixed_into_observation() -> None:
    watcher = ModuleWatcher()
    watcher.publish_receipt(
        receipt("module.watcher", ReceiptType.STARTED, "2026-07-28T00:00:00+00:00")
    )

    result = RuntimeConfirmationAdapter(watcher).observe(
        operation_id="workspace.module-state.update",
        module_id="module.registry",
    )

    assert result.status is RuntimeObservationStatus.UNAVAILABLE
    assert result.receipts == ()


def test_adapter_never_mutates_watcher_history() -> None:
    watcher = ModuleWatcher()
    watcher.publish_receipt(
        receipt("module.registry", ReceiptType.STARTED, "2026-07-28T00:00:00+00:00")
    )
    before = watcher.history

    RuntimeConfirmationAdapter(watcher).observe(
        operation_id="workspace.module-state.update",
        module_id="module.registry",
    )

    assert watcher.history == before
