from lbe_guard_inspector.module_registry import ModuleState, RegistryDefectCode
from lbe_guard_inspector.runtime_slice import RuntimeSlice


def test_startup_declares_and_loads_real_runtime_modules() -> None:
    runtime = RuntimeSlice(active_profile="test")

    before = {record.declaration.id: record.state for record in runtime.registry.list()}
    assert before["agent.http-server"] is ModuleState.REGISTERED
    assert before["module.registry"] is ModuleState.REGISTERED

    runtime.startup()

    assert runtime.state("app.launcher") is ModuleState.RUNNING
    assert runtime.state("agent.http-server") is ModuleState.RUNNING
    assert runtime.state("evidence.service") is ModuleState.LOADED
    assert runtime.state("guard.inspector") is ModuleState.LOADED
    assert runtime.state("guard.runner") is ModuleState.LOADED
    assert runtime.registry.defects() == []


def test_watcher_exposes_startup_chain_in_deterministic_order() -> None:
    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()

    events = [
        (event.event_type.value, event.module_id)
        for event in runtime.watcher.history
    ]

    assert events[:7] == [
        ("registered", "module.registry"),
        ("registered", "module.watcher"),
        ("registered", "app.launcher"),
        ("registered", "agent.http-server"),
        ("registered", "evidence.service"),
        ("registered", "guard.inspector"),
        ("registered", "guard.runner"),
    ]
    assert ("activity", "app.launcher") in events
    assert ("activity", "agent.http-server") in events


def test_request_and_shutdown_lifecycle_are_visible() -> None:
    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()

    runtime.request_started("POST /guard-run")
    assert runtime.state("agent.http-server") is ModuleState.RUNNING
    assert runtime.registry.get("agent.http-server").current_activity.detail == "POST /guard-run"

    runtime.request_finished()
    assert runtime.state("agent.http-server") is ModuleState.IDLE

    runtime.shutdown()
    assert runtime.state("agent.http-server") is ModuleState.STOPPED
    assert runtime.state("app.launcher") is ModuleState.STOPPED


def test_snapshot_is_read_only_serializable_registry_evidence() -> None:
    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()

    snapshot = runtime.snapshot()

    assert snapshot["profile"] == "test"
    assert snapshot["defects"] == []
    assert snapshot["watcher_failures"] == []
    module = next(item for item in snapshot["modules"] if item["id"] == "agent.http-server")
    assert module["state"] == "RUNNING"
    assert "module.query" in module["provides"]
    assert module["loaded_by"] == "app.launcher"
    assert snapshot["events"][-1]["module_id"] == "agent.http-server"


def test_missing_expected_module_remains_a_structured_defect() -> None:
    runtime = RuntimeSlice(active_profile="test")

    codes = {defect.code for defect in runtime.registry.defects()}

    assert RegistryDefectCode.EXPECTED_MODULE_NOT_LOADED in codes
