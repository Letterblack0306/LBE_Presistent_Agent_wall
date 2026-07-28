from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .module_registry import (
    ModuleDeclaration,
    ModuleRegistry,
    ModuleState,
    ModuleType,
    ModuleWatcher,
)


_RUNTIME_DECLARATIONS = (
    ModuleDeclaration(
        id="app.launcher",
        path="lbe_guard_inspector/server.py",
        type=ModuleType.CONTROLLER,
        purpose="Creates the evidence service, guard inspector, guard runner, and HTTP server.",
        provides=("app.start", "app.stop"),
        loaded_by="process.entrypoint",
        expected_profiles=("production", "test"),
    ),
    ModuleDeclaration(
        id="agent.http-server",
        path="lbe_guard_inspector/server.py",
        type=ModuleType.SERVICE,
        purpose="Exposes read-only evidence, guard execution, health, and registry endpoints.",
        provides=("http.health", "http.evidence", "http.guard-run", "module.query"),
        depends_on=("evidence.service", "guard.inspector", "guard.runner", "module.registry"),
        loaded_by="app.launcher",
        expected_profiles=("production", "test"),
    ),
    ModuleDeclaration(
        id="evidence.service",
        path="lbe_guard_inspector/evidence_service.py",
        type=ModuleType.SERVICE,
        purpose="Builds bounded evidence packages from current workspace and indexed evidence.",
        provides=("evidence.build",),
        loaded_by="app.launcher",
        expected_profiles=("production", "test"),
    ),
    ModuleDeclaration(
        id="guard.inspector",
        path="lbe_guard_inspector/guard_inspector.py",
        type=ModuleType.SERVICE,
        purpose="Maps deterministic rule results and evidence into evidence-bound guard verdicts.",
        provides=("guard.evaluate",),
        depends_on=("evidence.service",),
        loaded_by="app.launcher",
        expected_profiles=("production", "test"),
    ),
    ModuleDeclaration(
        id="guard.runner",
        path="lbe_guard_inspector/guard_runner.py",
        type=ModuleType.CONTROLLER,
        purpose="Selects and executes deterministic guards, then requests an evidence-bound verdict.",
        provides=("guard.run",),
        depends_on=("evidence.service", "guard.inspector"),
        loaded_by="app.launcher",
        expected_profiles=("production", "test"),
    ),
)


class RuntimeSlice:
    """Small, explicit runtime slice for registry-first inspection.

    This is intentionally limited to the executable Python service in this
    repository. It does not claim that unrelated browser-agent modules exist.
    """

    def __init__(self, *, active_profile: str = "production") -> None:
        self.watcher = ModuleWatcher(history_limit=200, failure_limit=50)
        self.registry = ModuleRegistry(
            active_profile=active_profile,
            watcher=self.watcher,
        )
        self.registry.register_registry_layer(load=False)
        for declaration in _RUNTIME_DECLARATIONS:
            self.registry.register(declaration)

    def startup(self) -> None:
        """Emit deterministic load/start receipts for the real startup path."""
        startup_order = (
            "module.registry",
            "module.watcher",
            "app.launcher",
            "evidence.service",
            "guard.inspector",
            "guard.runner",
            "agent.http-server",
        )
        for module_id in startup_order:
            self.registry.loaded(module_id, instance_id=f"{module_id}:primary")
        self.registry.started("app.launcher")
        self.registry.activity(
            "app.launcher",
            action="initialize-runtime",
            detail="Created registered evidence and guard service dependencies.",
        )
        self.registry.started("agent.http-server")
        self.registry.activity(
            "agent.http-server",
            action="listen",
            detail="HTTP server is ready to accept read-only requests.",
        )

    def request_started(self, route: str) -> None:
        self.registry.activity(
            "agent.http-server",
            action="request",
            detail=route,
        )

    def request_finished(self) -> None:
        self.registry.idle("agent.http-server")

    def request_failed(self, *, code: str, error: str) -> None:
        self.registry.failed("agent.http-server", code=code, error=error)

    def shutdown(self) -> None:
        self.registry.stopped("agent.http-server", reason="server shutdown")
        self.registry.stopped("app.launcher", reason="application shutdown")

    def snapshot(self) -> dict[str, Any]:
        modules = []
        for record in self.registry.list():
            modules.append(
                {
                    "id": record.declaration.id,
                    "path": record.declaration.path,
                    "type": record.declaration.type.value,
                    "purpose": record.declaration.purpose,
                    "provides": list(record.declaration.provides),
                    "depends_on": list(record.declaration.depends_on),
                    "loaded_by": record.declaration.loaded_by,
                    "expected_profiles": list(record.declaration.expected_profiles),
                    "state": record.state.value,
                    "loaded": record.loaded,
                    "running": record.running,
                    "healthy": record.healthy,
                    "instances": sorted(record.instances),
                    "current_activity": (
                        asdict(record.current_activity)
                        if record.current_activity is not None
                        else None
                    ),
                    "updated_at": record.updated_at,
                }
            )
        defects = [
            {
                "code": defect.code.value,
                "module_id": defect.module_id,
                "blocking": defect.blocking,
                "evidence": list(defect.evidence),
            }
            for defect in self.registry.defects()
        ]
        events = [
            {
                "sequence": event.sequence,
                "event_type": event.event_type.value,
                "module_id": event.module_id,
            }
            for event in self.watcher.history
        ]
        return {
            "profile": self.registry.active_profile,
            "modules": modules,
            "defects": defects,
            "events": events,
            "watcher_failures": [asdict(failure) for failure in self.watcher.failures],
        }

    def state(self, module_id: str) -> ModuleState:
        return self.registry.get(module_id).state
