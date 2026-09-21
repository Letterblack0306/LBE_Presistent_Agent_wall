param(
    [string]$Project = (Get-Location).Path,
    [string]$ProviderConfig = (Join-Path $PSScriptRoot 'reasoning-provider.json'),
    [switch]$RequireLiveProvider
)

$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'apps\lbe-terminal\tty-acceptance-test.ps1') `
    -Project $Project -ProviderConfig $ProviderConfig -RequireLiveProvider:$RequireLiveProvider
exit $LASTEXITCODE
