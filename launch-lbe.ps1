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
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) { throw 'Python is required to bootstrap the governed LBE session.' }
if (-not (Test-Path -LiteralPath $workspace -PathType Container)) { throw "Project workspace missing: $workspace" }
if (-not (Test-Path -LiteralPath $ProviderConfig -PathType Leaf)) {
    throw "Provider setup is required. Create reasoning-provider.json from reasoning-provider.example.json, then rerun this launcher. No provider or credential was fabricated."
}

$provider = Get-Content -LiteralPath $ProviderConfig -Raw | ConvertFrom-Json
if (-not $Model) { $Model = [string]$provider.model }
if (-not $Model -or $Model -eq 'replace-with-provider-model-id') {
    throw 'Provider setup is incomplete: reasoning-provider.json must contain a real model id.'
}
$providerId = if ($provider.provider_id) {
    [string]$provider.provider_id
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
    $result = (& $pythonCommand.Source @bootstrapArgs 2>&1 | Out-String).Trim()
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
