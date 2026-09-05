param(
    [ValidateSet("check", "prove", "build", "package")]
    [string]$Mode = "check",
    [ValidateSet("auto", "worktree", "origin-main")]
    [string]$SourceMode = "auto",
    [string]$AgentWallRoot = "C:\Agents-Memory-Tool-v6-integration",
    [string]$TuiRoot = "C:\LBE-TUI-Lab",
    [string]$OutputRoot = (Join-Path $PSScriptRoot "..\dist\product-integration"),
    [switch]$NoFetch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AgentWallRepository = "Letterblack0306/LBE_Presistent_Agent_wall"
$TuiRepository = "Letterblack0306/LBE_Agents_wall_Intigration"
$SchemaVersion = 2
$ClineReferenceRepository = "cline/cline"
$ClineReferenceCommit = "952df213ee654633fb3f7abda23a1c1b24e92d7f"
$ClineReferenceFiles = @(
    "apps/cli/src/runtime/run-interactive.ts",
    "apps/cli/src/runtime/interactive/session-runtime.ts",
    "apps/cli/src/runtime/interactive/approvals.ts",
    "apps/cli/src/runtime/session-events.ts",
    "apps/cli/src/runtime/tool-policies.ts"
)

if ($SourceMode -eq "auto") {
    $SourceMode = if ($Mode -in @("build", "package")) { "origin-main" } else { "worktree" }
}
if ($Mode -in @("build", "package") -and $SourceMode -ne "origin-main") {
    throw "Build/package modes require -SourceMode origin-main so candidate artifacts are never assembled from an uncommitted worktree."
}
$SourceRef = if ($SourceMode -eq "origin-main") { "origin/main" } else { "WORKTREE" }

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
        throw "git failed in ${Root}: $($result.command) $([Environment]::NewLine)$($result.output -join [Environment]::NewLine)"
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

function Get-SourceText {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][ValidateSet("worktree", "origin-main")][string]$SourceMode,
        [switch]$AllowMissing
    )
    if ($SourceMode -eq "worktree") {
        $full = Join-Path $Root $Path
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
            if ($AllowMissing) { return $null }
            throw "source file missing from worktree: $full"
        }
        return Get-Content -LiteralPath $full -Raw
    }

    $spec = "{0}:{1}" -f "origin/main", $Path
    $result = Invoke-Git -Root $Root -Arguments @("show", $spec) -AllowFailure
    if ($result.exit_code -ne 0) {
        if ($AllowMissing) { return $null }
        throw "source file missing from origin/main: $Path"
    }
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
    param(
        [string]$Id,
        [bool]$Passed,
        [string]$Classification,
        [string]$Detail,
        [bool]$Blocking = $true
    )
    [pscustomobject]@{
        id = $Id
        passed = $Passed
        blocking = $Blocking
        classification = $Classification
        detail = $Detail
    }
}

function Test-IntegrationContracts {
    param(
        [string]$AgentRoot,
        [string]$ClientRoot,
        [ValidateSet("worktree", "origin-main")][string]$SourceMode
    )

    $productEntry = Get-SourceText -Root $AgentRoot -Path "lbe_guard_inspector/product_entry.py" -SourceMode $SourceMode
    $toolRuntime = Get-SourceText -Root $AgentRoot -Path "lbe_guard_inspector/runtime/tool_orchestration.py" -SourceMode $SourceMode
    $productTests = Get-SourceText -Root $AgentRoot -Path "tests/test_product_entry.py" -SourceMode $SourceMode
    $history = Get-SourceText -Root $AgentRoot -Path "lbe_guard_inspector/memory/operational_history.py" -SourceMode $SourceMode -AllowMissing
    $childProductTests = Get-SourceText -Root $AgentRoot -Path "tests/test_child_agent_product_seam.py" -SourceMode $SourceMode -AllowMissing
    $historyTests = Get-SourceText -Root $AgentRoot -Path "tests/test_operational_history.py" -SourceMode $SourceMode -AllowMissing

    # Rust/Ratatui remains a reference/integration client. It is still checked for boundary drift,
    # but it is no longer treated as the primary LBE product surface.
    $wrapper = Get-SourceText -Root $ClientRoot -Path "src/wrapper.rs" -SourceMode $SourceMode
    $types = Get-SourceText -Root $ClientRoot -Path "src/types.rs" -SourceMode $SourceMode
    $app = Get-SourceText -Root $ClientRoot -Path "src/app.rs" -SourceMode $SourceMode
    $main = Get-SourceText -Root $ClientRoot -Path "src/main.rs" -SourceMode $SourceMode
    $requests = Get-SourceText -Root $ClientRoot -Path "src/requests.rs" -SourceMode $SourceMode

    # The active product surface uses bundled Cline CLI mechanics under LBE branding and authority.
    $clineAdapter = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/runtime/lbe-tool-adapter.ts" -SourceMode $SourceMode -AllowMissing
    $clineRunAgent = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/runtime/run-agent.ts" -SourceMode $SourceMode -AllowMissing
    $clineAdapterTests = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/runtime/lbe-tool-adapter.test.ts" -SourceMode $SourceMode -AllowMissing
    $clineWelcome = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/tui/interactive-welcome.ts" -SourceMode $SourceMode -AllowMissing
    $clineKeyboard = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/tui/keyboard-map.ts" -SourceMode $SourceMode -AllowMissing
    $clineOnboarding = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/tui/views/onboarding/screens.tsx" -SourceMode $SourceMode -AllowMissing
    $clineStatusBar = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/tui/components/status-bar.tsx" -SourceMode $SourceMode -AllowMissing
    $clineRoot = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/tui/root.tsx" -SourceMode $SourceMode -AllowMissing
    $clineIdentity = Get-SourceText -Root $ClientRoot -Path "cline/apps/cli/src/tui/components/lbe-identity.tsx" -SourceMode $SourceMode -AllowMissing

    $checks = [System.Collections.Generic.List[object]]::new()

    $productCommands = @("start", "turn", "control", "tool", "authorization", "capabilities", "export")
    $missingCommands = @($productCommands | Where-Object { $productEntry -notmatch ('"' + [regex]::Escape($_) + '"') })
    $checks.Add((New-ContractCheck -Id "lbe.product_commands" -Passed ($missingCommands.Count -eq 0) -Classification $(if ($missingCommands.Count -eq 0) { "CONNECTED" } else { "MISSING" }) -Detail $(if ($missingCommands.Count -eq 0) { "Published Agent Wall product-entry command surface is present." } else { "Missing commands: $($missingCommands -join ', ')" })))

    $wrapperUsesProductEntry = $wrapper.Contains("lbe_guard_inspector.product_entry")
    $checks.Add((New-ContractCheck -Id "tui.real_wrapper_boundary" -Passed $wrapperUsesProductEntry -Classification $(if ($wrapperUsesProductEntry) { "CONNECTED" } else { "MISSING" }) -Detail "Rust RealLbeWrapper must route through the canonical Agent Wall product entry."))

    $readOnlyRuntimeMarkers = @(
        "registry.register(workspace_read_spec()",
        "registry.register(workspace_list_spec()",
        "registry.register(workspace_glob_spec()",
        "registry.register(workspace_search_spec()"
    )
    $readOnlyClientTools = @("workspace.read", "workspace.list", "workspace.glob", "workspace.search")
    $missingRuntimeMarkers = @($readOnlyRuntimeMarkers | Where-Object { -not $productEntry.Contains($_) })
    $missingClientTools = @($readOnlyClientTools | Where-Object { -not $wrapper.Contains($_) })
    $readOnlyConnected = ($missingRuntimeMarkers.Count -eq 0) -and ($missingClientTools.Count -eq 0)
    $readOnlyDetail = if ($readOnlyConnected) {
        "Read-only workspace capabilities are registered by their canonical Agent Wall specs and routed by the Rust client."
    }
    else {
        "Missing runtime registrations: $($missingRuntimeMarkers -join ', '); missing Rust tool IDs: $($missingClientTools -join ', ')."
    }
    $checks.Add((New-ContractCheck -Id "workspace.readonly_tools" -Passed $readOnlyConnected -Classification $(if ($readOnlyConnected) { "CONNECTED" } else { "PARTIAL" }) -Detail $readOnlyDetail))

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

    # Cline is a behavior/reference source only. LetterBlack owns product identity,
    # session truth, authorization, governed execution, receipts, and completion.
    # These checks verify that the selected Rust surface has the same categories of
    # interaction that make an agent CLI usable: interactive chat, sessions,
    # provider/model selection, approvals, event projection, and tool activity.
    $cliSurfaceMarkers = @(
        "lbe                         Start the TUI",
        "lbe [project]               Start the TUI in a project",
        "lbe run",
        "--model PROVIDER/MODEL",
        "--agent build|plan|audit",
        "--session SESSION_ID",
        "--continue",
        "--json"
    )
    $missingCliSurface = @($cliSurfaceMarkers | Where-Object { -not $main.Contains($_) })
    $checks.Add((New-ContractCheck -Id "tui.cli_launch_surface" -Passed ($missingCliSurface.Count -eq 0) -Classification $(if ($missingCliSurface.Count -eq 0) { "CONNECTED" } else { "PARTIAL" }) -Detail $(if ($missingCliSurface.Count -eq 0) { "Interactive, project, headless, provider/model, mode, session, continuation, and JSON launch surfaces are present." } else { "Missing CLI markers: $($missingCliSurface -join ', ')" })))

    $navigationCommands = @(
        "/provider", "/models", "/sessions", "/mcp", "/tools", "/processes",
        "/activity", "/evidence", "/receipts", "/changes", "/memory", "/doctor", "/help"
    )
    $missingNavigation = @($navigationCommands | Where-Object { -not $app.Contains('"' + $_ + '"') })
    $checks.Add((New-ContractCheck -Id "tui.navigation_surfaces" -Passed ($missingNavigation.Count -eq 0) -Classification $(if ($missingNavigation.Count -eq 0) { "PRESENT" } else { "PARTIAL" }) -Detail $(if ($missingNavigation.Count -eq 0) { "All selected navigation/diagnostic surfaces are present in the Rust UI." } else { "Missing navigation commands: $($missingNavigation -join ', ')" })))

    $governedCommands = @(
        "/open", "/read", "/tree", "/list", "/glob", "/find", "/search",
        "/patch", "/run", "/authorize", "/audit", "/mode", "/new", "/clear", "/quit"
    )
    $missingGoverned = @($governedCommands | Where-Object { -not $app.Contains('"' + $_ + '"') })
    $checks.Add((New-ContractCheck -Id "tui.governed_command_surfaces" -Passed ($missingGoverned.Count -eq 0) -Classification $(if ($missingGoverned.Count -eq 0) { "PRESENT" } else { "PARTIAL" }) -Detail $(if ($missingGoverned.Count -eq 0) { "Governed workspace, authorization, mode, session, and lifecycle command surfaces are present." } else { "Missing governed commands: $($missingGoverned -join ', ')" })))

    $coreRealRoutes = @(
        "UserRequest::RefreshProviderCatalog",
        "UserRequest::SelectModel",
        "UserRequest::ListSessions",
        "UserRequest::ResumeSession",
        "UserRequest::RefreshMcpRegistry",
        "UserRequest::RunDiagnostics",
        "UserRequest::InspectWorkspace",
        "UserRequest::ListWorkspace",
        "UserRequest::GlobWorkspace",
        "UserRequest::SearchWorkspace",
        "UserRequest::PatchWorkspace",
        "UserRequest::RunRegisteredProcess",
        "UserRequest::Approve",
        "UserRequest::Reject",
        "UserRequest::SubmitTask"
    )
    $missingRealRoutes = @($coreRealRoutes | Where-Object { -not $wrapper.Contains($_) })
    $checks.Add((New-ContractCheck -Id "tui.real_runtime_core_routes" -Passed ($missingRealRoutes.Count -eq 0) -Classification $(if ($missingRealRoutes.Count -eq 0) { "CONNECTED" } else { "PARTIAL" }) -Detail $(if ($missingRealRoutes.Count -eq 0) { "Core conversational, provider/model, session, MCP, diagnostics, workspace, process, and approval requests route through RealLbeWrapper." } else { "Missing RealLbeWrapper routes: $($missingRealRoutes -join ', ')" })))

    $explicitlyDeferred = @(
        "provider configuration",
        "provider removal",
        "checkpoint comparison",
        "checkpoint restore",
        "context compaction",
        "session memory operations",
        "browser chat"
    )
    $deferredPresent = @($explicitlyDeferred | Where-Object { $wrapper.Contains('unsupported_real_request("' + $_ + '")') })
    $checks.Add((New-ContractCheck -Id "tui.deferred_scaffolding_truth" -Passed $true -Blocking $false -Classification $(if ($deferredPresent.Count -eq 0) { "NONE" } else { "EXPLICITLY_UNAVAILABLE" }) -Detail $(if ($deferredPresent.Count -eq 0) { "No selected deferred real-runtime scaffolding remains." } else { "Still explicitly unavailable in the real wrapper: $($deferredPresent -join ', '). These surfaces must not be represented as connected." })))

    $requestContractPresent = $requests.Contains("SubmitTask") -and $requests.Contains("PatchWorkspace") -and $requests.Contains("Approve") -and $requests.Contains("Reject")
    $checks.Add((New-ContractCheck -Id "tui.typed_request_contract" -Passed $requestContractPresent -Classification $(if ($requestContractPresent) { "CONNECTED" } else { "PARTIAL" }) -Detail "Typed request contract must cover conversational task submission, governed patching, and approval decisions."))

    $childOwnerPresent = $history -and
        $history.Contains("create_child_agent_run") -and
        $history.Contains("start_child_agent_run") -and
        $history.Contains("finalize_child_agent_run")
    $checks.Add((New-ContractCheck -Id "lbe.child_agent.owner" -Passed ([bool]$childOwnerPresent) -Classification $(if ($childOwnerPresent) { "OWNER_PRESENT" } else { "MISSING" }) -Detail "ChildAgentRun lifecycle must reuse SessionOperationalHistory rather than introducing a second child state machine."))

    $childProductSeam = $productEntry.Contains("child_agent") -and
        $productEntry.Contains("create") -and
        $productEntry.Contains("started") -and
        $productEntry.Contains("complete") -and
        $productEntry.Contains("failed") -and
        $productEntry.Contains("cancel")
    $checks.Add((New-ContractCheck -Id "lbe.child_agent.product_seam" -Passed $childProductSeam -Classification $(if ($childProductSeam) { "REGISTERED" } else { "MISSING" }) -Detail "LBE product entry must expose create/started/complete/failed/cancel as thin adapters over the existing child lifecycle owner."))

    $childProofPresent = $childProductTests -and $historyTests -and
        $childProductTests.Contains("child_agent") -and
        $historyTests.Contains("child_agent")
    $checks.Add((New-ContractCheck -Id "lbe.child_agent.test_contract" -Passed ([bool]$childProofPresent) -Classification $(if ($childProofPresent) { "TEST_PROOF_PRESENT" } else { "MISSING" }) -Detail "Focused product-seam and lifecycle-owner regression tests must be present."))

    $clineSurfacePresent = $clineAdapter -and $clineRunAgent -and $clineAdapterTests
    $checks.Add((New-ContractCheck -Id "cline.embedded_surface.present" -Passed ([bool]$clineSurfacePresent) -Classification $(if ($clineSurfacePresent) { "PRESENT" } else { "MISSING" }) -Detail "Bundled Cline CLI mechanics are the active LBE CLI/TUI implementation surface; absence blocks current product proof."))

    $clineSpawnBinding = $clineSurfacePresent -and
        $clineAdapter.Contains("child_agent") -and
        $clineAdapter.Contains("spawn_operation_id") -and
        $clineRunAgent.Contains("child_agent_spawn")
    $checks.Add((New-ContractCheck -Id "cline.child_spawn.lbe_admission" -Passed ([bool]$clineSpawnBinding) -Classification $(if ($clineSpawnBinding) { "BOUND_TO_LBE" } else { "MISSING" }) -Detail "Cline delegated-agent execution must cross the LBE child_agent admission seam before child execution."))

    $governedChildSurface = $clineSpawnBinding -and
        $clineAdapter.Contains("childAgentGovernedToolSurface") -and
        $clineAdapter.Contains("createLbeToolProxies") -and
        -not $clineAdapter.Contains("createBuiltinTools(") -and
        -not $clineRunAgent.Contains("createBuiltinTools(")
    $checks.Add((New-ContractCheck -Id "cline.child_tools.lbe_only" -Passed ([bool]$governedChildSurface) -Classification $(if ($governedChildSurface) { "FAIL_CLOSED" } else { "BYPASS_RISK" }) -Detail "Delegated children must receive only LBE-governed proxy tools; native Cline tool construction must not be reachable from the LBE child integration seam."))

    $recursiveSpawnGuard = $clineSpawnBinding -and
        $clineAdapter.Contains("LBE_ALLOW_RECURSIVE_SPAWN") -and
        ($clineAdapter.Contains("depth") -or $clineAdapter.Contains("DEPTH"))
    $checks.Add((New-ContractCheck -Id "cline.child_spawn.recursion_default_deny" -Passed ([bool]$recursiveSpawnGuard) -Classification $(if ($recursiveSpawnGuard) { "GUARDED" } else { "UNPROVEN" }) -Detail "Recursive child spawning must remain denied by default unless explicitly authorized by the LBE integration policy."))

    $lifecycleCalls = $clineSpawnBinding -and
        $clineAdapter.Contains("started") -and
        $clineAdapter.Contains("complete") -and
        $clineAdapter.Contains("failed") -and
        $clineAdapter.Contains("cancel")
    $checks.Add((New-ContractCheck -Id "cline.child_spawn.lifecycle_projection" -Passed ([bool]$lifecycleCalls) -Classification $(if ($lifecycleCalls) { "PRESENT" } else { "PARTIAL" }) -Detail "Cline child execution must project started and terminal outcomes through LBE."))

    $uiFilesPresent = $clineWelcome -and $clineKeyboard -and $clineOnboarding -and $clineStatusBar -and $clineRoot -and $clineIdentity
    $visibleUi = @($clineWelcome, $clineKeyboard, $clineOnboarding, $clineStatusBar, $clineRoot, $clineIdentity) -join [Environment]::NewLine
    $brandingLeaks = @("Welcome to Cline", "Exit Cline", "Cline Hub", "ClinePass:") | Where-Object { $visibleUi.Contains($_) }
    $identityPresent = $uiFilesPresent -and
        $visibleUi.Contains("Welcome to LBE") -and
        $visibleUi.Contains("Exit LBE") -and
        $visibleUi.Contains("Lockstep Boundry Engine") -and
        $visibleUi.Contains("LETTERBLACK")
    $brandingPass = $uiFilesPresent -and ($brandingLeaks.Count -eq 0) -and $identityPresent
    $checks.Add((New-ContractCheck -Id "lbe.ui.branding_contract" -Passed ([bool]$brandingPass) -Classification $(if ($brandingPass) { "LBE_ONLY" } elseif (-not $uiFilesPresent) { "MISSING" } else { "FAIL" }) -Detail $(if ($brandingLeaks.Count) { "Visible Cline branding leaks: $($brandingLeaks -join ', ')" } elseif (-not $identityPresent) { "Required LBE / Lockstep Boundry Engine / LETTERBLACK identity markers are incomplete." } else { "Active CLI/TUI surface is LBE-branded." })))

    $teamPremature = $clineWelcome -and $clineWelcome.Contains("Start the task with agent team")
    $checks.Add((New-ContractCheck -Id "lbe.ui.subagent_exposure" -Passed (-not [bool]$teamPremature) -Classification $(if ($teamPremature) { "PREMATURE_EXPOSURE" } else { "NOT_EXPOSED" }) -Detail "Do not advertise /team as generally available until installed governed child-agent acceptance passes."))

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
        $agentTests = [System.Collections.Generic.List[string]]::new()
        @(
            "tests/test_authorization_resolver.py",
            "tests/test_tool_orchestration.py",
            "tests/test_product_entry.py",
            "tests/test_provider_continuation.py"
        ) | ForEach-Object { $agentTests.Add($_) }
        foreach ($candidate in @("tests/test_child_agent_product_seam.py", "tests/test_operational_history.py")) {
            if (Test-Path -LiteralPath (Join-Path $AgentStage $candidate) -PathType Leaf) {
                $agentTests.Add($candidate)
            }
            else {
                $proofs.Add([pscustomobject]@{ id = "agent.$([IO.Path]::GetFileNameWithoutExtension($candidate))"; status = "BLOCKED"; exit_code = $null; command = "pytest"; output = @("required child-agent proof missing: $candidate") })
            }
        }
        $agent = Invoke-Native -FilePath $python.Source -WorkingDirectory $AgentStage -Arguments (@("-m", "pytest", "-q") + @($agentTests))
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
    $clineRoot = Join-Path $TuiStage "cline\apps\cli"
    if (-not (Test-Path -LiteralPath $clineRoot -PathType Container)) {
        $proofs.Add([pscustomobject]@{ id = "cline.subagent_tests"; status = "BLOCKED"; exit_code = $null; command = "npx vitest"; output = @("bundled Cline CLI source missing: $clineRoot") })
        $proofs.Add([pscustomobject]@{ id = "cline.typecheck"; status = "BLOCKED"; exit_code = $null; command = "npm run typecheck"; output = @("bundled Cline CLI source missing") })
    }
    else {
        $npx = Get-Command npx -ErrorAction SilentlyContinue
        if (-not $npx) {
            $proofs.Add([pscustomobject]@{ id = "cline.subagent_tests"; status = "BLOCKED"; exit_code = $null; command = "npx"; output = @("npx not found") })
        }
        else {
            $clineTests = Invoke-Native -FilePath $npx.Source -WorkingDirectory $clineRoot -Arguments @("vitest", "run", "src/runtime/lbe-tool-adapter.test.ts", "src/runtime/run-agent.test.ts")
            $proofs.Add([pscustomobject]@{ id = "cline.subagent_tests"; status = $(if ($clineTests.exit_code -eq 0) { "PASS" } else { "FAIL" }); exit_code = $clineTests.exit_code; command = $clineTests.command; output = $clineTests.output })
        }
        $npm = Get-Command npm -ErrorAction SilentlyContinue
        if (-not $npm) {
            $proofs.Add([pscustomobject]@{ id = "cline.typecheck"; status = "BLOCKED"; exit_code = $null; command = "npm"; output = @("npm not found") })
        }
        else {
            $typecheck = Invoke-Native -FilePath $npm.Source -WorkingDirectory $clineRoot -Arguments @("run", "typecheck")
            $proofs.Add([pscustomobject]@{ id = "cline.typecheck"; status = $(if ($typecheck.exit_code -eq 0) { "PASS" } else { "FAIL" }); exit_code = $typecheck.exit_code; command = $typecheck.command; output = $typecheck.output })
        }
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
    Copy-Item -LiteralPath (Join-Path $workerSource "worker.mjs") -Destination $workerOut
    Copy-Item -LiteralPath (Join-Path $workerSource "package.json") -Destination $workerOut
    Copy-Item -LiteralPath (Join-Path $workerSource "package-lock.json") -Destination $workerOut
    $npm = Get-Command npm -ErrorAction Stop
    $npmCi = Invoke-Native -FilePath $npm.Source -WorkingDirectory $workerOut -Arguments @("ci", "--omit=dev")
    if ($npmCi.exit_code -ne 0) { throw "Cline worker dependency provisioning failed." }

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

function Write-Launcher {
    param([string]$PackageRoot)
    $launcher = @'
param(
    [Parameter(Mandatory)][string]$Project,
    [Parameter(Mandatory)][string]$Database,
    [Parameter(Mandatory)][string]$ProviderConfig,
    [string]$CapabilityRegistry,
    [string]$SessionId,
    [ValidateSet("build", "plan", "audit")][string]$Agent = "build",
    [string]$Model,
    [switch]$Continue,
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "LetterBlack\LBE")
)

$ErrorActionPreference = "Stop"
$client = Join-Path $InstallRoot "lbe.exe"
$python = Join-Path $InstallRoot "venv\Scripts\python.exe"
$mcpConfigPath = Join-Path $InstallRoot "config\mcp.json"
if (Test-Path -LiteralPath $mcpConfigPath -PathType Leaf) {
    $mcp = Get-Content -LiteralPath $mcpConfigPath -Raw | ConvertFrom-Json
    if ($mcp.python) { $env:LBE_BIRDEYE_MCP_PYTHON = [string]$mcp.python }
    if ($mcp.server) { $env:LBE_BIRDEYE_MCP_SERVER = [string]$mcp.server }
}
if (-not (Test-Path -LiteralPath $client -PathType Leaf)) { throw "Installed Rust client missing: $client" }
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Installed LBE Python runtime missing: $python" }
if (-not (Test-Path -LiteralPath $Project -PathType Container)) { throw "Project workspace missing: $Project" }
if (-not (Test-Path -LiteralPath $ProviderConfig -PathType Leaf)) { throw "Provider config missing: $ProviderConfig" }

$env:LBE_RUNTIME = "real"
$env:LBE_WALL_ROOT = $InstallRoot
$env:LBE_WALL_PYTHON = $python
$env:LBE_TARGET_WORKSPACE = [IO.Path]::GetFullPath($Project)
$env:LBE_WALL_DATABASE = [IO.Path]::GetFullPath($Database)
$env:LBE_PROVIDER_CONFIG = [IO.Path]::GetFullPath($ProviderConfig)
if ($CapabilityRegistry) {
    if (-not (Test-Path -LiteralPath $CapabilityRegistry -PathType Leaf)) { throw "Capability registry missing: $CapabilityRegistry" }
    $env:LBE_CAPABILITY_REGISTRY = [IO.Path]::GetFullPath($CapabilityRegistry)
}
if ($SessionId) { $env:LBE_SESSION_ID = $SessionId } else { Remove-Item Env:LBE_SESSION_ID -ErrorAction SilentlyContinue }

$clientArgs = @($env:LBE_TARGET_WORKSPACE, "--agent", $Agent)
if ($Model) { $clientArgs += @("--model", $Model) }
if ($SessionId) { $clientArgs += @("--session", $SessionId) }
if ($Continue) { $clientArgs += "--continue" }

& $client @clientArgs
exit $LASTEXITCODE
'@
    Set-Content -LiteralPath (Join-Path $PackageRoot "lbe-launch.ps1") -Value $launcher -Encoding UTF8
}

function Write-Installer {
    param([string]$PackageRoot)
    $installer = @'
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "LetterBlack\LBE"),
    [string]$BirdEyeServer,
    [string]$BirdEyePython,
    [string]$Project
)
$ErrorActionPreference = "Stop"
$venv = Join-Path $InstallRoot "venv"
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
python -m venv $venv
$python = Join-Path $venv "Scripts\python.exe"
$wheel = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot "runtime") -Filter "*.whl" | Select-Object -First 1
if (-not $wheel) { throw "LBE runtime wheel missing" }
& $python -m pip install --no-deps $wheel.FullName
if ($LASTEXITCODE -ne 0) { throw "LBE runtime install failed" }
$config = Join-Path $InstallRoot "config"
New-Item -ItemType Directory -Path $config -Force | Out-Null
$server = $BirdEyeServer
if (-not $server -and $env:LBE_BIRDEYE_MCP_SERVER) { $server = $env:LBE_BIRDEYE_MCP_SERVER }
if (-not $server) {
    $candidates = @(
        (Join-Path $InstallRoot "mcp\birdeye\mcp_server.py"),
        (Join-Path $PSScriptRoot "mcp\birdeye\mcp_server.py"),
        "C:\MCP Local\Letterblack_BirdEye\mcp_server.py"
    )
    $server = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if ($server) { $server = [IO.Path]::GetFullPath($server) }
$mcpPython = if ($BirdEyePython) { $BirdEyePython } elseif ($env:LBE_BIRDEYE_MCP_PYTHON) { $env:LBE_BIRDEYE_MCP_PYTHON } else { $python }
$mcpStatus = if ($server -and (Test-Path -LiteralPath $server -PathType Leaf) -and (Test-Path -LiteralPath $mcpPython -PathType Leaf)) { "CONFIGURED" } else { "UNAVAILABLE_CONFIGURATION_REQUIRED" }
$registryPath = Join-Path $config "capability-registry.json"
if (-not (Test-Path -LiteralPath $registryPath -PathType Leaf)) {
    @{ schema_version = 1; integrations = @() } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $registryPath -Encoding UTF8
}
@{
    schema_version = 1
    provider = "birdeye"
    status = $mcpStatus
    server = $server
    python = $mcpPython
    transport = "stdio"
    authority = "LBE ToolRegistry and authorization"
    index_owner = "BirdEye MCP workspace/index projection"
    skills_role = "procedural guidance only"
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $config "mcp.json") -Encoding UTF8
@{
    schema_version = 1
    workspace = $Project
    database = (Join-Path $InstallRoot "state\lbe.sqlite3")
    capability_registry = $registryPath
    mcp_configuration = (Join-Path $config "mcp.json")
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $config "runtime.json") -Encoding UTF8
$site = & $python -c "import pathlib,lbe_guard_inspector; print(pathlib.Path(lbe_guard_inspector.__file__).parent)"
if ($LASTEXITCODE -ne 0) { throw "Unable to resolve installed LBE package" }
$workerTarget = Join-Path $site "runtime\cline_worker"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "cline-worker\node_modules") -Destination $workerTarget -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "client\lbe.exe") -Destination (Join-Path $InstallRoot "lbe.exe") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "lbe-launch.ps1") -Destination (Join-Path $InstallRoot "lbe-launch.ps1") -Force
Write-Host "Installed LetterBlack LBE to $InstallRoot"
Write-Host "Runtime CLI: $(Join-Path $venv 'Scripts\lbe.exe')"
Write-Host "Rust client: $(Join-Path $InstallRoot 'lbe.exe')"
Write-Host "Real-runtime launcher: $(Join-Path $InstallRoot 'lbe-launch.ps1')"
Write-Host "MCP configuration: $(Join-Path $config 'mcp.json') [$mcpStatus]"
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

function Test-PackageArchive {
    param(
        [Parameter(Mandatory)][string]$ZipPath,
        [Parameter(Mandatory)][string]$VerificationRoot
    )
    if (Test-Path -LiteralPath $VerificationRoot) { Remove-Item -LiteralPath $VerificationRoot -Recurse -Force }
    New-Item -ItemType Directory -Path $VerificationRoot -Force | Out-Null
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $VerificationRoot -Force

    $checksumPath = Join-Path $VerificationRoot "checksums.json"
    if (-not (Test-Path -LiteralPath $checksumPath -PathType Leaf)) {
        throw "Package verification failed: checksums.json missing from archive."
    }
    $expected = @(Get-Content -LiteralPath $checksumPath -Raw | ConvertFrom-Json)
    $errors = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $expected) {
        $relative = ([string]$entry.path).Replace("/", "\")
        $file = Join-Path $VerificationRoot $relative
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            $errors.Add("missing: $($entry.path)")
            continue
        }
        $actualHash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        $actualBytes = (Get-Item -LiteralPath $file).Length
        if ($actualHash -ne [string]$entry.sha256) { $errors.Add("sha256 mismatch: $($entry.path)") }
        if ($actualBytes -ne [int64]$entry.bytes) { $errors.Add("size mismatch: $($entry.path)") }
    }

    $result = [pscustomobject]@{
        status = $(if ($errors.Count -eq 0) { "PASS" } else { "FAIL" })
        archive = $ZipPath
        verified_file_count = $expected.Count
        errors = @($errors)
    }
    Remove-Item -LiteralPath $VerificationRoot -Recurse -Force
    return $result
}

$agent = Assert-Workspace -Root $AgentWallRoot -Repository $AgentWallRepository
$tui = Assert-Workspace -Root $TuiRoot -Repository $TuiRepository

if ($agent.worktree_count -ne 1) { throw "Agent Wall must have exactly one registered worktree; found $($agent.worktree_count)." }
if ($tui.worktree_count -ne 1) { throw "LBE TUI must have exactly one registered worktree; found $($tui.worktree_count)." }

$contracts = Test-IntegrationContracts -AgentRoot $AgentWallRoot -ClientRoot $TuiRoot -SourceMode $SourceMode
$structuralPass = @($contracts | Where-Object { $_.blocking -and -not $_.passed }).Count -eq 0

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$stageRoot = Join-Path $OutputRoot "_staging"
$agentStage = Join-Path $stageRoot "agent-wall"
$tuiStage = Join-Path $stageRoot "lbe-tui"
$proofs = @()
$build = $null
$packagePath = $null
$packageVerification = $null

if ($Mode -in @("prove", "build", "package")) {
    if ($SourceMode -eq "worktree") {
        $agentStage = $AgentWallRoot
        $tuiStage = $TuiRoot
    }
    else {
        Export-OriginMain -Root $AgentWallRoot -Destination $agentStage
        Export-OriginMain -Root $TuiRoot -Destination $tuiStage
    }
    $proofs = Invoke-Proof -AgentStage $agentStage -TuiStage $tuiStage
}

$proofPass = if ($proofs.Count -eq 0) { $false } else { @($proofs | Where-Object { $_.status -ne "PASS" }).Count -eq 0 }

if ($Mode -in @("build", "package")) {
    if (-not $structuralPass) { throw "Product build blocked: structural integration checks failed." }
    if (-not $proofPass) { throw "Product build blocked: proof suite did not pass." }
    $packageRoot = Join-Path $OutputRoot "LetterBlack-LBE"
    $build = Build-Product -AgentStage $agentStage -TuiStage $tuiStage -BuildRoot $packageRoot
    Write-Installer -PackageRoot $packageRoot
    Write-Launcher -PackageRoot $packageRoot
}

$manifest = [ordered]@{
    schema_version = $SchemaVersion
    product = "LetterBlack LBE"
    generated_at = [DateTimeOffset]::UtcNow.ToString("o")
    generator = "tools/lbe_product_integration.ps1"
    mode = $Mode
    verification_source = [ordered]@{
        mode = $SourceMode
        ref = $SourceRef
        rule = "check/prove may validate the assembled worktree; build/package are forced to origin/main and cannot package uncommitted state."
    }
    authority = [ordered]@{
        rule = "Agent Wall is the runtime/governance authority. The LBE CLI/TUI uses bundled Cline mechanics for cognition/provider/model/agent execution. Rust/Ratatui is a reference/integration client. This script owns no runtime decision."
        agent_wall = $agent
        lbe_cli_repository = $tui
        rust_reference_client = [ordered]@{ repository = $TuiRepository; role = "REFERENCE_INTEGRATION_CLIENT"; path = "src/" }
    }
    product_surface = [ordered]@{
        name = "LBE CLI/TUI"
        full_name = "Lockstep Boundry Engine"
        brand = "LETTERBLACK"
        mechanics = "bundled Cline CLI"
        rule = "Cline implementation names may exist internally, but user-facing product identity is LBE and all capability/consequence authority remains with LBE."
    }
    cline_upstream_reference = [ordered]@{
        repository = $ClineReferenceRepository
        commit = $ClineReferenceCommit
        role = "UPSTREAM_REFERENCE_FOR_EMBEDDED_MECHANICS"
        rule = "Reuse Cline cognition/provider/model/delegated-agent mechanics without transferring session, authorization, governed execution, persistence, receipt, evidence, validation, or completion authority away from LBE."
        reference_files = $ClineReferenceFiles
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
    $packageVerification = Test-PackageArchive -ZipPath $zip -VerificationRoot (Join-Path $OutputRoot "_package-verify")
    $packageVerification | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputRoot "package-verification.json") -Encoding UTF8
    if ($packageVerification.status -ne "PASS") {
        throw "Package verification failed: $($packageVerification.errors -join '; ')"
    }
}

if (Test-Path -LiteralPath $stageRoot) { Remove-Item -LiteralPath $stageRoot -Recurse -Force }

Write-Host "=== LETTERBLACK PRODUCT INTEGRATION ==="
Write-Host "Mode: $Mode"
Write-Host "Verification source:      $SourceMode ($SourceRef)"
Write-Host "Agent Wall origin/main: $($agent.origin_main)"
Write-Host "Rust TUI origin/main:     $($tui.origin_main)"
Write-Host "Structural integration:   $structuralPass"
Write-Host "Proof pass:               $proofPass"
Write-Host "Cline mechanics reference: $ClineReferenceRepository@$ClineReferenceCommit"
Write-Host "Manifest:                  $manifestPath"
if ($packagePath) { Write-Host "Candidate package:         $packagePath" }
if ($packageVerification) { Write-Host "Package verification:      $($packageVerification.status)" }
Write-Host "Release ready:             False (external installed PTY/ConPTY acceptance is intentionally not fabricated)"

if (-not $structuralPass) { exit 2 }
if ($Mode -in @("prove", "build", "package") -and -not $proofPass) { exit 3 }
exit 0
