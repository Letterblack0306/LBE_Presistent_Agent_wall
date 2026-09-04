param(
    [ValidateSet("check", "prove", "build", "package")]
    [string]$Mode = "check",
    [string]$AgentWallRoot = "C:\Agents-Memory-Tool-v6-integration",
    [string]$TuiRoot = "C:\LBE-TUI-Lab",
    [string]$OutputRoot = (Join-Path $PSScriptRoot "..\dist\product-integration"),
    [switch]$NoFetch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AgentWallRepository = "Letterblack0306/LBE_Presistent_Agent_wall"
$TuiRepository = "Letterblack0306/LBE_Agents_wall_Intigration"
$SchemaVersion = 1

function Invoke-Native {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$WorkingDirectory
    )
    $previous = Get-Location
    try {
        if ($WorkingDirectory) { Set-Location $WorkingDirectory }
        $lines = @(& $FilePath @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        Set-Location $previous
    }
    [pscustomobject]@{
        command = "$FilePath $($Arguments -join ' ')"
        exit_code = $exitCode
        output = @($lines | ForEach-Object { "$_" })
    }
}

function Invoke-Git {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string[]]$Arguments,
        [switch]$AllowFailure
    )
    $result = Invoke-Native -FilePath "git" -Arguments (@("-C", $Root) + $Arguments)
    if (-not $AllowFailure -and $result.exit_code -ne 0) {
        throw "git failed in $Root: $($result.command) $([Environment]::NewLine)$($result.output -join [Environment]::NewLine)"
    }
    return $result
}

function Get-GitText {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Ref,
        [Parameter(Mandatory)][string]$Path
    )
    $spec = "{0}:{1}" -f $Ref, $Path
    $result = Invoke-Git -Root $Root -Arguments @("show", $spec)
    return ($result.output -join [Environment]::NewLine)
}

function Assert-Workspace {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Repository
    )
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        throw "workspace missing: $Root"
    }
    $top = (Invoke-Git -Root $Root -Arguments @("rev-parse", "--show-toplevel")).output[-1].Trim()
    $origin = (Invoke-Git -Root $Root -Arguments @("remote", "get-url", "origin")).output[-1].Trim()
    $expectedName = [regex]::Escape($Repository)
    if ($origin -notmatch "(github\.com[:/])$expectedName(\.git)?$") {
        throw "repository identity mismatch for $Root. expected=$Repository origin=$origin"
    }
    if (-not $NoFetch) {
        $fetch = Invoke-Git -Root $Root -Arguments @("fetch", "origin", "main") -AllowFailure
        if ($fetch.exit_code -ne 0) { throw "failed to refresh origin/main for $Repository" }
    }
    $head = (Invoke-Git -Root $Root -Arguments @("rev-parse", "HEAD")).output[-1].Trim()
    $originMain = (Invoke-Git -Root $Root -Arguments @("rev-parse", "origin/main")).output[-1].Trim()
    $branchResult = Invoke-Git -Root $Root -Arguments @("branch", "--show-current") -AllowFailure
    $branch = if ($branchResult.exit_code -eq 0 -and $branchResult.output.Count) { $branchResult.output[-1].Trim() } else { "" }
    $status = Invoke-Git -Root $Root -Arguments @("status", "--porcelain=v1")
    $worktree = Invoke-Git -Root $Root -Arguments @("worktree", "list", "--porcelain")
    $worktreeCount = @($worktree.output | Where-Object { $_ -match "^worktree " }).Count
    [pscustomobject]@{
        repository = $Repository
        root = $top
        origin = $origin
        branch = $branch
        head = $head
        origin_main = $originMain
        head_matches_origin_main = ($head -eq $originMain)
        dirty_entry_count = @($status.output | Where-Object { $_.Trim() }).Count
        worktree_count = $worktreeCount
        packaging_ref = "origin/main"
    }
}

function New-ContractCheck {
    param([string]$Id, [bool]$Passed, [string]$Classification, [string]$Detail)
    [pscustomobject]@{
        id = $Id
        passed = $Passed
        classification = $Classification
        detail = $Detail
    }
}

function Test-IntegrationContracts {
    param([string]$AgentRoot, [string]$ClientRoot)

    $productEntry = Get-GitText -Root $AgentRoot -Ref "origin/main" -Path "lbe_guard_inspector/product_entry.py"
    $toolRuntime = Get-GitText -Root $AgentRoot -Ref "origin/main" -Path "lbe_guard_inspector/runtime/tool_orchestration.py"
    $productTests = Get-GitText -Root $AgentRoot -Ref "origin/main" -Path "tests/test_product_entry.py"
    $wrapper = Get-GitText -Root $ClientRoot -Ref "origin/main" -Path "src/wrapper.rs"
    $types = Get-GitText -Root $ClientRoot -Ref "origin/main" -Path "src/types.rs"

    $checks = [System.Collections.Generic.List[object]]::new()

    $productCommands = @("start", "turn", "control", "tool", "authorization", "capabilities", "export")
    $missingCommands = @($productCommands | Where-Object { $productEntry -notmatch ('"' + [regex]::Escape($_) + '"') })
    $checks.Add((New-ContractCheck -Id "lbe.product_commands" -Passed ($missingCommands.Count -eq 0) -Classification $(if ($missingCommands.Count -eq 0) { "CONNECTED" } else { "MISSING" }) -Detail $(if ($missingCommands.Count -eq 0) { "Published Agent Wall product-entry command surface is present." } else { "Missing commands: $($missingCommands -join ', ')" })))

    $wrapperUsesProductEntry = $wrapper.Contains("lbe_guard_inspector.product_entry")
    $checks.Add((New-ContractCheck -Id "tui.real_wrapper_boundary" -Passed $wrapperUsesProductEntry -Classification $(if ($wrapperUsesProductEntry) { "CONNECTED" } else { "MISSING" }) -Detail "Rust RealLbeWrapper must route through the canonical Agent Wall product entry."))

    $readOnlyTools = @("workspace.read", "workspace.list", "workspace.glob", "workspace.search")
    $readOnlyConnected = @($readOnlyTools | Where-Object { -not ($productEntry.Contains($_) -and $wrapper.Contains($_)) }).Count -eq 0
    $checks.Add((New-ContractCheck -Id "workspace.readonly_tools" -Passed $readOnlyConnected -Classification $(if ($readOnlyConnected) { "CONNECTED" } else { "PARTIAL" }) -Detail "Read-only workspace capabilities must exist on both runtime and client sides."))

    $approvalRuntime = $toolRuntime.Contains("approval_granted") -and $productEntry.Contains("_governed_operation_fingerprint") -and $productEntry.Contains("save_governed_operation")
    $approvalTest = $productTests.Contains("test_product_entry_approval_bridge_executes_exact_operation_once")
    $approvalClient = $wrapper.Contains("pending_authorization") -and $wrapper.Contains("UserRequest::Approve") -and $wrapper.Contains("UserRequest::Reject") -and $wrapper.Contains("workspace.patch")
    $approvalConnected = $approvalRuntime -and $approvalTest -and $approvalClient
    $checks.Add((New-ContractCheck -Id "workspace.patch.approval_bridge" -Passed $approvalConnected -Classification $(if ($approvalConnected) { "CONNECTED_TEST_PROOF_PRESENT" } else { "PARTIAL" }) -Detail "Requires persisted exact-operation approval binding, product-entry idempotency proof, and Rust approve/reject routing."))

    $payloadSubstitutionProof = $productTests.Contains("substituted") -and $productTests.Contains("payload")
    $checks.Add((New-ContractCheck -Id "workspace.patch.payload_binding" -Passed $payloadSubstitutionProof -Classification $(if ($payloadSubstitutionProof) { "TEST_PROOF_PRESENT" } else { "UNPROVEN" }) -Detail "Approved operation must reject changed payloads."))

    $mcpConnected = $productEntry.Contains("mcp.birdeye.") -and $wrapper.Contains("mcp.birdeye.")
    $checks.Add((New-ContractCheck -Id "mcp.birdeye.routing" -Passed $mcpConnected -Classification $(if ($mcpConnected) { "STRUCTURALLY_CONNECTED" } else { "PARTIAL" }) -Detail "BirdEye requests must cross the LBE governed tool boundary."))

    $sessionProjection = $types.Contains("session_id") -and $wrapper.Contains("session_id")
    $checks.Add((New-ContractCheck -Id "session.identity_projection" -Passed $sessionProjection -Classification $(if ($sessionProjection) { "CONNECTED" } else { "PARTIAL" }) -Detail "Rust session projection must preserve authoritative LBE session identity."))

    return @($checks)
}

function Export-OriginMain {
    param([string]$Root, [string]$Destination)
    if (Test-Path -LiteralPath $Destination) { Remove-Item -LiteralPath $Destination -Recurse -Force }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $archive = "$Destination.zip"
    if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
    Invoke-Git -Root $Root -Arguments @("archive", "--format=zip", "--output=$archive", "origin/main") | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $Destination -Force
    Remove-Item -LiteralPath $archive -Force
}

function Invoke-Proof {
    param([string]$AgentStage, [string]$TuiStage)

    $proofs = [System.Collections.Generic.List[object]]::new()
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $proofs.Add([pscustomobject]@{ id = "agent.focused_tests"; status = "BLOCKED"; exit_code = $null; command = "python"; output = @("python not found") })
    }
    else {
        $agent = Invoke-Native -FilePath $python.Source -WorkingDirectory $AgentStage -Arguments @("-m", "pytest", "-q", "tests/test_authorization_resolver.py", "tests/test_tool_orchestration.py", "tests/test_product_entry.py", "tests/test_provider_continuation.py")
        $proofs.Add([pscustomobject]@{ id = "agent.focused_tests"; status = $(if ($agent.exit_code -eq 0) { "PASS" } else { "FAIL" }); exit_code = $agent.exit_code; command = $agent.command; output = $agent.output })
    }

    $cargo = Get-Command cargo -ErrorAction SilentlyContinue
    if (-not $cargo) {
        $proofs.Add([pscustomobject]@{ id = "tui.cargo_test"; status = "BLOCKED"; exit_code = $null; command = "cargo"; output = @("cargo not found") })
    }
    else {
        $tui = Invoke-Native -FilePath $cargo.Source -WorkingDirectory $TuiStage -Arguments @("test", "--locked")
        $proofs.Add([pscustomobject]@{ id = "tui.cargo_test"; status = $(if ($tui.exit_code -eq 0) { "PASS" } else { "FAIL" }); exit_code = $tui.exit_code; command = $tui.command; output = $tui.output })
        $fmt = Invoke-Native -FilePath $cargo.Source -WorkingDirectory $TuiStage -Arguments @("fmt", "--", "--check")
        $proofs.Add([pscustomobject]@{ id = "tui.cargo_fmt"; status = $(if ($fmt.exit_code -eq 0) { "PASS" } else { "FAIL" }); exit_code = $fmt.exit_code; command = $fmt.command; output = $fmt.output })
    }
    return @($proofs)
}

function Build-Product {
    param([string]$AgentStage, [string]$TuiStage, [string]$BuildRoot)

    if (Test-Path -LiteralPath $BuildRoot) { Remove-Item -LiteralPath $BuildRoot -Recurse -Force }
    New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
    $runtimeOut = Join-Path $BuildRoot "runtime"
    $clientOut = Join-Path $BuildRoot "client"
    $workerOut = Join-Path $BuildRoot "cline-worker"
    New-Item -ItemType Directory -Path $runtimeOut, $clientOut, $workerOut -Force | Out-Null

    $python = Get-Command python -ErrorAction Stop
    $pipWheel = Invoke-Native -FilePath $python.Source -WorkingDirectory $AgentStage -Arguments @("-m", "pip", "wheel", ".", "--no-deps", "--wheel-dir", $runtimeOut)
    if ($pipWheel.exit_code -ne 0) { throw "Agent Wall wheel build failed." }

    $workerSource = Join-Path $AgentStage "lbe_guard_inspector\runtime\cline_worker"
    $npm = Get-Command npm -ErrorAction Stop
    $npmCi = Invoke-Native -FilePath $npm.Source -WorkingDirectory $workerSource -Arguments @("ci", "--omit=dev")
    if ($npmCi.exit_code -ne 0) { throw "Cline worker dependency provisioning failed." }
    Copy-Item -LiteralPath (Join-Path $workerSource "worker.mjs") -Destination $workerOut
    Copy-Item -LiteralPath (Join-Path $workerSource "package.json") -Destination $workerOut
    Copy-Item -LiteralPath (Join-Path $workerSource "package-lock.json") -Destination $workerOut
    Copy-Item -LiteralPath (Join-Path $workerSource "node_modules") -Destination $workerOut -Recurse

    $cargo = Get-Command cargo -ErrorAction Stop
    $cargoBuild = Invoke-Native -FilePath $cargo.Source -WorkingDirectory $TuiStage -Arguments @("build", "--release", "--locked")
    if ($cargoBuild.exit_code -ne 0) { throw "Rust client release build failed." }
    $exe = Join-Path $TuiStage "target\release\lbe.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Rust release binary missing: $exe" }
    Copy-Item -LiteralPath $exe -Destination (Join-Path $clientOut "lbe.exe")

    [pscustomobject]@{
        runtime_wheels = @((Get-ChildItem -LiteralPath $runtimeOut -Filter "*.whl" | Select-Object -ExpandProperty Name))
        client = "client/lbe.exe"
        cline_worker = "cline-worker/"
        build_commands = @($pipWheel.command, $npmCi.command, $cargoBuild.command)
    }
}

function Write-Installer {
    param([string]$PackageRoot)
    $installer = @'
param([string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "LetterBlack\LBE"))
$ErrorActionPreference = "Stop"
$venv = Join-Path $InstallRoot "venv"
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
python -m venv $venv
$python = Join-Path $venv "Scripts\python.exe"
$wheel = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot "runtime") -Filter "*.whl" | Select-Object -First 1
if (-not $wheel) { throw "LBE runtime wheel missing" }
& $python -m pip install --no-deps $wheel.FullName
if ($LASTEXITCODE -ne 0) { throw "LBE runtime install failed" }
$site = & $python -c "import pathlib,lbe_guard_inspector; print(pathlib.Path(lbe_guard_inspector.__file__).parent)"
if ($LASTEXITCODE -ne 0) { throw "Unable to resolve installed LBE package" }
$workerTarget = Join-Path $site "runtime\cline_worker"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "cline-worker\node_modules") -Destination $workerTarget -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "client\lbe.exe") -Destination (Join-Path $InstallRoot "lbe.exe") -Force
Write-Host "Installed LetterBlack LBE to $InstallRoot"
Write-Host "Runtime CLI: $(Join-Path $venv 'Scripts\lbe.exe')"
Write-Host "Rust client: $(Join-Path $InstallRoot 'lbe.exe')"
'@
    Set-Content -LiteralPath (Join-Path $PackageRoot "install.ps1") -Value $installer -Encoding UTF8
}

function Get-Checksums {
    param([string]$Root)
    @(
        Get-ChildItem -LiteralPath $Root -File -Recurse | Sort-Object FullName | ForEach-Object {
            $relative = [IO.Path]::GetRelativePath($Root, $_.FullName).Replace("\", "/")
            [pscustomobject]@{
                path = $relative
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                bytes = $_.Length
            }
        }
    )
}

$agent = Assert-Workspace -Root $AgentWallRoot -Repository $AgentWallRepository
$tui = Assert-Workspace -Root $TuiRoot -Repository $TuiRepository

if ($agent.worktree_count -ne 1) { throw "Agent Wall must have exactly one registered worktree; found $($agent.worktree_count)." }
if ($tui.worktree_count -ne 1) { throw "LBE TUI must have exactly one registered worktree; found $($tui.worktree_count)." }

$contracts = Test-IntegrationContracts -AgentRoot $AgentWallRoot -ClientRoot $TuiRoot
$structuralPass = @($contracts | Where-Object { -not $_.passed }).Count -eq 0

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$stageRoot = Join-Path $OutputRoot "_staging"
$agentStage = Join-Path $stageRoot "agent-wall"
$tuiStage = Join-Path $stageRoot "lbe-tui"
$proofs = @()
$build = $null
$packagePath = $null

if ($Mode -in @("prove", "build", "package")) {
    Export-OriginMain -Root $AgentWallRoot -Destination $agentStage
    Export-OriginMain -Root $TuiRoot -Destination $tuiStage
    $proofs = Invoke-Proof -AgentStage $agentStage -TuiStage $tuiStage
}

$proofPass = if ($proofs.Count -eq 0) { $false } else { @($proofs | Where-Object { $_.status -ne "PASS" }).Count -eq 0 }

if ($Mode -in @("build", "package")) {
    if (-not $structuralPass) { throw "Product build blocked: structural integration checks failed." }
    if (-not $proofPass) { throw "Product build blocked: proof suite did not pass." }
    $packageRoot = Join-Path $OutputRoot "LetterBlack-LBE"
    $build = Build-Product -AgentStage $agentStage -TuiStage $tuiStage -BuildRoot $packageRoot
    Write-Installer -PackageRoot $packageRoot
}

$manifest = [ordered]@{
    schema_version = $SchemaVersion
    product = "LetterBlack LBE"
    generated_at = [DateTimeOffset]::UtcNow.ToString("o")
    generator = "tools/lbe_product_integration.ps1"
    mode = $Mode
    authority = [ordered]@{
        rule = "Agent Wall is runtime authority; Rust is client/projection; this script verifies, proves, builds, and packages but owns no runtime decision."
        agent_wall = $agent
        rust_client = $tui
    }
    contracts = $contracts
    proofs = $proofs
    structural_integration_pass = $structuralPass
    proof_pass = $proofPass
    build = $build
    installed_interactive_pty = [ordered]@{
        classification = "UNPROVEN_BY_THIS_SCRIPT"
        blocking_release_acceptance = $true
        note = "External PTY/ConPTY interactive acceptance must be attached as separate machine evidence before release-ready status."
    }
    release_ready = $false
}

$manifestPath = Join-Path $OutputRoot "integration-manifest.json"
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

if ($Mode -eq "package") {
    $packageRoot = Join-Path $OutputRoot "LetterBlack-LBE"
    Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $packageRoot "integration-manifest.json") -Force
    $checksums = Get-Checksums -Root $packageRoot
    $checksums | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $packageRoot "checksums.json") -Encoding UTF8
    $zip = Join-Path $OutputRoot "LetterBlack-LBE-2.0.3-win-x64-candidate.zip"
    if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
    Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $zip -CompressionLevel Optimal
    $packagePath = $zip
}

if (Test-Path -LiteralPath $stageRoot) { Remove-Item -LiteralPath $stageRoot -Recurse -Force }

Write-Host "=== LETTERBLACK PRODUCT INTEGRATION ==="
Write-Host "Mode: $Mode"
Write-Host "Agent Wall origin/main: $($agent.origin_main)"
Write-Host "Rust TUI origin/main:     $($tui.origin_main)"
Write-Host "Structural integration:   $structuralPass"
Write-Host "Proof pass:               $proofPass"
Write-Host "Manifest:                 $manifestPath"
if ($packagePath) { Write-Host "Candidate package:        $packagePath" }
Write-Host "Release ready:             False (external installed PTY/ConPTY acceptance is intentionally not fabricated)"

if (-not $structuralPass) { exit 2 }
if ($Mode -in @("prove", "build", "package") -and -not $proofPass) { exit 3 }
exit 0
