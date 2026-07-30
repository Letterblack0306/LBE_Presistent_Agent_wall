"""Deterministic, read-only project profiling for guard selection."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


class ProjectProfiler:
    _SIGNALS = (
        ("package.json", "node", "generic"),
        ("pyproject.toml", "python", "generic"),
        ("CSXS/manifest.xml", "cep-extension", "cep"),
        (".lbe/module-registry.json", "module-registry", "module_registry"),
    )

    def profile(
        self,
        workspace_root: str | Path,
        *,
        configured_root_id: str | None = None,
    ) -> dict[str, Any]:
        root = Path(workspace_root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"workspace root is not a directory: {root}")
        signals: list[dict[str, str]] = []
        types: list[str] = []
        packs: list[str] = []
        for relative, project_type, pack in self._SIGNALS:
            path = root / relative
            if path.is_file():
                data = path.read_bytes()
                signals.append({"path": relative.replace("\\", "/"), "sha256": hashlib.sha256(data).hexdigest(), "project_type": project_type, "pack": pack})
                types.append(project_type)
                packs.append(pack)
        packs = list(dict.fromkeys(["generic", *packs]))
        return {
            "workspace_root": str(root), "project_types": sorted(set(types)),
            "workspace_id": self.workspace_id(root),
            "configured_root_id": configured_root_id,
            "target_project_root": str(root),
            "guard_packs": packs if signals else [], "signals": signals,
            "confidence": 1.0 if signals else 0.0,
            "outcome": "profiled" if signals else "insufficient_evidence",
            "missing_evidence": [] if signals else ["No approved project signal was found."],
            "read_only": True,
        }

    @staticmethod
    def workspace_id(workspace_root: str | Path) -> str:
        """Return the stable identity of one canonical project root."""
        canonical_root = str(Path(workspace_root).expanduser().resolve())
        digest = hashlib.sha256(canonical_root.encode("utf-8")).hexdigest()
        return f"workspace_{digest[:16]}"

    @staticmethod
    def snapshot(profile: dict[str, Any]) -> dict[str, Any]:
        signals = sorted(profile.get("signals", []), key=lambda item: item["path"])
        canonical = "\n".join(f"{item['path']}:{item['sha256']}" for item in signals)
        return {
            "workspace_id": profile.get("workspace_id"),
            "configured_root_id": profile.get("configured_root_id"),
            "target_project_root": profile.get("target_project_root"),
            "workspace_root": profile.get("workspace_root"),
            "profile_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "signal_count": len(signals),
            "signals": [
                {"path": item["path"], "sha256": item["sha256"]}
                for item in signals
            ],
        }
