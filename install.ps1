param(
    [string]$OutputRoot,
    [switch]$NoFetch
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Keep installation/package orchestration in the existing product integration
# owner. This wrapper intentionally creates no alternate runtime or launcher.
$integration = Join-Path $PSScriptRoot "tools\lbe_product_integration.ps1"
if (-not (Test-Path -LiteralPath $integration -PathType Leaf)) {
    throw "Canonical product integration script missing: $integration"
}

# Parameters must be passed as a hashtable splat. An array splat expands
# elements positionally, so a literal "-Mode" would be submitted as a *value*
# for Mode and rejected by the owner's ValidateSet before any work began.
$arguments = @{ Mode = "package" }
if ($OutputRoot) { $arguments["OutputRoot"] = $OutputRoot }
if ($NoFetch) { $arguments["NoFetch"] = $true }

& $integration @arguments
exit $LASTEXITCODE
