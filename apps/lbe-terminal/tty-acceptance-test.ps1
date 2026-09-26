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
$providerReady = Test-Path -LiteralPath $ProviderConfig -PathType Leaf

# Build provenance: the release binary is only usable for acceptance if it is not
# older than the Rust inputs that produced it. This deliberately compares the
# executable against its real build inputs, not against a Git commit timestamp.
# Commit timestamps and checkout/write timestamps are not a reliable
# build-provenance relationship, and an existence check alone can silently point
# an acceptance run at a stale binary.
$buildInputs = @()
foreach ($relative in @('Cargo.toml', 'Cargo.lock', 'build.rs')) {
    $candidate = Join-Path $PSScriptRoot $relative
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $buildInputs += $candidate }
}
$sourceRoot = Join-Path $PSScriptRoot 'src'
if (Test-Path -LiteralPath $sourceRoot -PathType Container) {
    $buildInputs += @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -File -Filter '*.rs' |
        ForEach-Object { $_.FullName })
}

$binaryInfo = $null
if (Test-Path -LiteralPath $binary -PathType Leaf) {
    $binaryInfo = Get-Item -LiteralPath $binary
}

$newestInput = $null
foreach ($input in $buildInputs) {
    $info = Get-Item -LiteralPath $input
    if ($null -eq $newestInput -or $info.LastWriteTimeUtc -gt $newestInput.LastWriteTimeUtc) {
        $newestInput = $info
    }
}

# A missing binary is reported separately from a stale one so the operator knows
# whether to build at all.
$binaryCurrent = $false
if ($null -ne $binaryInfo -and $null -ne $newestInput) {
    $binaryCurrent = $binaryInfo.LastWriteTimeUtc -ge $newestInput.LastWriteTimeUtc
}

$status = 'READY_FOR_LIVE_LAUNCH_ATTEMPT'
if ($null -eq $binaryInfo) {
    $status = 'BLOCKED_MISSING_RELEASE_BINARY'
} elseif (-not $binaryCurrent) {
    $status = 'BLOCKED_STALE_RELEASE_BINARY'
} elseif ($RequireLiveProvider -and -not $providerReady) {
    $status = 'BLOCKED_PROVIDER_SETUP'
}

[pscustomobject]@{
    status = $status
    launcher = $launcher
    binary = $binary
    binary_last_write_utc = if ($null -ne $binaryInfo) { $binaryInfo.LastWriteTimeUtc.ToString('o') } else { $null }
    newest_build_input = if ($null -ne $newestInput) { $newestInput.FullName } else { $null }
    newest_build_input_last_write_utc = if ($null -ne $newestInput) { $newestInput.LastWriteTimeUtc.ToString('o') } else { $null }
    release_binary_current = $binaryCurrent
    provider_config = $ProviderConfig
    provider_config_present = $providerReady
    remediation = 'Build explicitly, then rerun this check: cargo build --release --locked (in apps/lbe-terminal). This check never builds on your behalf.'
    note = 'This proves packaging and launch prerequisites only, not live PTY acceptance; live provider turns still require a real provider and terminal observation.'
} | ConvertTo-Json -Depth 4

# Fail closed: a blocked prerequisite must not look like a runnable acceptance.
if ($status -ne 'READY_FOR_LIVE_LAUNCH_ATTEMPT') { exit 1 }
exit 0
