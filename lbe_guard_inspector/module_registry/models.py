from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Iterable


class ModuleType(StrEnum):
    SERVICE = "service"
    CONTROLLER = "controller"
    PROVIDER = "provider"
    ADAPTER = "adapter"
    UI = "ui"
    REGISTRY = "registry"
    TOOL = "tool"
    STORE = "store"


class ModuleState(StrEnum):
    REGISTERED = "REGISTERED"
    NOT_LOADED = "NOT_LOADED"
    LOADED = "LOADED"
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    DISABLED = "DISABLED"


class ReceiptType(StrEnum):
    REGISTERED = "registered"
    LOADED = "loaded"
    STARTED = "started"
    ACTIVITY = "activity"
    STOPPED = "stopped"
    FAILED = "failed"


class RegistryDefectCode(StrEnum):
    MODULE_UNREGISTERED = "MODULE_UNREGISTERED"
    REGISTERED_NOT_LOADED = "REGISTERED_NOT_LOADED"
    EXPECTED_MODULE_NOT_LOADED = "EXPECTED_MODULE_NOT_LOADED"
    MODULE_DEPENDENCY_UNREGISTERED = "MODULE_DEPENDENCY_UNREGISTERED"
    MODULE_INSTANCE_CONFLICT = "MODULE_INSTANCE_CONFLICT"
    DISABLED_MODULE_LOADED = "DISABLED_MODULE_LOADED"
    RECEIPT_FOR_UNKNOWN_MODULE = "RECEIPT_FOR_UNKNOWN_MODULE"
    INVALID_LOADER_RELATIONSHIP = "INVALID_LOADER_RELATIONSHIP"
    CONTRADICTORY_LIFECYCLE_STATE = "CONTRADICTORY_LIFECYCLE_STATE"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: str, name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} must not be empty")
    return cleaned


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_clean(value, "list value") for value in values))


@dataclass(frozen=True, slots=True)
class ModuleDeclaration:
    id: str
    path: str
    type: ModuleType
    purpose: str
    provides: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    loaded_by: str = "process.entrypoint"
    expected_profiles: tuple[str, ...] = ("production",)
    singleton: bool = True
    disabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _clean(self.id, "id"))
        object.__setattr__(self, "path", _clean(self.path, "path").replace("\\", "/"))
        object.__setattr__(self, "purpose", _clean(self.purpose, "purpose"))
        object.__setattr__(self, "loaded_by", _clean(self.loaded_by, "loaded_by"))
        object.__setattr__(self, "provides", _unique(self.provides))
        object.__setattr__(self, "depends_on", _unique(self.depends_on))
        object.__setattr__(self, "expected_profiles", _unique(self.expected_profiles))
        if not isinstance(self.type, ModuleType):
            object.__setattr__(self, "type", ModuleType(self.type))


@dataclass(frozen=True, slots=True)
class ModuleActivity:
    action: str
    detail: str
    started_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", _clean(self.action, "action"))
        object.__setattr__(self, "detail", _clean(self.detail, "detail"))
        object.__setattr__(self, "started_at", _clean(self.started_at, "started_at"))


@dataclass(frozen=True, slots=True)
class LifecycleReceipt:
    module_id: str
    type: ReceiptType
    timestamp: str
    instance_id: str | None = None
    action: str | None = None
    detail: str | None = None
    reason: str | None = None
    code: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _clean(self.module_id, "module_id"))
        object.__setattr__(self, "timestamp", _clean(self.timestamp, "timestamp"))
        if not isinstance(self.type, ReceiptType):
            object.__setattr__(self, "type", ReceiptType(self.type))
        if self.type is ReceiptType.LOADED and not self.instance_id:
            raise ValueError("loaded receipt requires instance_id")
        if self.type is ReceiptType.ACTIVITY and (not self.action or not self.detail):
            raise ValueError("activity receipt requires action and detail")
        if self.type is ReceiptType.FAILED and (not self.code or not self.error):
            raise ValueError("failed receipt requires code and error")


@dataclass(frozen=True, slots=True)
class RegistryDefect:
    code: RegistryDefectCode
    module_id: str
    blocking: bool
    evidence: tuple[str, ...] = ()


@dataclass(slots=True)
class LiveModuleRecord:
    declaration: ModuleDeclaration
    state: ModuleState
    registered: bool = True
    loaded: bool = False
    running: bool = False
    healthy: bool = True
    instances: set[str] = field(default_factory=set)
    current_activity: ModuleActivity | None = None
    recent_activity: list[ModuleActivity] = field(default_factory=list)
    last_error: dict[str, str] | None = None
    loaded_at: str | None = None
    updated_at: str | None = None

    @property
    def instance_count(self) -> int:
        return len(self.instances)
