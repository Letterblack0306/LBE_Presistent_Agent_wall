from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "lbe_product_integration.ps1"
INSTALLER = Path(__file__).resolve().parents[1] / "install.ps1"


def test_product_launcher_contract_ships_installed_single_command_entrypoint() -> None:
    """Accepted product contract (docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md,
    lines 21-35): a fresh terminal resolves `lbe` through the LetterBlack-installed single command
        bin\\lbe.cmd -> lbe-launch.ps1 -> installed Rust/Ratatui lbe.exe.
    The launcher must declare that chain as its own authoritative entrypoint under its own install
    root (never an npm-published shim, never a global console script)."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert '$binDir = Join-Path $InstallRoot "bin"' in source
    assert '$binCmd = Join-Path $binDir "lbe.cmd"' in source
    assert 'Copy-Item -LiteralPath (Join-Path $PSScriptRoot "lbe-launch.ps1")' in source
    assert 'Join-Path $InstallRoot "lbe.exe"' in source


def test_product_launcher_contract_prepends_installed_bin_idempotently_without_touching_npm() -> None:
    """Installed-surface rule (acceptance gate lines 42-43; launcher contract, never write into npm's
    shim directory and never replace the global Python console script): LetterBlack\\LBE\\bin is
    prepended to the user PATH idempotently, and the launcher never writes into AppData\\Roaming\\npm."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert '[Environment]::SetEnvironmentVariable("Path", ($userPathEntries -join ";"), "User")' in source
    assert '-notcontains $binFull' in source or '-notcontains $binFull,' in source
    assert 'AppData\\Roaming\\npm' not in source


def test_root_installer_delegates_to_canonical_package_flow() -> None:
    source = INSTALLER.read_text(encoding="utf-8")

    assert 'Join-Path $PSScriptRoot "tools\\lbe_product_integration.ps1"' in source
    assert '$arguments = @("-Mode", "package")' in source
    assert '& $integration @arguments' in source
    assert 'python -m py_compile' not in source
