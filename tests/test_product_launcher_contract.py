from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "lbe_product_integration.ps1"
INSTALLER = ROOT / "install.ps1"


def test_product_launcher_contract_ships_installed_single_command_entrypoint() -> None:
    """Accepted product contract (docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md,
    lines 21-35): a fresh terminal resolves `lbe` through the LetterBlack-installed single command
        bin\\lbe.cmd -> lbe-launch.ps1 -> installed Python runtime -> lbe_guard_inspector.terminal_ui.
    The launcher must declare that chain as its own authoritative entrypoint under its own install
    root (never an npm-published shim, never a global console script, never the retained Rust reference client)."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert '$binDir = Join-Path $InstallRoot "bin"' in source
    assert '$binCmd = Join-Path $binDir "lbe.cmd"' in source
    assert 'Copy-Item -LiteralPath (Join-Path $PSScriptRoot "lbe-launch.ps1")' in source
    assert 'Join-Path $InstallRoot "venv\\Scripts\\python.exe"' in source
    assert '"-m", "lbe_guard_inspector.terminal_ui"' in source
    assert 'SET "LBE_EXIT=%ERRORLEVEL%"' in source
    assert 'ENDLOCAL & EXIT /B %LBE_EXIT%' in source
    assert 'Join-Path $InstallRoot "lbe.exe"' not in source


def test_product_launcher_contract_prepends_installed_bin_idempotently_without_touching_npm() -> None:
    """Installed-surface rule (acceptance gate lines 42-43; launcher contract, never write into npm's
    shim directory and never replace the global Python console script): LetterBlack\\LBE\\bin is
    prepended to the user PATH idempotently, and the launcher never writes into AppData\\Roaming\\npm."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert '[Environment]::SetEnvironmentVariable("Path", ($userPathEntries -join ";"), "User")' in source
    assert '-notcontains $binFull' in source or '-notcontains $binFull,' in source
    assert 'AppData\\Roaming\\npm' not in source


def test_root_installer_delegates_to_canonical_package_flow() -> None:
    """The root installer must delegate to the existing package owner.

    This asserts structure only. It deliberately does not pin one literal
    argument-splatting style, because pinning a style is what previously let a
    runtime-broken invocation satisfy the contract. The delegation is proven
    functionally by the test below.
    """
    source = INSTALLER.read_text(encoding="utf-8")

    assert 'Join-Path $PSScriptRoot "tools\\lbe_product_integration.ps1"' in source
    assert '& $integration @arguments' in source
    assert 'Mode = "package"' in source
    assert 'python -m py_compile' not in source


def test_root_installer_functionally_binds_parameters_to_the_package_owner(tmp_path) -> None:
    """Execute the real root installer and prove it reaches the real package owner
    with correctly bound parameters.

    A stub owner stands in for the build, so this stays fast and hermetic while
    still exercising the genuine wrapper code path: script discovery, argument
    construction, and splatting. The previous array-splat form failed here,
    because "-Mode" arrived as a *value* for Mode and was rejected by ValidateSet
    before any work began.
    """
    if shutil.which("powershell") is None:
        import pytest

        pytest.skip("powershell is required to execute the root installer")

    probe = tmp_path / "captured-arguments.json"
    stub = f"""
param(
    [ValidateSet("check", "prove", "build", "package")][string]$Mode,
    [ValidateSet("auto", "worktree", "origin-main")][string]$SourceMode = "auto",
    [string]$AgentWallRoot,
    [string]$ClientCratePath,
    [string]$TuiRoot,
    [string]$OutputRoot,
    [switch]$NoFetch
)
[pscustomobject]@{{
    Mode = $Mode
    OutputRoot = $OutputRoot
    NoFetch = [bool]$NoFetch
}} | ConvertTo-Json | Set-Content -LiteralPath "{probe}" -Encoding UTF8
"""

    stage = tmp_path / "stage"
    (stage / "tools").mkdir(parents=True)
    (stage / "tools" / "lbe_product_integration.ps1").write_text(stub, encoding="utf-8")
    shutil.copy2(INSTALLER, stage / "install.ps1")

    output_root = tmp_path / "package-out"
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(stage / "install.ps1"),
            "-OutputRoot",
            str(output_root),
            "-NoFetch",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert completed.returncode == 0, (
        f"root installer failed: {completed.stdout}\n{completed.stderr}"
    )
    assert probe.exists(), f"package owner was never invoked: {completed.stdout}\n{completed.stderr}"

    # Windows PowerShell writes UTF-8 with a BOM.
    captured = json.loads(probe.read_text(encoding="utf-8-sig"))
    assert captured["Mode"] == "package"
    assert captured["OutputRoot"] == str(output_root)
    assert captured["NoFetch"] is True


def test_provider_model_instance_failure_remains_non_blocking_after_live_recovery() -> None:
    gate = json.loads(
        (ROOT / ".lbe" / "governance" / "implementation-gates.json").read_text(encoding="utf-8")
    )
    provider_slice = gate["active_execution_plan"]["ordered_slices"]["PROVIDER_MODEL_BINDING"]

    assert provider_slice["status"] == "PASS_BOUNDED_INSTALLED"
    assert provider_slice["blocking"] is False
    assert provider_slice["failure_scope"] == "PROVIDER_OR_MODEL_INSTANCE"
    assert provider_slice["isolation_status"] == "PASS"

    source = SCRIPT.read_text(encoding="utf-8")
    assert "blocking_pending_slices" in source
    assert "non_blocking_pending_slices" in source
    assert "Where-Object { $_.blocking }" in source


def test_installer_is_idempotent_when_provider_config_is_already_installed() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "providerSourceFull" in source
    assert "providerDestinationFull" in source
    assert "[StringComparison]::OrdinalIgnoreCase" in source
    assert "Provider configuration already installed" in source
    assert "pip install --force-reinstall" in source
    assert '"-m", "lbe_guard_inspector.product_entry", "turn"' in source
    assert '"-m", "lbe_guard_inspector.terminal_ui"' in source
