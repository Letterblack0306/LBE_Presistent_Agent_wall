from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "lbe_product_integration.ps1"


def test_product_launcher_binds_project_guard_runtime_without_site_packages_fallback() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert '$guardConfigPath = Join-Path $InstallRoot "config\\config.json"' in source
    assert '$guardGovernancePath = Join-Path $InstallRoot "config\\governance.json"' in source
    assert '$guardStateDir = Join-Path $InstallRoot "state"' in source
    assert '$env:LBE_GUARD_INSPECTOR_CONFIG_PATH = [IO.Path]::GetFullPath($guardConfigPath)' in source
    assert '$env:LBE_GUARD_INSPECTOR_GOVERNANCE_PATH = [IO.Path]::GetFullPath($guardGovernancePath)' in source
    assert '$env:LBE_GUARD_INSPECTOR_STATE_DIR = [IO.Path]::GetFullPath($guardStateDir)' in source
    assert 'if (-not (Test-Path -LiteralPath $required -PathType Leaf))' in source
    assert 'knowledge_roots = @(@{ name = "launched-project"; path = [IO.Path]::GetFullPath($Project) })' in source
    assert 'allowed_write_paths = @(".")' in source
    assert 'lbe-client.exe' in source


def test_product_launcher_owns_user_command_without_overwriting_npm() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'Set-Content -LiteralPath (Join-Path $InstallRoot "lbe.cmd")' in source
    assert 'Set-Content -LiteralPath (Join-Path $InstallRoot "lbe.ps1")' in source
    assert '[Environment]::SetEnvironmentVariable("Path", "$installFull;$userPath", "User")' in source
    assert 'AppData\\Roaming\\npm' not in source
