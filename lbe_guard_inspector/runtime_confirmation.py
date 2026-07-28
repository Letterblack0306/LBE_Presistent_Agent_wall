from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .module_registry import LifecycleReceipt, ModuleWatcher, ReceiptType


class RuntimeObservationStatus(str, Enum):
    CONFIRMED = "confirmed"
    UNAVAILABLE = "unavailable"
    UNSAFE = "unsafe"


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    operation_id: str
    module_id: str
    status: RuntimeObservationStatus
    observed_at: str | None
    provenance: str
    receipts: tuple[dict[str, Any], ...]
    detail: str


class RuntimeConfirmationAdapter:
    """Read-only, bounded observation over existing ModuleWatcher receipts.

    The adapter never starts modules, executes callbacks, persists state, or
    mutates watcher history. Exact operation identity is supplied by the caller
    and correlated only with the requested module's already-recorded receipts.
    """

    def __init__(
        self,
        watcher: ModuleWatcher | None,
        *,
        provenance: str = "module.watcher.history",
        max_receipts: int = 20,
    ) -> None:
        if max_receipts < 1:
            raise ValueError("max_receipts must be at least 1")
        self._watcher = watcher
        self._provenance = provenance.strip()
        self._max_receipts = max_receipts

    def observe(
        self,
        *,
        operation_id: str,
        module_id: str,
        safe_to_observe: bool = True,
        require_persistence_activity: bool = False,
    ) -> RuntimeObservation:
        clean_operation = operation_id.strip()
        clean_module = module_id.strip()
        if not clean_operation:
            raise ValueError("operation_id must not be empty")
        if not clean_module:
            raise ValueError("module_id must not be empty")
        if not safe_to_observe:
            return RuntimeObservation(
                operation_id=clean_operation,
                module_id=clean_module,
                status=RuntimeObservationStatus.UNSAFE,
                observed_at=None,
                provenance=self._provenance,
                receipts=(),
                detail="Runtime observation was explicitly marked unsafe.",
            )
        if self._watcher is None:
            return RuntimeObservation(
                operation_id=clean_operation,
                module_id=clean_module,
                status=RuntimeObservationStatus.UNAVAILABLE,
                observed_at=None,
                provenance=self._provenance,
                receipts=(),
                detail="Runtime watcher is unavailable.",
            )

        matching = [
            event
            for event in self._watcher.history
            if event.module_id == clean_module
            and event.event_type is not ReceiptType.REGISTERED
        ][-self._max_receipts :]
        receipts = tuple(self._serialize(event.payload) for event in matching)
        observed_at = receipts[-1]["timestamp"] if receipts else None
        if not receipts:
            return RuntimeObservation(
                operation_id=clean_operation,
                module_id=clean_module,
                status=RuntimeObservationStatus.UNAVAILABLE,
                observed_at=None,
                provenance=self._provenance,
                receipts=(),
                detail="No lifecycle receipts were observed for the requested module.",
            )

        if require_persistence_activity:
            persistence_receipts = tuple(
                receipt
                for receipt in receipts
                if receipt["type"] == ReceiptType.ACTIVITY.value
                and "persist" in (
                    f"{receipt.get('action', '')} {receipt.get('detail', '')}"
                ).lower()
            )
            if not persistence_receipts:
                return RuntimeObservation(
                    operation_id=clean_operation,
                    module_id=clean_module,
                    status=RuntimeObservationStatus.UNAVAILABLE,
                    observed_at=observed_at,
                    provenance=self._provenance,
                    receipts=receipts,
                    detail="Lifecycle receipts exist, but active persistence was not observed.",
                )

        return RuntimeObservation(
            operation_id=clean_operation,
            module_id=clean_module,
            status=RuntimeObservationStatus.CONFIRMED,
            observed_at=observed_at,
            provenance=self._provenance,
            receipts=receipts,
            detail="Existing runtime receipts confirm the requested module observation.",
        )

    @staticmethod
    def _serialize(receipt: LifecycleReceipt) -> dict[str, Any]:
        return {
            "operation_id": None,
            "module_id": receipt.module_id,
            "type": receipt.type.value,
            "timestamp": receipt.timestamp,
            "instance_id": receipt.instance_id,
            "action": receipt.action,
            "detail": receipt.detail,
            "reason": receipt.reason,
            "code": receipt.code,
            "error": receipt.error,
        }
