from __future__ import annotations

from lbe_guard_inspector.module_registry import (
    ModuleDeclaration,
    ModuleRegistry,
    ModuleType,
    ModuleWatcher,
    ReceiptType,
    WatchSubscription,
)


class Clock:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> str:
        self.value += 1
        return f"2026-07-28T00:00:{self.value:02d}+00:00"


def declaration() -> ModuleDeclaration:
    return ModuleDeclaration(
        id="browser.loop-controller",
        path="src/system/LoopController.js",
        type=ModuleType.CONTROLLER,
        purpose="Polls browser turns.",
        provides=("browser.loop.start",),
        loaded_by="process.entrypoint",
        expected_profiles=("production",),
    )


def test_watcher_receives_events_in_deterministic_order() -> None:
    watcher = ModuleWatcher()
    seen: list[str] = []
    watcher.watch(
        WatchSubscription(
            name="observer",
            on_registered=lambda item: seen.append(f"registered:{item.id}"),
            on_loaded=lambda item: seen.append(f"loaded:{item.module_id}"),
            on_started=lambda item: seen.append(f"started:{item.module_id}"),
            on_activity=lambda item: seen.append(f"activity:{item.action}"),
            on_stopped=lambda item: seen.append(f"stopped:{item.module_id}"),
            on_failed=lambda item: seen.append(f"failed:{item.code}"),
        )
    )
    registry = ModuleRegistry(clock=Clock(), watcher=watcher)
    registry.register(declaration())
    registry.loaded("browser.loop-controller", instance_id="loop-1")
    registry.started("browser.loop-controller")
    registry.activity("browser.loop-controller", action="poll", detail="waiting")
    registry.stopped("browser.loop-controller", reason="done")
    registry.failed("browser.loop-controller", code="E", error="bad")

    assert seen == [
        "registered:browser.loop-controller",
        "loaded:browser.loop-controller",
        "started:browser.loop-controller",
        "activity:poll",
        "stopped:browser.loop-controller",
        "failed:E",
    ]
    assert [event.sequence for event in watcher.history] == [1, 2, 3, 4, 5, 6]
    assert [event.event_type for event in watcher.history] == [
        ReceiptType.REGISTERED,
        ReceiptType.LOADED,
        ReceiptType.STARTED,
        ReceiptType.ACTIVITY,
        ReceiptType.STOPPED,
        ReceiptType.FAILED,
    ]


def test_failing_subscriber_is_isolated_from_registry_truth() -> None:
    watcher = ModuleWatcher()

    def fail(_payload: object) -> None:
        raise RuntimeError("subscriber failed")

    watcher.watch(WatchSubscription(name="broken", on_loaded=fail))
    registry = ModuleRegistry(clock=Clock(), watcher=watcher)
    registry.register(declaration())
    record = registry.loaded("browser.loop-controller", instance_id="loop-1")

    assert record.loaded is True
    assert record.instance_count == 1
    assert len(watcher.failures) == 1
    failure = watcher.failures[0]
    assert failure.subscriber_name == "broken"
    assert failure.error_type == "RuntimeError"
    assert failure.error == "subscriber failed"


def test_watcher_history_and_failures_are_bounded() -> None:
    watcher = ModuleWatcher(history_limit=2, failure_limit=1)

    def fail(_payload: object) -> None:
        raise ValueError("bad subscriber")

    watcher.watch(
        WatchSubscription(
            name="broken",
            on_registered=fail,
            on_loaded=fail,
            on_started=fail,
        )
    )
    registry = ModuleRegistry(clock=Clock(), watcher=watcher)
    registry.register(declaration())
    registry.loaded("browser.loop-controller", instance_id="loop-1")
    registry.started("browser.loop-controller")

    assert [event.event_type for event in watcher.history] == [
        ReceiptType.LOADED,
        ReceiptType.STARTED,
    ]
    assert len(watcher.failures) == 1
    assert watcher.failures[0].event_type is ReceiptType.STARTED


def test_registry_and_watcher_self_register() -> None:
    watcher = ModuleWatcher()
    registry = ModuleRegistry(clock=Clock(), watcher=watcher)
    registry.register_registry_layer()

    registry_record = registry.get("module.registry")
    watcher_record = registry.get("module.watcher")
    assert registry_record.loaded is True
    assert watcher_record.loaded is True
    assert watcher_record.declaration.depends_on == ("module.registry",)
    assert [event.module_id for event in watcher.history] == [
        "module.registry",
        "module.watcher",
        "module.registry",
        "module.watcher",
    ]
