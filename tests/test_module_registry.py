from __future__ import annotations

import pytest

from lbe_guard_inspector.module_registry import (
    LifecycleReceipt,
    ModuleDeclaration,
    ModuleRegistry,
    ModuleState,
    ModuleType,
    ReceiptType,
    RegistryDefectCode,
)


class Clock:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self) -> str:
        self._value += 1
        return f"2026-07-28T00:00:{self._value:02d}+00:00"


def declaration(**overrides: object) -> ModuleDeclaration:
    values: dict[str, object] = {
        "id": "browser.loop-controller",
        "path": "src/system/LoopController.js",
        "type": ModuleType.CONTROLLER,
        "purpose": "Polls completed browser turns.",
        "provides": ("browser.loop.start",),
        "depends_on": ("browser.chat-bridge",),
        "loaded_by": "app.launcher",
        "expected_profiles": ("production", "test"),
    }
    values.update(overrides)
    return ModuleDeclaration(**values)


def registry_with_dependencies() -> ModuleRegistry:
    registry = ModuleRegistry(clock=Clock())
    registry.register(
        declaration(
            id="app.launcher",
            path="src/app/launcher.js",
            type=ModuleType.SERVICE,
            purpose="Starts the runtime.",
            provides=(),
            depends_on=(),
            loaded_by="process.entrypoint",
        )
    )
    registry.register(
        declaration(
            id="browser.chat-bridge",
            path="src/browser/ChatBridge.js",
            type=ModuleType.ADAPTER,
            purpose="Connects to the browser provider.",
            provides=(),
            depends_on=(),
            loaded_by="app.launcher",
        )
    )
    registry.register(declaration())
    return registry


def test_declaration_validation_and_normalization() -> None:
    item = declaration(
        path="src\\system\\LoopController.js",
        provides=("browser.loop.start", "browser.loop.start"),
    )
    assert item.path == "src/system/LoopController.js"
    assert item.provides == ("browser.loop.start",)
    with pytest.raises(ValueError, match="purpose"):
        declaration(purpose=" ")
    with pytest.raises(ValueError):
        declaration(type="unknown")


def test_duplicate_registration_is_rejected() -> None:
    registry = ModuleRegistry()
    registry.register(declaration(depends_on=(), loaded_by="process.entrypoint"))
    with pytest.raises(ValueError, match="duplicate module id"):
        registry.register(declaration(depends_on=(), loaded_by="process.entrypoint"))


def test_receipt_validation() -> None:
    with pytest.raises(ValueError, match="instance_id"):
        LifecycleReceipt("module", ReceiptType.LOADED, "time")
    with pytest.raises(ValueError, match="action and detail"):
        LifecycleReceipt("module", ReceiptType.ACTIVITY, "time")
    with pytest.raises(ValueError, match="code and error"):
        LifecycleReceipt("module", ReceiptType.FAILED, "time")


def test_lifecycle_state_and_error_retention() -> None:
    registry = registry_with_dependencies()
    assert registry.loaded("browser.loop-controller", instance_id="loop-1").state is ModuleState.LOADED
    assert registry.started("browser.loop-controller").state is ModuleState.RUNNING
    record = registry.activity(
        "browser.loop-controller",
        action="provider-turn.poll",
        detail="Waiting for a completed browser turn",
    )
    assert record.current_activity is not None
    assert record.current_activity.action == "provider-turn.poll"
    assert registry.idle("browser.loop-controller").state is ModuleState.IDLE
    failed = registry.failed("browser.loop-controller", code="PROVIDER_LOST", error="Disconnected")
    assert failed.state is ModuleState.FAILED
    assert failed.last_error is not None
    assert failed.last_error["code"] == "PROVIDER_LOST"


def test_activity_history_is_bounded() -> None:
    registry = ModuleRegistry(clock=Clock(), activity_limit=2)
    registry.register(declaration(depends_on=(), loaded_by="process.entrypoint"))
    registry.loaded("browser.loop-controller", instance_id="loop-1")
    for index in range(3):
        registry.activity(
            "browser.loop-controller",
            action=f"action-{index}",
            detail=f"detail-{index}",
        )
    assert [item.action for item in registry.get("browser.loop-controller").recent_activity] == [
        "action-1",
        "action-2",
    ]


def test_registry_filters_are_deterministic() -> None:
    registry = registry_with_dependencies()
    records = registry.list(
        module_type="controller",
        profile="production",
        capability="browser.loop.start",
        loader="app.launcher",
        dependency="browser.chat-bridge",
    )
    assert [record.declaration.id for record in records] == ["browser.loop-controller"]


def test_expected_missing_and_nonblocking_registered_defects() -> None:
    registry = registry_with_dependencies()
    defects = registry.defects()
    assert any(
        defect.code is RegistryDefectCode.EXPECTED_MODULE_NOT_LOADED and defect.blocking
        for defect in defects
    )

    optional = ModuleRegistry(active_profile="test")
    optional.register(
        declaration(
            expected_profiles=("production",),
            depends_on=(),
            loaded_by="process.entrypoint",
        )
    )
    defect = optional.defects()[0]
    assert defect.code is RegistryDefectCode.REGISTERED_NOT_LOADED
    assert defect.blocking is False


def test_dependency_loader_instance_disabled_and_unknown_defects() -> None:
    registry = ModuleRegistry()
    registry.register(declaration(depends_on=("missing",), loaded_by="missing.loader"))
    codes = {defect.code for defect in registry.defects()}
    assert RegistryDefectCode.MODULE_DEPENDENCY_UNREGISTERED in codes
    assert RegistryDefectCode.INVALID_LOADER_RELATIONSHIP in codes

    singleton = registry_with_dependencies()
    singleton.loaded("browser.loop-controller", instance_id="loop-1")
    singleton.loaded("browser.loop-controller", instance_id="loop-2")
    assert any(
        defect.code is RegistryDefectCode.MODULE_INSTANCE_CONFLICT
        for defect in singleton.defects()
    )

    disabled = ModuleRegistry()
    disabled.register(
        declaration(
            disabled=True,
            expected_profiles=(),
            depends_on=(),
            loaded_by="process.entrypoint",
        )
    )
    disabled.loaded("browser.loop-controller", instance_id="loop-1")
    assert any(
        defect.code is RegistryDefectCode.DISABLED_MODULE_LOADED
        for defect in disabled.defects()
    )

    unknown = ModuleRegistry(clock=Clock())
    with pytest.raises(KeyError):
        unknown.loaded("unknown", instance_id="unknown-1")
    assert unknown.defects()[0].code is RegistryDefectCode.RECEIPT_FOR_UNKNOWN_MODULE


def test_started_before_loaded_is_rejected() -> None:
    registry = ModuleRegistry(clock=Clock())
    registry.register(declaration(depends_on=(), loaded_by="process.entrypoint"))
    with pytest.raises(ValueError, match="not loaded"):
        registry.started("browser.loop-controller")
