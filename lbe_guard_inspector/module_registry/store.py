from __future__ import annotations

from collections.abc import Callable

from .models import (
    LifecycleReceipt,
    LiveModuleRecord,
    ModuleActivity,
    ModuleDeclaration,
    ModuleState,
    ModuleType,
    ReceiptType,
    RegistryDefect,
    RegistryDefectCode,
    utc_now,
)


_ALLOWED_EXTERNAL_LOADERS = {"process.entrypoint", "external.runtime"}


class ModuleRegistry:
    def __init__(
        self,
        *,
        active_profile: str = "production",
        activity_limit: int = 20,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        if activity_limit < 1:
            raise ValueError("activity_limit must be at least 1")
        self.active_profile = active_profile.strip()
        if not self.active_profile:
            raise ValueError("active_profile must not be empty")
        self._activity_limit = activity_limit
        self._clock = clock
        self._declarations: dict[str, ModuleDeclaration] = {}
        self._records: dict[str, LiveModuleRecord] = {}
        self._unknown_receipts: list[LifecycleReceipt] = []

    def register(self, declaration: ModuleDeclaration) -> LiveModuleRecord:
        if declaration.id in self._declarations:
            raise ValueError(f"duplicate module id: {declaration.id}")
        timestamp = self._clock()
        state = ModuleState.DISABLED if declaration.disabled else ModuleState.REGISTERED
        record = LiveModuleRecord(
            declaration=declaration,
            state=state,
            updated_at=timestamp,
        )
        self._declarations[declaration.id] = declaration
        self._records[declaration.id] = record
        return record

    def declaration(self, module_id: str) -> ModuleDeclaration:
        return self._declarations[module_id]

    def get(self, module_id: str) -> LiveModuleRecord:
        return self._records[module_id]

    def list(
        self,
        *,
        state: ModuleState | str | None = None,
        module_type: ModuleType | str | None = None,
        profile: str | None = None,
        capability: str | None = None,
        loader: str | None = None,
        dependency: str | None = None,
    ) -> list[LiveModuleRecord]:
        state_value = ModuleState(state) if state is not None else None
        type_value = ModuleType(module_type) if module_type is not None else None
        records = []
        for module_id in sorted(self._records):
            record = self._records[module_id]
            declaration = record.declaration
            if state_value is not None and record.state is not state_value:
                continue
            if type_value is not None and declaration.type is not type_value:
                continue
            if profile is not None and profile not in declaration.expected_profiles:
                continue
            if capability is not None and capability not in declaration.provides:
                continue
            if loader is not None and declaration.loaded_by != loader:
                continue
            if dependency is not None and dependency not in declaration.depends_on:
                continue
            records.append(record)
        return records

    def loaded(self, module_id: str, *, instance_id: str) -> LiveModuleRecord:
        return self._apply(
            LifecycleReceipt(
                module_id=module_id,
                type=ReceiptType.LOADED,
                timestamp=self._clock(),
                instance_id=instance_id,
            )
        )

    def started(self, module_id: str) -> LiveModuleRecord:
        return self._apply(
            LifecycleReceipt(module_id, ReceiptType.STARTED, self._clock())
        )

    def activity(self, module_id: str, *, action: str, detail: str) -> LiveModuleRecord:
        return self._apply(
            LifecycleReceipt(
                module_id=module_id,
                type=ReceiptType.ACTIVITY,
                timestamp=self._clock(),
                action=action,
                detail=detail,
            )
        )

    def idle(self, module_id: str) -> LiveModuleRecord:
        record = self._known_record(module_id, ReceiptType.ACTIVITY)
        if not record.loaded:
            self._contradiction(module_id, "idle-before-loaded")
            raise ValueError(f"module is not loaded: {module_id}")
        record.running = False
        record.state = ModuleState.IDLE
        record.updated_at = self._clock()
        return record

    def stopped(self, module_id: str, *, reason: str = "stopped") -> LiveModuleRecord:
        return self._apply(
            LifecycleReceipt(
                module_id=module_id,
                type=ReceiptType.STOPPED,
                timestamp=self._clock(),
                reason=reason,
            )
        )

    def failed(self, module_id: str, *, code: str, error: str) -> LiveModuleRecord:
        return self._apply(
            LifecycleReceipt(
                module_id=module_id,
                type=ReceiptType.FAILED,
                timestamp=self._clock(),
                code=code,
                error=error,
            )
        )

    def defects(self) -> list[RegistryDefect]:
        defects = [
            RegistryDefect(
                RegistryDefectCode.RECEIPT_FOR_UNKNOWN_MODULE,
                receipt.module_id,
                True,
                (receipt.type.value, receipt.timestamp),
            )
            for receipt in self._unknown_receipts
        ]
        for module_id in sorted(self._records):
            record = self._records[module_id]
            declaration = record.declaration
            for dependency in declaration.depends_on:
                if dependency not in self._declarations:
                    defects.append(
                        RegistryDefect(
                            RegistryDefectCode.MODULE_DEPENDENCY_UNREGISTERED,
                            module_id,
                            True,
                            (dependency,),
                        )
                    )
            if (
                declaration.loaded_by not in _ALLOWED_EXTERNAL_LOADERS
                and declaration.loaded_by not in self._declarations
            ):
                defects.append(
                    RegistryDefect(
                        RegistryDefectCode.INVALID_LOADER_RELATIONSHIP,
                        module_id,
                        True,
                        (declaration.loaded_by,),
                    )
                )
            if declaration.disabled and record.loaded:
                defects.append(
                    RegistryDefect(
                        RegistryDefectCode.DISABLED_MODULE_LOADED,
                        module_id,
                        True,
                        tuple(sorted(record.instances)),
                    )
                )
            expected = self.active_profile in declaration.expected_profiles
            if expected and not record.loaded and not declaration.disabled:
                defects.append(
                    RegistryDefect(
                        RegistryDefectCode.EXPECTED_MODULE_NOT_LOADED,
                        module_id,
                        True,
                        (self.active_profile,),
                    )
                )
            elif not record.loaded and not declaration.disabled:
                defects.append(
                    RegistryDefect(
                        RegistryDefectCode.REGISTERED_NOT_LOADED,
                        module_id,
                        False,
                    )
                )
            if declaration.singleton and record.instance_count > 1:
                defects.append(
                    RegistryDefect(
                        RegistryDefectCode.MODULE_INSTANCE_CONFLICT,
                        module_id,
                        True,
                        tuple(sorted(record.instances)),
                    )
                )
        return defects

    def _known_record(
        self, module_id: str, receipt_type: ReceiptType
    ) -> LiveModuleRecord:
        if module_id in self._records:
            return self._records[module_id]
        receipt = LifecycleReceipt(module_id, receipt_type, self._clock())
        self._unknown_receipts.append(receipt)
        raise KeyError(module_id)

    def _contradiction(self, module_id: str, detail: str) -> None:
        self._unknown_receipts.append(
            LifecycleReceipt(
                module_id=module_id,
                type=ReceiptType.FAILED,
                timestamp=self._clock(),
                code=RegistryDefectCode.CONTRADICTORY_LIFECYCLE_STATE.value,
                error=detail,
            )
        )

    def _apply(self, receipt: LifecycleReceipt) -> LiveModuleRecord:
        record = self._known_record(receipt.module_id, receipt.type)
        if receipt.type is ReceiptType.LOADED:
            assert receipt.instance_id is not None
            record.instances.add(receipt.instance_id)
            record.loaded = True
            record.state = ModuleState.LOADED
            record.loaded_at = record.loaded_at or receipt.timestamp
        elif receipt.type is ReceiptType.STARTED:
            if not record.loaded:
                self._contradiction(receipt.module_id, "started-before-loaded")
                raise ValueError(f"module is not loaded: {receipt.module_id}")
            record.running = True
            record.state = ModuleState.RUNNING
        elif receipt.type is ReceiptType.ACTIVITY:
            if not record.loaded:
                self._contradiction(receipt.module_id, "activity-before-loaded")
                raise ValueError(f"module is not loaded: {receipt.module_id}")
            activity = ModuleActivity(
                action=receipt.action or "",
                detail=receipt.detail or "",
                started_at=receipt.timestamp,
            )
            record.current_activity = activity
            record.recent_activity.append(activity)
            record.recent_activity[:] = record.recent_activity[-self._activity_limit :]
            record.running = True
            record.state = ModuleState.RUNNING
        elif receipt.type is ReceiptType.STOPPED:
            record.running = False
            record.current_activity = None
            record.state = ModuleState.STOPPED
        elif receipt.type is ReceiptType.FAILED:
            record.running = False
            record.healthy = False
            record.state = ModuleState.FAILED
            record.last_error = {
                "code": receipt.code or "UNKNOWN",
                "error": receipt.error or "Unknown error",
                "timestamp": receipt.timestamp,
            }
        record.updated_at = receipt.timestamp
        return record
