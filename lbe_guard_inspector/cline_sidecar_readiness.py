"""Runtime readiness proof for the optional Cline ``@cline/llms`` sidecar.

Readiness is deliberately narrower than provider/model capability discovery. It
proves only that this host can launch the pinned provider-transport backend. It
does not claim that a selected model supports tools, reasoning, streaming,
structured output, or any workspace capability.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable, Sequence

from .cline_llms_compat import CLINE_LLMS_PACKAGE, CLINE_LLMS_VERSION


MINIMUM_NODE_MAJOR = 22


class ClineSidecarReadinessStatus(StrEnum):
    READY = "ready"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


@dataclass(frozen=True)
class ClineSidecarReadiness:
    status: ClineSidecarReadinessStatus
    node_version: str | None
    bridge_path: str
    package_manifest_path: str
    cline_package_version: str | None
    reason: str

    @property
    def ready(self) -> bool:
        return self.status is ClineSidecarReadinessStatus.READY


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def probe_cline_sidecar_readiness(
    *,
    node_executable: str = "node",
    bridge_path: str | Path | None = None,
    command_runner: CommandRunner | None = None,
) -> ClineSidecarReadiness:
    """Prove whether the pinned Cline sidecar transport is locally runnable.

    The probe never contacts a provider and never infers model features. Missing
    runtime dependencies are UNAVAILABLE. A present but contract-incompatible
    manifest/install is INVALID and fails closed.
    """
    if not isinstance(node_executable, str) or not node_executable.strip():
        raise ValueError("node_executable must be a non-empty string")
    bridge = Path(bridge_path) if bridge_path is not None else _default_bridge_path()
    bridge = bridge.resolve()
    manifest = bridge.parent / "package.json"

    if not bridge.is_file():
        return _result(ClineSidecarReadinessStatus.UNAVAILABLE, bridge, manifest, reason="bridge entrypoint is missing")
    if not manifest.is_file():
        return _result(ClineSidecarReadinessStatus.INVALID, bridge, manifest, reason="bridge package manifest is missing")

    try:
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _result(ClineSidecarReadinessStatus.INVALID, bridge, manifest, reason="bridge package manifest is unreadable or invalid JSON")

    declared = manifest_data.get("dependencies", {}).get(CLINE_LLMS_PACKAGE)
    if declared != CLINE_LLMS_VERSION:
        return _result(
            ClineSidecarReadinessStatus.INVALID,
            bridge,
            manifest,
            cline_package_version=declared if isinstance(declared, str) else None,
            reason=f"bridge must pin {CLINE_LLMS_PACKAGE}@{CLINE_LLMS_VERSION} exactly",
        )

    runner = command_runner or _run_command
    try:
        version_result = runner((node_executable.strip(), "--version"))
    except OSError as exc:
        return _result(ClineSidecarReadinessStatus.UNAVAILABLE, bridge, manifest, reason=f"Node executable is unavailable: {exc}")
    if version_result.returncode != 0:
        return _result(ClineSidecarReadinessStatus.UNAVAILABLE, bridge, manifest, reason="Node version probe failed")

    node_version = version_result.stdout.strip()
    major = _node_major(node_version)
    if major is None:
        return _result(ClineSidecarReadinessStatus.INVALID, bridge, manifest, node_version=node_version, reason="Node version output is not recognized")
    if major < MINIMUM_NODE_MAJOR:
        return _result(
            ClineSidecarReadinessStatus.UNAVAILABLE,
            bridge,
            manifest,
            node_version=node_version,
            reason=f"Node >= {MINIMUM_NODE_MAJOR} is required for the Cline sidecar",
        )

    package_manifest = bridge.parent / "node_modules" / "@cline" / "llms" / "package.json"
    if not package_manifest.is_file():
        return _result(
            ClineSidecarReadinessStatus.UNAVAILABLE,
            bridge,
            manifest,
            node_version=node_version,
            reason=f"{CLINE_LLMS_PACKAGE}@{CLINE_LLMS_VERSION} is not installed in the isolated sidecar",
        )
    try:
        installed = json.loads(package_manifest.read_text(encoding="utf-8")).get("version")
    except (OSError, json.JSONDecodeError):
        return _result(ClineSidecarReadinessStatus.INVALID, bridge, manifest, node_version=node_version, reason="installed Cline package manifest is invalid")
    if installed != CLINE_LLMS_VERSION:
        return _result(
            ClineSidecarReadinessStatus.INVALID,
            bridge,
            manifest,
            node_version=node_version,
            cline_package_version=installed if isinstance(installed, str) else None,
            reason=f"installed {CLINE_LLMS_PACKAGE} version does not match the pinned compatibility contract",
        )

    return _result(
        ClineSidecarReadinessStatus.READY,
        bridge,
        manifest,
        node_version=node_version,
        cline_package_version=installed,
        reason="pinned Cline sidecar transport is locally runnable",
    )


def require_cline_sidecar_ready(**kwargs: object) -> ClineSidecarReadiness:
    readiness = probe_cline_sidecar_readiness(**kwargs)
    if not readiness.ready:
        raise RuntimeError(f"Cline sidecar is not ready: {readiness.reason}")
    return readiness


def _run_command(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=False,
        check=False,
    )


def _node_major(version: str) -> int | None:
    match = re.fullmatch(r"v?(\d+)(?:\.\d+){0,2}", version.strip())
    return int(match.group(1)) if match else None


def _result(
    status: ClineSidecarReadinessStatus,
    bridge: Path,
    manifest: Path,
    *,
    node_version: str | None = None,
    cline_package_version: str | None = None,
    reason: str,
) -> ClineSidecarReadiness:
    return ClineSidecarReadiness(
        status=status,
        node_version=node_version,
        bridge_path=str(bridge),
        package_manifest_path=str(manifest),
        cline_package_version=cline_package_version,
        reason=reason,
    )


def _default_bridge_path() -> Path:
    return Path(__file__).resolve().parents[1] / "provider_bridge" / "cline_llms" / "bridge.mjs"
