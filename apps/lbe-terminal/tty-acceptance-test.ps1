param(
    [string]$Project = (Join-Path $PSScriptRoot '..\..'),
    [string]$ProviderConfig = (Join-Path $PSScriptRoot '..\..\reasoning-provider.json'),
    [switch]$RequireLiveProvider
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$launcher = Join-Path $root 'launch-lbe.ps1'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw "Launcher missing: $launcher" }

$parseErrors = @()
[System.Management.Automation.Language.Parser]::ParseFile($launcher, [ref]$null, [ref]$parseErrors) | Out-Null
if ($parseErrors.Count -gt 0) { throw "Launcher syntax invalid: $($parseErrors -join '; ')" }

$binary = Join-Path $PSScriptRoot 'target\release\lbe.exe'
if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw "Release binary missing: $binary" }

$providerReady = Test-Path -LiteralPath $ProviderConfig -PathType Leaf
if ($RequireLiveProvider -and -not $providerReady) { throw "Live provider configuration missing: $ProviderConfig" }

[pscustomobject]@{
    status = if ($providerReady) { 'READY_FOR_LIVE_LAUNCH_ATTEMPT' } else { 'BLOCKED_PROVIDER_SETUP' }
    launcher = $launcher
    binary = $binary
    provider_config = $ProviderConfig
    provider_config_present = $providerReady
    note = 'This proves packaging and launch prerequisites; live provider turns still require a real provider and terminal observation.'
} | ConvertTo-Json -Depth 4
