param(
    [ValidateSet("check", "prove", "build", "package")]
    [string]$Mode = "check",
    [ValidateSet("auto", "worktree", "origin-main")]
    [string]$SourceMode = "auto",
    [string]$AgentWallRoot = "C:\Agents-Memory-Tool-v6-integration",
    [string]$TuiRoot = (Join-Path $AgentWallRoot "apps\lbe-terminal"),
    [string]$OutputRoot = (Join-Path $PSScriptRoot "..\dist\product-integration"),
    [switch]$NoFetch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AgentWallRepository = "Letterblack0306/LBE_Presistent_Agent_wall"
$SchemaVersion = 2
$ClientCratePath = "apps\lbe-terminal"
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

    # Rust/Ratatui is the canonical visible LBE product client selected by the product owner
    # on 2026-09-18. It remains projection/control only; all authority-bearing consequences
    # continue through the canonical Agent Wall owners.
    # Single-project topology: the client crate is colocated at apps\lbe-terminal in the Agent Wall
    # repository, so client source paths are prefixed with the crate directory.
    $wrapper = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/src/wrapper.rs" -SourceMode $SourceMode
    $types = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/src/types.rs" -SourceMode $SourceMode
    $app = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/src/app.rs" -SourceMode $SourceMode
    $main = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/src/main.rs" -SourceMode $SourceMode
    $requests = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/src/requests.rs" -SourceMode $SourceMode

    # Cline CLI/OpenTUI source is optional reference/reuse material only. The product does not
    # require a copied Cline UI tree. Headless Cline reasoning/provider mechanics are owned by
    # the Agent Wall cline_worker path. Reference paths are intentionally retired from the
    # consolidated single-project layout; these optional reads resolve to $null when absent.
    $clineAdapter = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/runtime/lbe-tool-adapter.ts" -SourceMode $SourceMode -AllowMissing
    $clineRunAgent = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/runtime/run-agent.ts" -SourceMode $SourceMode -AllowMissing
    $clineAdapterTests = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/runtime/lbe-tool-adapter.test.ts" -SourceMode $SourceMode -AllowMissing
    $clineWelcome = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/interactive-welcome.ts" -SourceMode $SourceMode -AllowMissing
    $clineKeyboard = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/keyboard-map.ts" -SourceMode $SourceMode -AllowMissing
    $clineOnboarding = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/views/onboarding/screens.tsx" -SourceMode $SourceMode -AllowMissing
    $clineStatusBar = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/components/status-bar.tsx" -SourceMode $SourceMode -AllowMissing
    $clineRoot = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/root.tsx" -SourceMode $SourceMode -AllowMissing
    $clineIdentity = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/components/lbe-identity.tsx" -SourceMode $SourceMode -AllowMissing
    $clineHome = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/views/home-view.tsx" -SourceMode $SourceMode -AllowMissing
    $clineChat = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/views/chat-view.tsx" -SourceMode $SourceMode -AllowMissing
    $clineInput = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/components/input-bar.tsx" -SourceMode $SourceMode -AllowMissing
    $clineMessages = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/components/chat-message-list.tsx" -SourceMode $SourceMode -AllowMissing
    $clineLoader = Get-SourceText -Root $ClientRoot -Path "apps/lbe-terminal/cline/apps/cli/src/tui/components/letterblack-loader.tsx" -SourceMode $SourceMode -AllowMissing

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
    $checks.Add((New-ContractCheck -Id "cline.embedded_surface.present" -Blocking $false -Passed ([bool]$clineSurfacePresent) -Classification $(if ($clineSurfacePresent) { "PRESENT" } else { "MISSING" }) -Detail "Reference-only Cline CLI adapter/source presence. Absence does not block the selected Rust/Ratatui product surface; headless Cline runtime proof belongs to the Agent Wall worker/provider path."))

    $clineSpawnBinding = $clineSurfacePresent -and
        $clineAdapter.Contains("child_agent") -and
        $clineAdapter.Contains("spawn_operation_id") -and
        $clineRunAgent.Contains("child_agent_spawn")
    $checks.Add((New-ContractCheck -Id "cline.child_spawn.lbe_admission" -Blocking $false -Passed ([bool]$clineSpawnBinding) -Classification $(if ($clineSpawnBinding) { "BOUND_TO_LBE" } else { "MISSING" }) -Detail "Cline delegated-agent execution must cross the LBE child_agent admission seam before child execution."))

    $governedChildSurface = $clineSpawnBinding -and
        $clineAdapter.Contains("childAgentGovernedToolSurface") -and
        $clineAdapter.Contains("createLbeToolProxies") -and
        -not $clineAdapter.Contains("createBuiltinTools(") -and
        -not $clineRunAgent.Contains("createBuiltinTools(")
    $checks.Add((New-ContractCheck -Id "cline.child_tools.lbe_only" -Blocking $false -Passed ([bool]$governedChildSurface) -Classification $(if ($governedChildSurface) { "FAIL_CLOSED" } else { "BYPASS_RISK" }) -Detail "Delegated children must receive only LBE-governed proxy tools; native Cline tool construction must not be reachable from the LBE child integration seam."))

    $recursiveSpawnGuard = $clineSpawnBinding -and
        $clineAdapter.Contains("LBE_ALLOW_RECURSIVE_SPAWN") -and
        ($clineAdapter.Contains("depth") -or $clineAdapter.Contains("DEPTH"))
    $checks.Add((New-ContractCheck -Id "cline.child_spawn.recursion_default_deny" -Blocking $false -Passed ([bool]$recursiveSpawnGuard) -Classification $(if ($recursiveSpawnGuard) { "GUARDED" } else { "UNPROVEN" }) -Detail "Recursive child spawning must remain denied by default unless explicitly authorized by the LBE integration policy."))

    $lifecycleCalls = $clineSpawnBinding -and
        $clineAdapter.Contains("started") -and
        $clineAdapter.Contains("complete") -and
        $clineAdapter.Contains("failed") -and
        $clineAdapter.Contains("cancel")
    $checks.Add((New-ContractCheck -Id "cline.child_spawn.lifecycle_projection" -Blocking $false -Passed ([bool]$lifecycleCalls) -Classification $(if ($lifecycleCalls) { "PRESENT" } else { "PARTIAL" }) -Detail "Cline child execution must project started and terminal outcomes through LBE."))

    $uiFilesPresent = $clineWelcome -and $clineKeyboard -and $clineOnboarding -and $clineStatusBar -and $clineRoot -and $clineIdentity
    $visibleUi = @($clineWelcome, $clineKeyboard, $clineOnboarding, $clineStatusBar, $clineRoot, $clineIdentity) -join [Environment]::NewLine
    $brandingLeaks = @(@("Welcome to Cline", "Exit Cline", "Cline Hub", "ClinePass:") | Where-Object { $visibleUi.Contains($_) })
    $identityPresent = $uiFilesPresent -and
        $visibleUi.Contains("Welcome to LBE") -and
        $visibleUi.Contains("Exit LBE") -and
        $visibleUi.Contains("Lockstep Boundry Engine") -and
        $visibleUi.Contains("LETTERBLACK")
    $brandingPass = $uiFilesPresent -and ($brandingLeaks.Count -eq 0) -and $identityPresent
    $checks.Add((New-ContractCheck -Id "lbe.ui.branding_contract" -Blocking $false -Passed ([bool]$brandingPass) -Classification $(if ($brandingPass) { "LBE_ONLY" } elseif (-not $uiFilesPresent) { "MISSING" } else { "FAIL" }) -Detail $(if ($brandingLeaks.Count) { "Visible Cline branding leaks: $($brandingLeaks -join ', ')" } elseif (-not $identityPresent) { "Required LBE / Lockstep Boundry Engine / LETTERBLACK identity markers are incomplete." } else { "Active CLI/TUI surface is LBE-branded." })))

    # Branding alone is insufficient. The accepted LBE surface must not retain the
    # recognizable Cline centered hero/composer composition. Structural acceptance
    # requires the minimal LBE runtime shell: persistent status/header hierarchy,
    # [I] composer identity, bounded active-process stream, collapsed completed work,
    # and context projection. A renamed logo or recolored Cline home view must FAIL.
    $visualFilesPresent = $clineHome -and $clineChat -and $clineInput -and $clineMessages -and $clineLoader
    $clineHeroMarkers = @(
        'alignItems="center"',
        'justifyContent="center"',
        '<TrackedRobot',
        '<strong>What can I do for you?</strong>'
    )
    $clineHeroMarkerCount = @($clineHeroMarkers | Where-Object { $clineHome -and $clineHome.Contains($_) }).Count
    $lbeStructuralMarkers = @(
        [bool]($clineInput -and $clineInput.Contains("[I]")),
        [bool]($clineLoader -and ($clineLoader.Contains("bounce") -or $clineLoader.Contains("direction"))),
        [bool]($clineMessages -and $clineMessages.Contains("3") -and ($clineMessages.Contains("expand") -or $clineMessages.Contains("collapsed"))),
        [bool](($clineHome -and $clineHome.Contains("context")) -or ($clineStatusBar -and $clineStatusBar.Contains("context")))
    )
    $lbeStructuralPass = $visualFilesPresent -and ($clineHeroMarkerCount -lt 3) -and -not ($lbeStructuralMarkers -contains $false)
    $visualDetail = if (-not $visualFilesPresent) {
        "Reference Cline/LBE visual source files are absent; this is non-blocking for the selected Rust/Ratatui product surface."
    } elseif ($clineHeroMarkerCount -ge 3) {
        "Reference Cline UI retains its upstream hero/composer composition; this no longer determines product visual acceptance."
    } elseif ($lbeStructuralMarkers -contains $false) {
        "Reference Cline UI does not contain the complete LBE shell markers; product acceptance is evaluated on the Rust/Ratatui client."
    } else {
        "Reference Cline UI contains the historical LBE shell markers; this is informational only."
    }
    $checks.Add((New-ContractCheck -Id "lbe.ui.structural_differentiation" -Blocking $false -Passed ([bool]$lbeStructuralPass) -Classification $(if ($lbeStructuralPass) { "DISTINCT_LBE_SHELL" } else { "FAIL" }) -Detail $visualDetail))

    $teamPremature = $clineWelcome -and $clineWelcome.Contains("Start the task with agent team")
    $checks.Add((New-ContractCheck -Id "lbe.ui.subagent_exposure" -Blocking $false -Passed (-not [bool]$teamPremature) -Classification $(if ($teamPremature) { "PREMATURE_EXPOSURE" } else { "NOT_EXPOSED" }) -Detail "Do not advertise /team as generally available until installed governed child-agent acceptance passes."))

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
        $tuiTest = Invoke-Native -FilePath $cargo.Source -WorkingDirectory $TuiStage -Arguments @("test", "--locked")
        $proofs.Add([pscustomobject]@{ id = "tui.cargo_test"; status = $(if ($tuiTest.exit_code -eq 0) { "PASS" } else { "FAIL" }); exit_code = $tuiTest.exit_code; command = $tuiTest.command; output = $tuiTest.output })
        $fmt = Invoke-Native -FilePath $cargo.Source -WorkingDirectory $TuiStage -Arguments @("fmt", "--", "--check")
        $proofs.Add([pscustomobject]@{ id = "tui.cargo_fmt"; status = $(if ($fmt.exit_code -eq 0) { "PASS" } else { "FAIL" }); exit_code = $fmt.exit_code; command = $fmt.command; output = $fmt.output })
    }
    $clineRoot = Join-Path $TuiStage "cline\apps\cli"
    if (-not (Test-Path -LiteralPath $clineRoot -PathType Container)) {
        $proofs.Add([pscustomobject]@{ id = "cline.reference_tests"; status = "SKIP"; blocking = $false; exit_code = $null; command = "npx vitest"; output = @("reference Cline CLI source absent; not required by canonical Rust/Ratatui product surface") })
        $proofs.Add([pscustomobject]@{ id = "cline.reference_typecheck"; status = "SKIP"; blocking = $false; exit_code = $null; command = "npm run typecheck"; output = @("reference Cline CLI source absent; not required by canonical Rust/Ratatui product surface") })
    }
    else {
        $npx = Get-Command npx -ErrorAction SilentlyContinue
        if (-not $npx) {
            $proofs.Add([pscustomobject]@{ id = "cline.reference_tests"; status = "BLOCKED"; blocking = $false; exit_code = $null; command = "npx"; output = @("npx not found; reference-only check") })
        }
        else {
            $clineTests = Invoke-Native -FilePath $npx.Source -WorkingDirectory $clineRoot -Arguments @("vitest", "run", "src/runtime/lbe-tool-adapter.test.ts", "src/runtime/run-agent.test.ts")
            $proofs.Add([pscustomobject]@{ id = "cline.reference_tests"; status = $(if ($clineTests.exit_code -eq 0) { "PASS" } else { "FAIL" }); blocking = $false; exit_code = $clineTests.exit_code; command = $clineTests.command; output = $clineTests.output })
        }
        $npm = Get-Command npm -ErrorAction SilentlyContinue
        if (-not $npm) {
            $proofs.Add([pscustomobject]@{ id = "cline.reference_typecheck"; status = "BLOCKED"; blocking = $false; exit_code = $null; command = "npm"; output = @("npm not found; reference-only check") })
        }
        else {
            $typecheck = Invoke-Native -FilePath $npm.Source -WorkingDirectory $clineRoot -Arguments @("run", "typecheck")
            $proofs.Add([pscustomobject]@{ id = "cline.reference_typecheck"; status = $(if ($typecheck.exit_code -eq 0) { "PASS" } else { "FAIL" }); blocking = $false; exit_code = $typecheck.exit_code; command = $typecheck.command; output = $typecheck.output })
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
    [string]$Project,
    [string]$Database,
    [string]$ProviderConfig,
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

# Informational flags must pass through to the installed client without
# requiring a full runtime/session/provider bootstrap. They can arrive either
# as unbound $args or positionally bound to $Project / $Model.
$informational = @('--version', '-V', '--help', '-h')
$infoArg = $null
foreach ($candidate in @($args) + @($Project) + @($Model)) {
    if ($informational -contains $candidate) { $infoArg = $candidate; break }
}
if ($infoArg) {
    if (-not (Test-Path -LiteralPath $client -PathType Leaf)) { throw "Installed Rust client missing: $client" }
    & $client --version
    exit $LASTEXITCODE
}

$mcpConfigPath = Join-Path $InstallRoot "config\mcp.json"
if (Test-Path -LiteralPath $mcpConfigPath -PathType Leaf) {
    $mcp = Get-Content -LiteralPath $mcpConfigPath -Raw | ConvertFrom-Json
    if ($mcp.python) { $env:LBE_BIRDEYE_MCP_PYTHON = [string]$mcp.python }
    if ($mcp.server) { $env:LBE_BIRDEYE_MCP_SERVER = [string]$mcp.server }
}

# Installed runtime.json supplies the state/config defaults so the launcher is
# usable with zero mandatory arguments. Every default is composed from the
# installed tree, never from npm or any other package owner.
$runtimeConfig = $null
$runtimeConfigPath = Join-Path $InstallRoot "config\runtime.json"
if (Test-Path -LiteralPath $runtimeConfigPath -PathType Leaf) {
    $runtimeConfig = Get-Content -LiteralPath $runtimeConfigPath -Raw | ConvertFrom-Json
}

if (-not $Project) { $Project = (Get-Location).Path }
$workspaceFull = [IO.Path]::GetFullPath($Project)
if (-not (Test-Path -LiteralPath $workspaceFull -PathType Container)) { throw "Project workspace missing: $workspaceFull" }

if (-not $Database) {
    if ($runtimeConfig -and $runtimeConfig.database) { $Database = [string]$runtimeConfig.database }
    else { $Database = Join-Path $InstallRoot "state\lbe.sqlite3" }
}
if (-not $ProviderConfig) {
    if ($env:LBE_PROVIDER_CONFIG) { $ProviderConfig = $env:LBE_PROVIDER_CONFIG }
    elseif ($runtimeConfig -and $runtimeConfig.provider_configuration) { $ProviderConfig = [string]$runtimeConfig.provider_configuration }
    elseif (Test-Path -LiteralPath (Join-Path $InstallRoot "config\provider-config.json") -PathType Leaf) { $ProviderConfig = Join-Path $InstallRoot "config\provider-config.json" }
}
if (-not $CapabilityRegistry -and $runtimeConfig -and $runtimeConfig.capability_registry) { $CapabilityRegistry = [string]$runtimeConfig.capability_registry }
if (-not $SessionId -and $env:LBE_SESSION_ID) { $SessionId = $env:LBE_SESSION_ID }

if (-not (Test-Path -LiteralPath $client -PathType Leaf)) { throw "Installed Rust client missing: $client" }
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Installed LBE Python runtime missing: $python" }
if (-not (Test-Path -LiteralPath $ProviderConfig -PathType Leaf)) { throw "Provider config missing: $ProviderConfig" }

$env:LBE_RUNTIME = "real"
$env:LBE_WALL_ROOT = $InstallRoot
$env:LBE_WALL_PYTHON = $python
$env:LBE_TARGET_WORKSPACE = $workspaceFull
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
    [string]$Project,
    [string]$ProviderConfig
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
    provider_configuration = (Join-Path $config "provider-config.json")
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $config "runtime.json") -Encoding UTF8
$installedProviderConfig = Join-Path $config "provider-config.json"
if ($ProviderConfig -and (Test-Path -LiteralPath $ProviderConfig -PathType Leaf)) {
    Copy-Item -LiteralPath $ProviderConfig -Destination $installedProviderConfig -Force
    Write-Host "Installed provider configuration: $installedProviderConfig"
}
elseif (-not (Test-Path -LiteralPath $installedProviderConfig -PathType Leaf)) {
    @{
        endpoint = "http://127.0.0.1:1234/v1/chat/completions"
        model = "google/gemma-4-e4b"
        timeout_seconds = 120
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $installedProviderConfig -Encoding UTF8
    Write-Host "Generated default provider configuration (127.0.0.1:1234): $installedProviderConfig"
}
else {
    Write-Host "Provider configuration already present: $installedProviderConfig"
}
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

# --- Installed single-command contract: bin\lbe.cmd -> lbe-launch.ps1 -> lbe.exe ---
$binDir = Join-Path $InstallRoot "bin"
New-Item -ItemType Directory -Path $binDir -Force | Out-Null
$binCmd = Join-Path $binDir "lbe.cmd"
@"
@ECHO off
SETLOCAL
SET "LBE_INSTALL_ROOT=$InstallRoot"
powershell -NoProfile -ExecutionPolicy Bypass -File "%LBE_INSTALL_ROOT%\lbe-launch.ps1" %*
ENDLOCAL
"@ | Set-Content -LiteralPath $binCmd -Encoding ASCII
$binCmdFull = [IO.Path]::GetFullPath($binCmd)
if (-not (Test-Path -LiteralPath $binCmdFull -PathType Leaf)) { throw "Unable to create authoritative entrypoint: $binCmdFull" }

# Prepend %LOCALAPPDATA%\LetterBlack\LBE\bin to the user PATH, idempotently.
# Per product contract, never write into npm's shim directory and never
# replace the global Python console script. The LetterBlack bin dir merely
# wins resolution order.
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
$userPathEntries = @($userPath -split ';' | Where-Object { $_ -and $_.Trim() })
$binFull = [IO.Path]::GetFullPath($binDir)
if ($userPathEntries -notcontains $binFull) {
    $userPathEntries = @($binFull) + @($userPathEntries)
    [Environment]::SetEnvironmentVariable("Path", ($userPathEntries -join ";"), "User")
    Write-Host "Prepended user PATH entry: $binFull"
}
else {
    Write-Host "User PATH entry already present (idempotent): $binFull"
}

# Detect existing lbe collisions and report them explicitly without replacing.
$collisions = @()
$allLbe = Get-Command lbe -All -ErrorAction SilentlyContinue
foreach ($entry in $allLbe) {
    $src = ""
    try { $src = $entry.Source } catch { $src = [string]$entry.CommandType }
    $isCanonical = ($src -and $src -like "$binFull\lbe.cmd*")
    if (-not $isCanonical) {
        $collisions += $src
    }
}
if ($collisions.Count -gt 0) {
    Write-Host "Installed lbe collisions detected (NOT silently replaced):"
    foreach ($c in $collisions) { Write-Host "  - $c" }
}
else {
    Write-Host "No competing installed lbe entrypoints detected."
}
Write-Host "Authoritative PATH entrypoint: $binCmdFull"
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

if ($agent.worktree_count -ne 1) { throw "Agent Wall must have exactly one registered worktree; found $($agent.worktree_count)." }

# Single-project topology: the Rust/Ratatui client crate is colocated at apps\lbe-terminal in the
# Agent Wall repository. No separate TUI workspace/repository is required to build, launch,
# install, test, or operate the product.
$clientCrateProbe = if ($SourceMode -eq "worktree") {
    (Test-Path -LiteralPath (Join-Path $AgentWallRoot "apps\lbe-terminal\Cargo.toml") -PathType Leaf)
}
else {
    (Invoke-Git -Root $AgentWallRoot -Arguments @("show", "origin/main:apps/lbe-terminal/Cargo.toml") -AllowFailure).exit_code -eq 0
}
if (-not $clientCrateProbe) {
    throw "Rust client crate missing in Agent Wall repository: apps\lbe-terminal ($SourceMode)"
}

$contracts = Test-IntegrationContracts -AgentRoot $AgentWallRoot -ClientRoot $AgentWallRoot -SourceMode $SourceMode
$structuralPass = @($contracts | Where-Object { $_.blocking -and -not $_.passed }).Count -eq 0

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$stageRoot = Join-Path $OutputRoot "_staging"
$agentStage = if ($Mode -eq "check") { $AgentWallRoot } else { Join-Path $stageRoot "agent-wall" }
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
        $tuiStage = Join-Path $agentStage "apps\lbe-terminal"
    }
    $proofs = Invoke-Proof -AgentStage $agentStage -TuiStage $tuiStage
}

$proofPass = if ($proofs.Count -eq 0) { $false } else { @($proofs | Where-Object { ($_.blocking -ne $false) -and $_.status -ne "PASS" }).Count -eq 0 }

if ($Mode -in @("build", "package")) {
    if (-not $structuralPass) { throw "Product build blocked: structural integration checks failed." }
    if (-not $proofPass) { throw "Product build blocked: proof suite did not pass." }
    $packageRoot = Join-Path $OutputRoot "LetterBlack-LBE"
    $build = Build-Product -AgentStage $agentStage -TuiStage $tuiStage -BuildRoot $packageRoot
    Write-Installer -PackageRoot $packageRoot
    Write-Launcher -PackageRoot $packageRoot
}

function Get-GateField {
    param(
        [object]$Target,
        [string]$Name
    )
    if ($null -eq $Target) { return $null }
    $prop = $Target.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $null }
    return $prop.Value
}

function Get-GateStringField {
    param(
        [object]$Target,
        [string]$Name,
        [string]$Default = ""
    )
    $value = Get-GateField -Target $Target -Name $Name
    if ($null -eq $value) { return $Default }
    return [string]$value
}

$machineGatePath = Join-Path $agentStage ".lbe\governance\implementation-gates.json"
if (-not (Test-Path -LiteralPath $machineGatePath -PathType Leaf)) {
    throw "Machine execution gate missing: $machineGatePath"
}
$machineGate = Get-Content -LiteralPath $machineGatePath -Raw | ConvertFrom-Json
$machineExecutionPlan = Get-GateField -Target $machineGate -Name "active_execution_plan"
if ($null -eq $machineExecutionPlan) {
    throw "Machine execution gate does not declare active_execution_plan."
}

# Normalize ordered_slices regardless of legacy array form or current object-dict form.
$rawOrderedSlices = Get-GateField -Target $machineExecutionPlan -Name "ordered_slices"
$orderedMachineSlices = @()
if ($null -ne $rawOrderedSlices) {
    if ($rawOrderedSlices -is [System.Collections.IEnumerable] -and $rawOrderedSlices -isnot [string]) {
        $index = 0
        foreach ($item in $rawOrderedSlices) {
            $orderedMachineSlices += [pscustomobject]@{
                slice_id = Get-GateStringField -Target $item -Name "slice_id" -Default ("slice-$index")
                order = Get-GateStringField -Target $item -Name "order" -Default ("{0:D4}" -f $index)
                status = Get-GateStringField -Target $item -Name "status" -Default "UNVERIFIED"
            }
            $index++
        }
    }
    elseif ($rawOrderedSlices.PSObject.Properties) {
        $index = 0
        foreach ($prop in $rawOrderedSlices.PSObject.Properties) {
            $orderedMachineSlices += [pscustomobject]@{
                slice_id = $prop.Name
                order = ("{0:D4}" -f $index)
                status = Get-GateStringField -Target $prop.Value -Name "status" -Default "UNVERIFIED"
            }
            $index++
        }
    }
}
$orderedMachineSlices = @($orderedMachineSlices | Sort-Object -Property order)
$pendingMachineSlices = @($orderedMachineSlices | Where-Object { $_.status -ne "PASS" })
$currentMachineSlice = @($pendingMachineSlices | Select-Object -First 1)
$currentMachineSliceId = if ($currentMachineSlice.Count -eq 0) { "GATE_CLOSURE" } else { [string]$currentMachineSlice[0].slice_id }
$currentMachineSliceStatus = if ($currentMachineSlice.Count -eq 0) { "READY_FOR_GATE_EVALUATION" } else { [string]$currentMachineSlice[0].status }

# Gate fields introduced in the current gate schema are optional; read them defensively.
$gateId = Get-GateStringField -Target $machineExecutionPlan -Name "gate_id" -Default ((Get-GateStringField -Target $machineGate -Name "active_phase") + "/" + $currentMachineSliceId)
$objective = Get-GateStringField -Target $machineExecutionPlan -Name "objective" -Default (Get-GateStringField -Target $machineGate -Name "active_phase")
$continuationPolicyValue = Get-GateField -Target (Get-GateField -Target $machineGate -Name "agent_continuation_policy") -Name "mode"
$continuationPolicy = if ($null -eq $continuationPolicyValue) { "declared_only" } else { [string]$continuationPolicyValue }
$nextGateAfterPass = Get-GateStringField -Target $machineExecutionPlan -Name "next_gate_after_pass"

$manifest = [ordered]@{
    schema_version = $SchemaVersion
    product = "LetterBlack LBE"
    generated_at = [DateTimeOffset]::UtcNow.ToString("o")
    generator = "tools/lbe_product_integration.ps1"
    machine_execution = [ordered]@{
        gate_id = $gateId
        objective = $objective
        current_slice = $currentMachineSliceId
        current_slice_status = $currentMachineSliceStatus
        continuation_policy = $continuationPolicy
        ordered_slices = $orderedMachineSlices
        pending_slices = @($pendingMachineSlices | ForEach-Object { [string]$_.slice_id })
        pending_count = $pendingMachineSlices.Count
        always_visible_pending = @((Get-GateField -Target $machineExecutionPlan -Name "always_visible_pending"))
        out_of_scope = @((Get-GateField -Target $machineExecutionPlan -Name "out_of_scope"))
        next_gate_after_pass = $nextGateAfterPass
        rule = "PENDING/IMPLEMENTED/UNVERIFIED continue through the declared plan when runnable; FAIL/BLOCKED remain visible; only PASS advances."
    }
    mode = $Mode
    verification_source = [ordered]@{
        mode = $SourceMode
        ref = $SourceRef
        rule = "check/prove may validate the assembled worktree; build/package are forced to origin/main and cannot package uncommitted state."
    }
    authority = [ordered]@{
        rule = "Agent Wall is the runtime/governance authority. The LBE-owned Rust/Ratatui client is the canonical visible product surface, colocated in the Agent Wall repository at apps\lbe-terminal. Headless Cline mechanics provide cognition/provider/model/continuation behind LBE. This script owns no runtime decision."
        agent_wall = $agent
        rust_product_client = [ordered]@{ repository = $AgentWallRepository; role = "CANONICAL_VISIBLE_PRODUCT_CLIENT"; path = "apps/lbe-terminal/src/" }
    }
    product_surface = [ordered]@{
        name = "LBE CLI/TUI"
        full_name = "Lockstep Boundry Engine"
        brand = "LETTERBLACK"
        mechanics = "Rust/Ratatui visible client + headless Cline reasoning/provider worker"
        rule = "User-facing product identity and presentation are LBE-owned. Cline remains headless internal mechanics only; all capability/consequence authority remains with LBE."
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
Write-Host "Rust client crate:        apps\lbe-terminal (in-repo, no separate TUI origin/main)"
Write-Host "Structural integration:   $structuralPass"
Write-Host "Proof pass:               $proofPass"
Write-Host "Machine gate:             $gateId"
Write-Host "Machine current slice:    $currentMachineSliceId [$currentMachineSliceStatus]"
Write-Host "Continuation policy:      $continuationPolicy"
Write-Host "Pending machine slices:   $($pendingMachineSlices.Count)"
if ($pendingMachineSlices.Count -gt 0) {
    Write-Host "Pending IDs:               $((@($pendingMachineSlices | ForEach-Object { $_.slice_id })) -join ', ')"
}
Write-Host "Cline mechanics reference: $ClineReferenceRepository@$ClineReferenceCommit"
Write-Host "Manifest:                  $manifestPath"
if ($packagePath) { Write-Host "Candidate package:         $packagePath" }
if ($packageVerification) { Write-Host "Package verification:      $($packageVerification.status)" }
Write-Host "Release ready:             False (external installed PTY/ConPTY acceptance is intentionally not fabricated)"

if (-not $structuralPass) { exit 2 }
if ($Mode -in @("prove", "build", "package") -and -not $proofPass) { exit 3 }
exit 0
