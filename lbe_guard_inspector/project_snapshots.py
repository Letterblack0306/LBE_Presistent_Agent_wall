"""Generated, historical project-profile snapshots.

Snapshots are held in the inspector state directory.  They never replace or
override the current filesystem profile used for an audit.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent import STATE_DIR, write_json


class ProjectSnapshotStore:
    def __init__(self, state_dir: Path | None = None) -> None:
        self._state_dir = state_dir or STATE_DIR

    def snapshot_path(self, workspace_id: str) -> Path:
        if not workspace_id.startswith("workspace_"):
            raise ValueError("workspace_id must be a generated workspace identity")
        return self._state_dir / "workspace-intelligence" / workspace_id / "snapshot.json"

    def load(self, workspace_id: str) -> dict[str, Any] | None:
        path = self.snapshot_path(workspace_id)
        if not path.is_file():
            return None
        import json
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError(f"Snapshot must be a JSON object: {path}")
        return payload

    @staticmethod
    def compare(
        previous: dict[str, Any] | None, current: dict[str, Any]
    ) -> dict[str, Any]:
        if previous is None:
            return {
                "previous_snapshot_available": False,
                "historical_only": True,
                "added": [],
                "removed": [],
                "changed": [],
            }
        old_signals = {
            item["path"]: item["sha256"]
            for item in previous.get("signals", [])
            if isinstance(item, dict) and "path" in item and "sha256" in item
        }
        new_signals = {
            item["path"]: item["sha256"]
            for item in current.get("signals", [])
            if isinstance(item, dict) and "path" in item and "sha256" in item
        }
        return {
            "previous_snapshot_available": True,
            "historical_only": True,
            "added": sorted(set(new_signals) - set(old_signals)),
            "removed": sorted(set(old_signals) - set(new_signals)),
            "changed": sorted(
                path for path in set(old_signals) & set(new_signals)
                if old_signals[path] != new_signals[path]
            ),
        }

    def save(
        self,
        profile_snapshot: dict[str, Any],
        guard_results: list[dict[str, str]],
    ) -> dict[str, Any]:
        workspace_id = str(profile_snapshot.get("workspace_id", ""))
        if not workspace_id:
            raise ValueError("profile snapshot is missing workspace_id")
        previous = self.load(workspace_id)
        comparison = self.compare(previous, profile_snapshot)
        payload = {
            **profile_snapshot,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guards": guard_results,
        }
        write_json(self.snapshot_path(workspace_id), payload)
        return comparison
