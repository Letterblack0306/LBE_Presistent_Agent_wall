from __future__ import annotations

import json
import subprocess

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadinessStatus,
    probe_cline_sidecar_readiness,
)


def _sidecar(tmp_path, *, declared="0.0.73", installed="0.0.73"):
    root = tmp_path / "cline_llms"
    root.mkdir()
    bridge = root / "bridge.mjs"
    bridge.write_text("// test bridge\n", encoding="utf-8")
    (root / "package.json").write_text(
        json.dumps({"dependencies": {"@cline/llms": declared}}),
        encoding="utf-8",
    )
    if installed is not None:
        package_dir = root / "node_modules" / "@cline" / "llms"
        package_dir.mkdir(parents=True)
        (package_dir / "package.json").write_text(json.dumps({"version": installed}), encoding="utf-8")
    return bridge


def _node(version="v24.15.0", *, returncode=0):
    def run(argv):
        assert list(argv)[-1] == "--version"
        return subprocess.CompletedProcess(list(argv), returncode, stdout=version + "\n", stderr="")

    return run


def test_ready_requires_node_22_and_exact_installed_pin(tmp_path) -> None:
    result = probe_cline_sidecar_readiness(
        bridge_path=_sidecar(tmp_path),
        command_runner=_node(),
    )
    assert result.status is ClineSidecarReadinessStatus.READY
    assert result.ready is True
    assert result.node_version == "v24.15.0"
    assert result.cline_package_version == "0.0.73"


def test_node_below_22_is_unavailable_not_model_unsupported(tmp_path) -> None:
    result = probe_cline_sidecar_readiness(
        bridge_path=_sidecar(tmp_path),
        command_runner=_node("v20.19.4"),
    )
    assert result.status is ClineSidecarReadinessStatus.UNAVAILABLE
    assert result.ready is False
    assert "Node >= 22" in result.reason


def test_missing_isolated_cline_install_is_unavailable(tmp_path) -> None:
    result = probe_cline_sidecar_readiness(
        bridge_path=_sidecar(tmp_path, installed=None),
        command_runner=_node(),
    )
    assert result.status is ClineSidecarReadinessStatus.UNAVAILABLE
    assert "not installed" in result.reason


def test_manifest_pin_drift_is_invalid_and_fails_closed(tmp_path) -> None:
    result = probe_cline_sidecar_readiness(
        bridge_path=_sidecar(tmp_path, declared="0.0.74"),
        command_runner=_node(),
    )
    assert result.status is ClineSidecarReadinessStatus.INVALID
    assert "0.0.73" in result.reason


def test_installed_version_drift_is_invalid_and_fails_closed(tmp_path) -> None:
    result = probe_cline_sidecar_readiness(
        bridge_path=_sidecar(tmp_path, installed="0.0.72"),
        command_runner=_node(),
    )
    assert result.status is ClineSidecarReadinessStatus.INVALID
    assert result.cline_package_version == "0.0.72"


def test_missing_bridge_is_unavailable_without_running_node(tmp_path) -> None:
    called = False

    def run(argv):
        nonlocal called
        called = True
        return subprocess.CompletedProcess(list(argv), 0, stdout="v24.15.0\n", stderr="")

    result = probe_cline_sidecar_readiness(
        bridge_path=tmp_path / "missing" / "bridge.mjs",
        command_runner=run,
    )
    assert result.status is ClineSidecarReadinessStatus.UNAVAILABLE
    assert called is False
