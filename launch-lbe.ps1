param(
    [string]$Project = (Get-Location).Path,
    [string]$Database = (Join-Path $PSScriptRoot 'state\workspace.db'),
    [string]$ProviderConfig = (Join-Path $PSScriptRoot 'reasoning-provider.json'),
    [string]$CapabilityRegistry = (Join-Path $PSScriptRoot 'state\capability-registry.json'),
    [string]$SessionId = $env:LBE_SESSION_ID,
    [ValidateSet('audit','plan','coding')][string]$Agent = 'audit',
    [string]$Model
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = [IO.Path]::GetFullPath($PSScriptRoot)
$workspace = [IO.Path]::GetFullPath($Project)
function Resolve-LbePython {
    # The governed session bootstrap needs a real Python 3.11+ interpreter with the
    # runtime dependencies present. A bare `python` on PATH can be older than the
    # package requirement, so resolve deterministically and fail with a clear reason
    # instead of letting the private runtime blow up later with an opaque error.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $candidates = New-Object System.Collections.Generic.List[string]
        $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            $listing = (& $pyLauncher.Source '-0p' 2>$null | Out-String)
            foreach ($line in ($listing -split "`r?`n")) {
                if ($line -match '-V:(?<major>\d+)\.(?<minor>\d+)\s+\*?\s*(?<path>[A-Za-z]:\\.*?python\.exe)\s*$') {
                    if ([int]$Matches['major'] -eq 3 -and [int]$Matches['minor'] -ge 11) {
                        $candidates.Add($Matches['path'].Trim())
                    }
                }
            }
            if ($candidates.Count -eq 0) {
                foreach ($tag in @('-3.14', '-3.13', '-3.12', '-3.11')) {
                    $probe = (& $pyLauncher.Source $tag -c 'import sys; print(sys.executable)' 2>$null | Out-String).Trim()
                    if ($LASTEXITCODE -eq 0 -and $probe) { $candidates.Add($probe) }
                }
            }
        }
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCommand) { $candidates.Add($pythonCommand.Source) }

        foreach ($candidate in ($candidates | Select-Object -Unique)) {
            if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
            & $candidate -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            $version = (& $candidate -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>$null | Out-String).Trim()
            $dependencyError = (& $candidate -c 'import jsonschema' 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -ne 0) {
                return [pscustomobject]@{ Source = $candidate; Version = $version; DependencyError = $dependencyError }
            }
            return [pscustomobject]@{ Source = $candidate; Version = $version; DependencyError = $null }
        }
        return $null
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

$pythonCommand = Resolve-LbePython
if (-not $pythonCommand) {
    throw 'LBE requires a Python 3.11 or newer interpreter to bootstrap the governed session; none was found (the default `python` on this machine is older). Install one (for example: winget install Python.Python.3.13) and rerun this launcher.'
}
if ($pythonCommand.DependencyError) {
    throw "LBE runtime Python $($pythonCommand.Version) at $($pythonCommand.Source) is missing a required dependency: $($pythonCommand.DependencyError). Install it with `"$($pythonCommand.Source)`" -m pip install -r requirements.txt"
}
if (-not (Test-Path -LiteralPath $workspace -PathType Container)) { throw "Project workspace missing: $workspace" }
if (-not (Test-Path -LiteralPath $ProviderConfig -PathType Leaf)) {
    throw "Provider setup is required. Create reasoning-provider.json from reasoning-provider.example.json, then rerun this launcher. No provider or credential was fabricated."
}

$provider = Get-Content -LiteralPath $ProviderConfig -Raw | ConvertFrom-Json
if (-not $Model) { $Model = [string]$provider.model }
if (-not $Model -or $Model -eq 'replace-with-provider-model-id') {
    throw 'Provider setup is incomplete: reasoning-provider.json must contain a real model id.'
}
$providerIdProperty = $provider.PSObject.Properties['provider_id']
$providerId = if ($providerIdProperty -and -not [string]::IsNullOrWhiteSpace([string]$providerIdProperty.Value)) {
    [string]$providerIdProperty.Value
} elseif ([string]$provider.endpoint -match '/v1(?:/|$)') {
    # The explicit provider file is OpenAI-compatible when it supplies a
    # standard /v1 endpoint. Keep the runtime identity parseable by the TUI
    # instead of inventing a provider id that the real adapter cannot project.
    'openai-compatible'
} else {
    'configured-provider'
}

if (-not $SessionId) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($workspace.ToLowerInvariant())
        $workspaceId = 'workspace_' + ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally { $sha.Dispose() }
    $mode = if ($Agent -eq 'plan') { 'investigation' } elseif ($Agent -eq 'audit') { 'audit' } else { 'coding' }
    $bootstrapArgs = @(
        '-m','lbe_guard_inspector.product_entry','start',
        '--database',[IO.Path]::GetFullPath($Database),
        '--workspace',$workspace,
        '--project-workspace-id',$workspaceId,
        '--mode',$mode,
        '--permission','read_only',
        '--runtime-policy','audit',
        '--provider',$providerId,
        '--model',$Model,
        '--provider-config',[IO.Path]::GetFullPath($ProviderConfig),
        '--format','json'
    )
    if (Test-Path -LiteralPath $CapabilityRegistry -PathType Leaf) {
        $bootstrapArgs += @('--capability-registry',[IO.Path]::GetFullPath($CapabilityRegistry))
    }
    # The runtime package lives in this repository; `-m lbe_guard_inspector.product_entry`
    # only resolves from the repository root, so bootstrap there instead of trusting the
    # caller's current directory.
    Push-Location -LiteralPath $root
    try {
        $result = (& $pythonCommand.Source @bootstrapArgs 2>&1 | Out-String).Trim()
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) { throw "Governed session bootstrap failed: $result" }
    try { $created = $result | ConvertFrom-Json } catch { throw "Governed session bootstrap returned invalid JSON: $result" }
    if (-not $created.ok -or -not $created.session_id) { throw "Governed session bootstrap was rejected: $result" }
    $SessionId = [string]$created.session_id
}

$env:LBE_RUNTIME = 'real'
$env:LBE_WALL_ROOT = $root
$env:LBE_WALL_PYTHON = $pythonCommand.Source
$env:LBE_TARGET_WORKSPACE = $workspace
$env:LBE_WALL_DATABASE = [IO.Path]::GetFullPath($Database)
$env:LBE_PROVIDER_CONFIG = [IO.Path]::GetFullPath($ProviderConfig)
$env:LBE_SESSION_ID = $SessionId
if (Test-Path -LiteralPath $CapabilityRegistry -PathType Leaf) {
    $env:LBE_CAPABILITY_REGISTRY = [IO.Path]::GetFullPath($CapabilityRegistry)
}

$exe = Join-Path $root 'apps\lbe-terminal\target\release\lbe.exe'
if (Test-Path -LiteralPath $exe -PathType Leaf) {
    & $exe $workspace '--agent' $Agent '--model' $Model '--session' $SessionId
    exit $LASTEXITCODE
}

Push-Location (Join-Path $root 'apps\lbe-terminal')
try {
    & cargo run --release -- $workspace '--agent' $Agent '--model' $Model '--session' $SessionId
    exit $LASTEXITCODE
} finally { Pop-Location }
