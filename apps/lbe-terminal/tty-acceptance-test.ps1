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
$depInfo = Join-Path $PSScriptRoot 'target\release\lbe.d'
$providerReady = Test-Path -LiteralPath $ProviderConfig -PathType Leaf

$binaryInfo = $null
if (Test-Path -LiteralPath $binary -PathType Leaf) {
    $binaryInfo = Get-Item -LiteralPath $binary
}

# The release target's Rust source dependency set comes from the compiler's own
# dep-info output, which Cargo documents for external build systems. It is used
# instead of enumerating src/**/*.rs because a source tree scan wrongly treats
# #[cfg(test)] modules such as tests.rs as release inputs, and a hard-coded module
# list would go stale the moment a module is added.
#
# The dep-info mtime is deliberately NOT used as a freshness signal: it tracks
# the last compile, not the last link of lbe.exe.
$depInfoTarget = $null
$depInfoSources = @()
$depInfoStatus = 'BLOCKED_RELEASE_DEPINFO_UNAVAILABLE'
if (Test-Path -LiteralPath $depInfo -PathType Leaf) {
    try {
        $raw = Get-Content -LiteralPath $depInfo -Raw
        # Join continuation lines, then split on the target/dependency separator.
        # The separator is a colon followed by whitespace. An absolute path on
        # Windows begins with a drive letter like "C:\", whose colon is followed
        # by a backslash, so it must not be treated as the separator.
        $normalized = (($raw -replace "\\\r?\n", ' ') -replace "`r?`n", ' ').Trim()
        $match = [regex]::Match($normalized, '^(?<t>.+?):\s(?<d>.+)$')
        if ($match.Success) {
            $candidateTarget = $match.Groups['t'].Value.Trim()
            $candidateSources = $match.Groups['d'].Value.Trim() -split '\s+' |
                Where-Object { $_ -ne '' }
            # Only accept dep-info that actually describes the expected release
            # executable; any other .d file found nearby is not our manifest.
            $expected = [IO.Path]::GetFullPath($binary)
            $actual = [IO.Path]::GetFullPath($candidateTarget)
            if ([String]::Equals($expected, $actual, [StringComparison]::OrdinalIgnoreCase)) {
                $depInfoTarget = $actual
                $depInfoSources = @($candidateSources)
                $depInfoStatus = 'OK'
            }
        }
    } catch {
        $depInfoStatus = 'BLOCKED_RELEASE_DEPINFO_UNAVAILABLE'
    }
}

# Dependency set: compiler-reported sources plus the manifest inputs, which
# dep-info does not carry.
$declaredDependencies = @()
foreach ($relative in @('Cargo.toml', 'Cargo.lock', 'build.rs')) {
    $candidate = Join-Path $PSScriptRoot $relative
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $declaredDependencies += $candidate }
}
$allDependencies = @($depInfoSources) + @($declaredDependencies)

$missingDependencies = @($allDependencies | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
$newestInput = $null
foreach ($dependency in $allDependencies) {
    if (-not (Test-Path -LiteralPath $dependency -PathType Leaf)) { continue }
    $info = Get-Item -LiteralPath $dependency
    if ($null -eq $newestInput -or $info.LastWriteTimeUtc -gt $newestInput.LastWriteTimeUtc) {
        $newestInput = $info
    }
}

$binaryCurrent = $false
if ($null -ne $binaryInfo -and $null -ne $newestInput) {
    $binaryCurrent = $binaryInfo.LastWriteTimeUtc -ge $newestInput.LastWriteTimeUtc
}

# Ordered fail-closed evaluation. Each blocked state is distinct so the operator
# knows exactly what to do, and none of them can be mistaken for a runnable
# acceptance.
$status = 'READY_FOR_LIVE_LAUNCH_ATTEMPT'
if ($null -eq $binaryInfo) {
    $status = 'BLOCKED_MISSING_RELEASE_BINARY'
} elseif ($depInfoStatus -ne 'OK' -or $depInfoSources.Count -eq 0) {
    $status = 'BLOCKED_RELEASE_DEPINFO_UNAVAILABLE'
} elseif ($missingDependencies.Count -gt 0) {
    $status = 'BLOCKED_RELEASE_DEPENDENCY_MISSING'
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
    dep_info_path = $depInfo
    dep_info_target = $depInfoTarget
    dependency_count = $allDependencies.Count
    missing_dependencies = @($missingDependencies)
    newest_build_input = if ($null -ne $newestInput) { $newestInput.FullName } else { $null }
    newest_build_input_last_write_utc = if ($null -ne $newestInput) { $newestInput.LastWriteTimeUtc.ToString('o') } else { $null }
    release_binary_current = $binaryCurrent
    provider_config = $ProviderConfig
    provider_config_present = $providerReady
    remediation = 'Build explicitly, then rerun this check: cargo build --release --locked (in apps/lbe-terminal). This check never builds on your behalf.'
    note = 'This proves release artifact provenance and launch prerequisites only. It is not evidence that the TUI works interactively, that ALLOW executes, or that receipts and evidence appear; those still require the real interactive terminal acceptance run.'
} | ConvertTo-Json -Depth 5

if ($status -ne 'READY_FOR_LIVE_LAUNCH_ATTEMPT') { exit 1 }
exit 0
