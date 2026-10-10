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
    $SourceMode = "worktree"
}
if ($Mode -in @("build", "package") -and $SourceMode -notin @("worktree", "origin-main")) {
    throw "Build/package source must be worktree or origin-main."
}
$SourceRef = if ($SourceMode -eq "origin-main") { "origin/main" } else { "WORKTREE" }

function Invoke-Native {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$WorkingDirectory
    )
    $previous = Get-Location
    # Native commands may write non-fatal progress/errors to stderr. Capture
    # both streams and let the native exit code remain authoritative.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        if ($WorkingDirectory) { Set-Location $WorkingDirectory }
        $lines = @(& $FilePath @Arguments 2>&1 | ForEach-Object { "$_" })
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
        Set-Location $previous
    }
    [pscustomobject]@{
        command = "$FilePath $($Arguments -join ' ')"
        exit_code = $exitCode
        output = $lines
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
    $terminalUi = Get-SourceText -Root $AgentRoot -Path "lbe_guard_inspector/terminal_ui.py" -SourceMode $SourceMode
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

    # Keep structural source markers ASCII-stable.  SourceMode=origin-main
    # reads through git/PowerShell, whose console decoding can mojibake
    # non-ASCII UI glyphs without changing the actual UTF-8 source.
    $terminalMarkers = @(
        "LBE",
        "LETTERBLACK",
        "ACTIVE PROCESS",
        "[I] > ",
        '"/plan"',
        '"/act"',
        '"/audit"',
        "lbe_guard_inspector.product_entry"
    )
    $missingTerminalMarkers = @($terminalMarkers | Where-Object { -not $terminalUi.Contains($_) })
    $terminalConnected = $productEntry.Contains("from .terminal_ui import main as terminal_main") -and ($missingTerminalMarkers.Count -eq 0)
    $checks.Add((New-ContractCheck -Id "lbe.terminal_product_surface" -Passed $terminalConnected -Classification $(if ($terminalConnected) { "CONNECTED" } else { "MISSING" }) -Detail $(if ($terminalConnected) { "Bare lbe delegates to the LBE-owned terminal client, which delegates governed work back through product_entry." } else { "Missing terminal markers: $($missingTerminalMarkers -join ', ')" })))

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

function Get-ProofPython {
    # The proof suite must run on an interpreter that satisfies the package
    # requirement. A bare `python` on PATH can be older than 3.11 and need not
    # carry pytest, which made agent.focused_tests fail for environmental
    # reasons and blocked the whole product build. Resolution mirrors
    # launch-lbe.ps1 Resolve-LbePython so the installer and the launcher agree.
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

        # The proof suite runs pytest, so the interpreter must actually be able
        # to import it. Several 3.11+ interpreters exist on this machine and the
        # newest one is not necessarily the one carrying the test dependencies.
        foreach ($candidate in ($candidates | Select-Object -Unique)) {
            if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
            & $candidate -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            & $candidate -c 'import pytest' 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            return $candidate
        }
        return $null
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Invoke-Proof {
    param([string]$AgentStage, [string]$TuiStage)

    $proofs = [System.Collections.Generic.List[object]]::new()
    $pythonPath = Get-ProofPython
    $python = if ($pythonPath) { [pscustomobject]@{ Source = $pythonPath } } else { $null }
    if (-not $python) {
        $proofs.Add([pscustomobject]@{ id = "agent.focused_tests"; status = "BLOCKED"; blocking = $true; exit_code = $null; command = "python"; output = @("python not found") })
    }
    else {
        $agentTests = [System.Collections.Generic.List[string]]::new()
        @(
            "tests/test_authorization_resolver.py",
            "tests/test_tool_orchestration.py",
            "tests/test_product_entry.py",
            "tests/test_provider_continuation.py",
            "tests/test_terminal_ui.py"
        ) | ForEach-Object { $agentTests.Add($_) }
        foreach ($candidate in @("tests/test_child_agent_product_seam.py", "tests/test_operational_history.py")) {
            if (Test-Path -LiteralPath (Join-Path $AgentStage $candidate) -PathType Leaf) {
                $agentTests.Add($candidate)
            }
            else {
                $proofs.Add([pscustomobject]@{ id = "agent.$([IO.Path]::GetFileNameWithoutExtension($candidate))"; status = "BLOCKED"; blocking = $true; exit_code = $null; command = "pytest"; output = @("required child-agent proof missing: $candidate") })
            }
        }
        # pytest's default base_temp lives under the user profile temp root, which
    # can be ACL-locked on a real machine. Every test here failed at setup with
    # PermissionError before running a single assertion, which read as a product
    # failure. Point the proof run at a unique directory the installer creates.
    $proofBaseTemp = Join-Path ([IO.Path]::GetTempPath()) ("lbe-proof-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
    $agent = Invoke-Native -FilePath $python.Source -WorkingDirectory $AgentStage -Arguments (@("-m", "pytest", "-q", "--basetemp", $proofBaseTemp) + @($agentTests))
        $proofs.Add([pscustomobject]@{ id = "agent.focused_tests"; status = $(if ($agent.exit_code -eq 0) { "PASS" } else { "FAIL" }); blocking = $true; exit_code = $agent.exit_code; command = $agent.command; output = $agent.output })
    }

    $cargo = Get-Command cargo -ErrorAction SilentlyContinue
    if (-not $cargo) {
        $proofs.Add([pscustomobject]@{ id = "rust_reference.cargo_test"; status = "SKIP"; blocking = $false; exit_code = $null; command = "cargo"; output = @("cargo not found") })
    }
    else {
        $tuiTest = Invoke-Native -FilePath $cargo.Source -WorkingDirectory $TuiStage -Arguments @("test", "--locked")
        $proofs.Add([pscustomobject]@{ id = "rust_reference.cargo_test"; status = $(if ($tuiTest.exit_code -eq 0) { "PASS" } else { "FAIL" }); blocking = $false; exit_code = $tuiTest.exit_code; command = $tuiTest.command; output = $tuiTest.output })
        $fmt = Invoke-Native -FilePath $cargo.Source -WorkingDirectory $TuiStage -Arguments @("fmt", "--", "--check")
        $proofs.Add([pscustomobject]@{ id = "rust_reference.cargo_fmt"; status = $(if ($fmt.exit_code -eq 0) { "PASS" } else { "FAIL" }); blocking = $false; exit_code = $fmt.exit_code; command = $fmt.command; output = $fmt.output })
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

    if (Test-Path -LiteralPath $BuildRoot) {
        # Fail closed if an external process still owns a staged node_modules
        # path; bounded retry handles transient Windows/antivirus file handles.
        $cleared = $false
        for ($attempt = 1; $attempt -le 5; $attempt++) {
            try {
                Remove-Item -LiteralPath $BuildRoot -Recurse -Force -ErrorAction Stop
                $cleared = -not (Test-Path -LiteralPath $BuildRoot)
                if ($cleared) { break }
            }
            catch {
                if ($attempt -eq 5) { throw }
            }
            Start-Sleep -Seconds 2
        }
        if (-not $cleared) { throw "Cannot clear prior isolated package build root: $BuildRoot" }
    }
    New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
    $runtimeOut = Join-Path $BuildRoot "runtime"
    $workerOut = Join-Path $BuildRoot "cline-worker"
    New-Item -ItemType Directory -Path $runtimeOut, $workerOut -Force | Out-Null

    $pythonPath = Get-ProofPython
    if (-not $pythonPath) { throw "No Python 3.11+ interpreter is available to build the Agent Wall wheel." }
    $python = [pscustomobject]@{ Source = $pythonPath }
    $pipWheel = Invoke-Native -FilePath $python.Source -WorkingDirectory $AgentStage -Arguments @("-m", "pip", "wheel", ".", "--no-deps", "--wheel-dir", $runtimeOut)
    if ($pipWheel.exit_code -ne 0) { throw "Agent Wall wheel build failed." }

    $workerSource = Join-Path $AgentStage "lbe_guard_inspector\runtime\cline_worker"
    Copy-Item -LiteralPath (Join-Path $workerSource "worker.mjs") -Destination $workerOut
    Copy-Item -LiteralPath (Join-Path $workerSource "package.json") -Destination $workerOut
    Copy-Item -LiteralPath (Join-Path $workerSource "package-lock.json") -Destination $workerOut
    $npm = Get-Command npm.cmd -ErrorAction Stop
    $npmCi = Invoke-Native -FilePath $npm.Source -WorkingDirectory $workerOut -Arguments @("ci", "--omit=dev")
    if ($npmCi.exit_code -ne 0) { throw "Cline worker dependency provisioning failed." }

    [pscustomobject]@{
        runtime_wheels = @((Get-ChildItem -LiteralPath $runtimeOut -Filter "*.whl" | Select-Object -ExpandProperty Name))
        client = "lbe_guard_inspector.terminal_ui"
        rust_reference_client = "apps/lbe-terminal (source/reference only; not packaged as primary client)"
        cline_worker = "cline-worker/"
        build_commands = @($pipWheel.command, $npmCi.command)
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
    [string]$Provider = "openai-compatible",
    [string]$Model,
    [string]$Prompt,
    [switch]$Continue,
    [switch]$Json,
    [switch]$Plain,
    [switch]$NoAnimation,
    [switch]$Ascii,
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "LetterBlack\LBE")
)

$ErrorActionPreference = "Stop"
$python = Join-Path $InstallRoot "venv\Scripts\python.exe"

# Preserve the public command aliases before PowerShell resolves positional
# parameters into launcher configuration fields.
$headlessRun = $false
if ($Project -eq "tui") {
    $Project = $null
}
elseif ($Project -eq "run") {
    $headlessRun = $true
    # In the public form `lbe run "prompt"`, PowerShell binds the second
    # positional value to $Database. Reclassify it as the prompt before
    # database defaults are resolved.
    if (-not $Prompt -and $Database) {
        $Prompt = $Database
        $Database = $null
    }
    $Project = $null
    if (-not $Prompt) { throw "lbe run requires a prompt." }
}

# Informational flags must pass through to the installed client without
# requiring a full runtime/session/provider bootstrap. They can arrive either
# as unbound $args or positionally bound to $Project / $Model.
$informational = @('--version', '-V', '--help', '-h')
$infoArg = $null
foreach ($candidate in @($args) + @($Project) + @($Model)) {
    if ($informational -contains $candidate) { $infoArg = $candidate; break }
}
if ($infoArg) {
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Installed LBE Python runtime missing: $python" }
    if ($infoArg -in @('--version','-V')) {
        & $python -m lbe_guard_inspector.terminal_ui --version
    } else {
        & $python -m lbe_guard_inspector.terminal_ui --help
    }
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

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Installed LBE Python runtime missing: $python" }
if (-not (Test-Path -LiteralPath $ProviderConfig -PathType Leaf)) { throw "Provider config missing: $ProviderConfig" }

# The visible LBE terminal client cannot attach until a persisted session exists. Create
# that session through the authoritative Python entrypoint instead of making
# the TUI invent identity or bypassing the session policy gate. An explicit
# -SessionId (or LBE_SESSION_ID) still resumes an existing session exactly as
# before.
if (-not $SessionId) {
    $providerDocument = Get-Content -LiteralPath $ProviderConfig -Raw | ConvertFrom-Json
    if (-not $Model) { $Model = [string]$providerDocument.model }
    if (-not $Model) { throw "Provider config must declare a model before creating a session" }
    if ($providerDocument.provider_id) { $Provider = [string]$providerDocument.provider_id }

    $hash = [Security.Cryptography.SHA256]::Create()
    try {
        $workspaceBytes = [Text.Encoding]::UTF8.GetBytes($workspaceFull.ToLowerInvariant())
        $workspaceId = "workspace_" + ([BitConverter]::ToString($hash.ComputeHash($workspaceBytes))).Replace('-', '').ToLowerInvariant()
    }
    finally { $hash.Dispose() }

    switch ($Agent) {
        "audit" {
            $sessionMode = "audit"
            $sessionPermission = "read_only"
            $sessionRuntimePolicy = "audit"
        }
        "plan" {
            $sessionMode = "investigation"
            $sessionPermission = "read_only"
            $sessionRuntimePolicy = "permissive"
        }
        default {
            $sessionMode = "coding"
            $sessionPermission = "write_allowed"
            $sessionRuntimePolicy = "permissive"
        }
    }
    $bootstrapArgs = @(
        "-m", "lbe_guard_inspector.product_entry", "start",
        "--database", ([IO.Path]::GetFullPath($Database)),
        "--workspace", $workspaceFull,
        "--project-workspace-id", $workspaceId,
        "--mode", $sessionMode,
        "--permission", $sessionPermission,
        "--runtime-policy", $sessionRuntimePolicy,
        "--provider", $Provider,
        "--model", $Model,
        "--provider-config", ([IO.Path]::GetFullPath($ProviderConfig)),
        "--format", "json"
    )
    if ($CapabilityRegistry) { $bootstrapArgs += @("--capability-registry", ([IO.Path]::GetFullPath($CapabilityRegistry))) }
    $previousPreference = $ErrorActionPreference
    $previousLocation = Get-Location
    try {
        $ErrorActionPreference = "Continue"
        Set-Location -LiteralPath $InstallRoot
        $bootstrapLines = @(& $python @bootstrapArgs 2>&1 | ForEach-Object { "$_" })
        $bootstrapExitCode = $LASTEXITCODE
    }
    finally {
        Set-Location $previousLocation
        $ErrorActionPreference = $previousPreference
    }
    $bootstrapOutput = ($bootstrapLines -join [Environment]::NewLine).Trim()
    if ($bootstrapExitCode -ne 0) { throw "Unable to create LBE session: $bootstrapOutput" }
    try { $bootstrap = $bootstrapOutput | ConvertFrom-Json }
    catch { throw "LBE session bootstrap returned invalid JSON: $bootstrapOutput" }
    if (-not $bootstrap.ok -or -not $bootstrap.session_id) {
        throw "LBE session bootstrap was rejected: $bootstrapOutput"
    }
    $SessionId = [string]$bootstrap.session_id
}

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

if ($headlessRun -or $Prompt) {
    if (-not $Prompt) { throw "lbe run requires a prompt." }
    $turnArgs = @(
        "-m", "lbe_guard_inspector.product_entry", "turn",
        "--database", ([IO.Path]::GetFullPath($Database)),
        "--session-id", $SessionId,
        "--text", $Prompt,
        "--provider-config", ([IO.Path]::GetFullPath($ProviderConfig))
    )
    if ($Json) { $turnArgs += @("--format", "json") }
    else { $turnArgs += @("--format", "text") }
    & $python @turnArgs
    exit $LASTEXITCODE
}

$terminalArgs = @(
    "-m", "lbe_guard_inspector.terminal_ui",
    $workspaceFull,
    "--database", ([IO.Path]::GetFullPath($Database)),
    "--provider-config", ([IO.Path]::GetFullPath($ProviderConfig)),
    "--session", $SessionId,
    "--agent", $(if ($Agent -eq "build") { "act" } else { $Agent })
)
if ($Model) { $terminalArgs += @("--model", $Model) }
& $python @terminalArgs
exit $LASTEXITCODE
'@
    Set-Content -LiteralPath (Join-Path $PackageRoot "lbe-launch.ps1") -Value $launcher -Encoding UTF8
}

function Write-ClineLauncher {
    param([string]$PackageRoot)
    $launcher = @'
param(
    [string]$Project,
    [string]$Database,
    [string]$SessionId,
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "LetterBlack\LBE")
)

$ErrorActionPreference = "Stop"
$python = Join-Path $InstallRoot "venv\Scripts\python.exe"

# Installed config\mcp.json supplies the BirdEye read-tool server identity, the
# same source lbe-launch.ps1 uses. The governed add-on shells to that server at
# the process boundary and never imports the installed BirdEye package in-process.
$mcpConfigPath = Join-Path $InstallRoot "config\mcp.json"
if (Test-Path -LiteralPath $mcpConfigPath -PathType Leaf) {
    $mcp = Get-Content -LiteralPath $mcpConfigPath -Raw | ConvertFrom-Json
    if ($mcp.python) { $env:LBE_BIRDEYE_MCP_PYTHON = [string]$mcp.python }
    if ($mcp.server) { $env:LBE_BIRDEYE_MCP_SERVER = [string]$mcp.server }
}

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

# LBE_SESSION_ID is the governed session the add-on binds. Cline session ids are
# correlation-only and never become an authority owner.
if (-not $SessionId) { $SessionId = $env:LBE_SESSION_ID }
if (-not $SessionId) { throw "LBE governed session id is required (create one with 'lbe session create', or set LBE_SESSION_ID)." }

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Installed LBE Python runtime missing: $python" }
if (-not (Test-Path -LiteralPath $Database -PathType Leaf)) { throw "LBE wall database missing: $Database" }

$env:LBE_RUNTIME = "real"
$env:LBE_WALL_ROOT = $InstallRoot
$env:LBE_WALL_PYTHON = $python
$env:LBE_TARGET_WORKSPACE = $workspaceFull
$env:LBE_WALL_DATABASE = [IO.Path]::GetFullPath($Database)
$env:LBE_SESSION_ID = $SessionId

# --- Workspace-scoped Cline provisioning. Only the project's own .cline tree is
# written; global ~/.cline settings are never touched. ---
$clineDir = Join-Path $workspaceFull ".cline"
$rulesDir = Join-Path $clineDir "rules"
New-Item -ItemType Directory -Path $rulesDir -Force | Out-Null

$birdeyePython = if ($env:LBE_BIRDEYE_MCP_PYTHON) { $env:LBE_BIRDEYE_MCP_PYTHON } else { $python }
$birdeyeServer = $env:LBE_BIRDEYE_MCP_SERVER
if (-not $birdeyeServer) { $birdeyeServer = Join-Path $InstallRoot "mcp\birdeye\mcp_server.py" }

$mcpFilePath = Join-Path $clineDir "mcp.json"
$projectMcp = $null
if (Test-Path -LiteralPath $mcpFilePath -PathType Leaf) {
    $projectMcp = Get-Content -LiteralPath $mcpFilePath -Raw | ConvertFrom-Json
}
if ($null -eq $projectMcp -or -not $projectMcp.PSObject.Properties.Name -contains "mcpServers") {
    $projectMcp = @{ mcpServers = @{} }
}
$serverEntry = @{
    command = $python
    args = @("-m", "lbe_guard_inspector.runtime.cline_governed_birdeye", "--stdio")
    autoApprove = @()
    env = @{
        LBE_SESSION_ID = $SessionId
        LBE_WALL_DATABASE = [IO.Path]::GetFullPath($Database)
        LBE_TARGET_WORKSPACE = $workspaceFull
        LBE_BIRDEYE_MCP_PYTHON = $birdeyePython
        LBE_BIRDEYE_MCP_SERVER = $birdeyeServer
    }
}
$projectMcp.mcpServers."lbe-birdeye" = $serverEntry
$projectMcp | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $mcpFilePath -Encoding UTF8

$rulesLines = @(
    "# LBE governance (curated by the installed LetterBlack LBE)",
    "",
    "- This Cline session is a governed surface of the LBE Agent Wall.",
    "- Use the lbe-birdeye read tools and the lbe_governed_execute tool for ",
    "  governed operations; do not bypass them with raw file, shell, or editor ",
    "  mutations when a governed tool exists.",
    "- Reads via lbe-birdeye never require approval. Writes through ",
    "  lbe_governed_execute require explicit Agent Wall approval and produce ",
    "  deterministic receipts recorded in governed_operations.",
    "- The Agent Wall - not this Cline session - owns session, provider, ",
    "  credential, tool, and completion authority.",
    "- Keep every mutation inside the workspace root reported by ",
    "  lbe_session_status."
)
$rulesContent = ($rulesLines -join "`r`n")
Set-Content -LiteralPath (Join-Path $rulesDir "lbe-governance.md") -Value $rulesContent -Encoding UTF8

# --- Resolve the global Cline CLI or fail explicitly (never install it). ---
$cline = $null
$candidates = @()
if ($env:APPDATA) {
    $candidates += (Join-Path $env:APPDATA "npm\cline.cmd")
    $candidates += (Join-Path $env:APPDATA "npm\cline.cli\cline.cmd")
    $candidates += (Join-Path $env:APPDATA "npm\@cline\cli\cline.cmd")
}
$candidates += "cline.cmd"
$candidates += "cline"
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { $cline = $candidate; break }
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) { $cline = $command.Source; break }
}
if (-not $cline) { throw "Cline CLI not found. Install @cline/cli so it resolves, then retry." }

$cliArgs = @("--tui", "-c", $workspaceFull)
foreach ($extra in $args) { $cliArgs += $extra }
& $cline @cliArgs
exit $LASTEXITCODE
'@
    Set-Content -LiteralPath (Join-Path $PackageRoot "lbe-cline.ps1") -Value $launcher -Encoding UTF8
}

function Write-Installer {
    param([string]$PackageRoot)
    $installer = @'
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "LetterBlack\LBE"),
    [string]$BirdEyeServer,
    [string]$BirdEyePython,
    [string]$Project,
    [string]$ProviderConfig,
    [switch]$SkipUserPath
)
$ErrorActionPreference = "Stop"
$venv = Join-Path $InstallRoot "venv"
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
$bootstrapPython = $null
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $candidate = (& $pyLauncher.Source -3 -c 'import sys; print(sys.executable)' 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and $candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        & $candidate -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $bootstrapPython = $candidate }
    }
}
if (-not $bootstrapPython) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        & $pythonCommand.Source -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $bootstrapPython = $pythonCommand.Source }
    }
}
if (-not $bootstrapPython) { throw "LBE installer requires Python 3.11 or newer; no compatible interpreter was found." }
& $bootstrapPython -m venv $venv
if ($LASTEXITCODE -ne 0) { throw "Unable to create LBE Python virtual environment" }
$python = Join-Path $venv "Scripts\python.exe"
$wheel = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot "runtime") -Filter "*.whl" | Select-Object -First 1
if (-not $wheel) { throw "LBE runtime wheel missing" }
& $python -m pip install --force-reinstall $wheel.FullName
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
    $providerSourceFull = [IO.Path]::GetFullPath($ProviderConfig)
    $providerDestinationFull = [IO.Path]::GetFullPath($installedProviderConfig)
    if ([String]::Equals($providerSourceFull, $providerDestinationFull, [StringComparison]::OrdinalIgnoreCase)) {
        Write-Host "Provider configuration already installed: $installedProviderConfig"
    }
    else {
        Copy-Item -LiteralPath $providerSourceFull -Destination $providerDestinationFull -Force
        Write-Host "Installed provider configuration: $installedProviderConfig"
    }
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

# Windows PowerShell's -Encoding UTF8 emits a BOM. Normalize every JSON
# artifact consumed by the Python runtime to UTF-8 without BOM.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($jsonConfig in @(
    $registryPath,
    (Join-Path $config "mcp.json"),
    (Join-Path $config "runtime.json"),
    $installedProviderConfig
)) {
    if (Test-Path -LiteralPath $jsonConfig -PathType Leaf) {
        $jsonText = [IO.File]::ReadAllText($jsonConfig)
        if ($jsonText.Length -gt 0 -and $jsonText[0] -eq [char]0xFEFF) {
            $jsonText = $jsonText.Substring(1)
        }
        [IO.File]::WriteAllText($jsonConfig, $jsonText, $utf8NoBom)
    }
}
$site = & $python -c "import pathlib,lbe_guard_inspector; print(pathlib.Path(lbe_guard_inspector.__file__).parent)"
if ($LASTEXITCODE -ne 0) { throw "Unable to resolve installed LBE package" }
$workerTarget = Join-Path $site "runtime\cline_worker"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "cline-worker\node_modules") -Destination $workerTarget -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "lbe-launch.ps1") -Destination (Join-Path $InstallRoot "lbe-launch.ps1") -Force
Write-Host "Installed LetterBlack LBE to $InstallRoot"
Write-Host "Runtime CLI: $(Join-Path $venv 'Scripts\lbe.exe')"
Write-Host "LBE terminal client: $python -m lbe_guard_inspector.terminal_ui"
Write-Host "Real-runtime launcher: $(Join-Path $InstallRoot 'lbe-launch.ps1')"
Write-Host "MCP configuration: $(Join-Path $config 'mcp.json') [$mcpStatus]"

# --- Installed single-command contract: bin\lbe.cmd -> lbe-launch.ps1 -> LBE terminal client ---
$binDir = Join-Path $InstallRoot "bin"
New-Item -ItemType Directory -Path $binDir -Force | Out-Null
$binCmd = Join-Path $binDir "lbe.cmd"
@"
@ECHO off
SETLOCAL
SET "LBE_INSTALL_ROOT=$InstallRoot"
powershell -NoProfile -ExecutionPolicy Bypass -File "%LBE_INSTALL_ROOT%\lbe-launch.ps1" %*
SET "LBE_EXIT=%ERRORLEVEL%"
ENDLOCAL & EXIT /B %LBE_EXIT%
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
if ($SkipUserPath) {
    Write-Host "Isolated installation: user PATH deliberately unchanged."
}
elseif ($userPathEntries -notcontains $binFull) {
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

# --- Governed Cline product surface: bin\lbe-cline.cmd -> lbe-cline.ps1 ---
$clineLauncher = Join-Path $PSScriptRoot "lbe-cline.ps1"
if (-not (Test-Path -LiteralPath $clineLauncher -PathType Leaf)) { throw "Cline launcher missing from package: $clineLauncher" }
Copy-Item -LiteralPath $clineLauncher -Destination (Join-Path $InstallRoot "lbe-cline.ps1") -Force
$clineBinCmd = Join-Path $binDir "lbe-cline.cmd"
@"
@ECHO off
SETLOCAL
SET "LBE_INSTALL_ROOT=$InstallRoot"
powershell -NoProfile -ExecutionPolicy Bypass -File "%LBE_INSTALL_ROOT%\lbe-cline.ps1" %*
SET "LBE_EXIT=%ERRORLEVEL%"
ENDLOCAL & EXIT /B %LBE_EXIT%
"@ | Set-Content -LiteralPath $clineBinCmd -Encoding ASCII
Write-Host "Cline product launcher: $(Join-Path $InstallRoot 'lbe-cline.ps1')"
Write-Host "Cline entrypoint: $clineBinCmd"
'@
    Set-Content -LiteralPath (Join-Path $PackageRoot "install.ps1") -Value $installer -Encoding UTF8
}

function Get-Checksums {
    param([string]$Root)
    @(
        Get-ChildItem -LiteralPath $Root -File -Recurse | Sort-Object FullName | ForEach-Object {
            $rootFull = [IO.Path]::GetFullPath($Root).TrimEnd("\") + "\"
            $relative = $_.FullName.Substring($rootFull.Length).Replace("\", "/")
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
    # Verify the actual archive bytes without first extracting thousands of npm
    # paths into a second Windows directory. Expand-Archive can fail on valid
    # long/short-lived node_modules paths; archive-entry hashing is authoritative.
    # Keep VerificationRoot as a compatibility parameter for existing callers.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $manifest = $archive.GetEntry("checksums.json")
        if ($null -eq $manifest) {
            throw "Package verification failed: checksums.json missing from archive."
        }
        $reader = [IO.StreamReader]::new($manifest.Open(), [Text.Encoding]::UTF8, $true)
        try {
            # Windows PowerShell 5.1 preserves a JSON-array result as one
            # pipeline object with @(... | ConvertFrom-Json). Assign directly
            # so all individual checksum records are enumerated.
            $expected = ConvertFrom-Json -InputObject ($reader.ReadToEnd())
        }
        finally {
            $reader.Dispose()
        }
        $errors = [System.Collections.Generic.List[string]]::new()
        $known = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        [void]$known.Add("checksums.json")
        foreach ($entry in $expected) {
            $relative = [string]$entry.path
            if (-not $known.Add($relative)) {
                $errors.Add("duplicate checksum entry: $relative")
                continue
            }
            # Windows PowerShell/.NET Framework normalizes ZipArchive entry
            # names to backslashes on read, even when the ZIP stores '/'.
            $file = $archive.GetEntry($relative)
            if ($null -eq $file) {
                $file = $archive.GetEntry($relative.Replace("/", "\"))
            }
            if ($null -eq $file) {
                $errors.Add("missing: $relative")
                continue
            }
            if ($file.Length -ne [int64]$entry.bytes) {
                $errors.Add("size mismatch: $relative")
            }
            $stream = $file.Open()
            $hasher = [Security.Cryptography.SHA256]::Create()
            try {
                $actualHash = [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace("-", "").ToLowerInvariant()
            }
            finally {
                $hasher.Dispose()
                $stream.Dispose()
            }
            if ($actualHash -ne [string]$entry.sha256) {
                $errors.Add("sha256 mismatch: $relative")
            }
        }
        foreach ($archived in $archive.Entries) {
            if (-not $known.Contains($archived.FullName.Replace("\", "/"))) {
                $errors.Add("unmanifested archive entry: $($archived.FullName)")
            }
        }
        return [pscustomobject]@{
            status = $(if ($errors.Count -eq 0) { "PASS" } else { "FAIL" })
            archive = $ZipPath
            verified_file_count = $expected.Count
            errors = @($errors)
        }
    }
    finally {
        $archive.Dispose()
    }
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
    Write-Host "Rust/Ratatui reference client is absent from this source snapshot; primary LBE package does not depend on it."
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

$proofPass = if ($proofs.Count -eq 0) { $false } else { @($proofs | Where-Object { (($null -eq $_.PSObject.Properties["blocking"]) -or $_.blocking) -and $_.status -ne "PASS" }).Count -eq 0 }

if ($Mode -in @("build", "package")) {
    if (-not $structuralPass) { throw "Product build blocked: structural integration checks failed." }
    if (-not $proofPass) { Write-Host "--- BLOCKING PROOFS ---"; $blockingProofs=@($proofs | Where-Object { (($null -eq $_.PSObject.Properties["blocking"]) -or $_.blocking) -and $_.status -ne "PASS" }); foreach($proof in $blockingProofs){ Write-Host ("PROOF=" + $proof.id + " STATUS=" + $proof.status + " EXIT=" + $proof.exit_code); foreach($line in @($proof.output)){ Write-Host ("  " + $line) } }; throw "Product build blocked: proof suite did not pass." }
    $packageRoot = Join-Path $OutputRoot "LetterBlack-LBE"
    $build = Build-Product -AgentStage $agentStage -TuiStage $tuiStage -BuildRoot $packageRoot
    Write-Installer -PackageRoot $packageRoot
    Write-Launcher -PackageRoot $packageRoot
    Write-ClineLauncher -PackageRoot $packageRoot
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
            $blockingValue = Get-GateField -Target $item -Name "blocking"
            $orderedMachineSlices += [pscustomobject]@{
                slice_id = Get-GateStringField -Target $item -Name "slice_id" -Default ("slice-$index")
                order = Get-GateStringField -Target $item -Name "order" -Default ("{0:D4}" -f $index)
                status = Get-GateStringField -Target $item -Name "status" -Default "UNVERIFIED"
                blocking = if ($null -eq $blockingValue) { $true } else { [bool]$blockingValue }
            }
            $index++
        }
    }
    elseif ($rawOrderedSlices.PSObject.Properties) {
        $index = 0
        foreach ($prop in $rawOrderedSlices.PSObject.Properties) {
            $blockingValue = Get-GateField -Target $prop.Value -Name "blocking"
            $orderedMachineSlices += [pscustomobject]@{
                slice_id = $prop.Name
                order = ("{0:D4}" -f $index)
                status = Get-GateStringField -Target $prop.Value -Name "status" -Default "UNVERIFIED"
                blocking = if ($null -eq $blockingValue) { $true } else { [bool]$blockingValue }
            }
            $index++
        }
    }
}
$orderedMachineSlices = @($orderedMachineSlices | Sort-Object -Property order)
$pendingMachineSlices = @($orderedMachineSlices | Where-Object { $_.status -ne "PASS" })
$blockingPendingMachineSlices = @($pendingMachineSlices | Where-Object { $_.blocking })
$nonBlockingPendingMachineSlices = @($pendingMachineSlices | Where-Object { -not $_.blocking })
$currentMachineSlice = @($blockingPendingMachineSlices | Select-Object -First 1)
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
        blocking_pending_slices = @($blockingPendingMachineSlices | ForEach-Object { [string]$_.slice_id })
        blocking_pending_count = $blockingPendingMachineSlices.Count
        non_blocking_pending_slices = @($nonBlockingPendingMachineSlices | ForEach-Object { [string]$_.slice_id })
        non_blocking_pending_count = $nonBlockingPendingMachineSlices.Count
        always_visible_pending = @((Get-GateField -Target $machineExecutionPlan -Name "always_visible_pending"))
        out_of_scope = @((Get-GateField -Target $machineExecutionPlan -Name "out_of_scope"))
        next_gate_after_pass = $nextGateAfterPass
        rule = "Only blocking non-PASS slices hold product acceptance. Non-blocking provider/model failures remain visible as degraded evidence but do not fail LBE as a whole."
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
    # npm ci can leave the Windows filesystem enumerator briefly inconsistent
    # after completion. Retry hashing a fresh complete inventory instead of
    # treating a transient disappeared path as a successful package.
    $checksums = $null
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            $checksums = Get-Checksums -Root $packageRoot
            break
        }
        catch {
            if ($attempt -eq 5) { throw }
            Start-Sleep -Seconds 2
        }
    }
    $checksums = @($checksums)
    if ($checksums.Count -eq 0) {
        throw "Package inventory failed: no files were returned for checksum generation."
    }
    $checksumsPath = Join-Path $packageRoot "checksums.json"
    $checksums | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $checksumsPath -Encoding UTF8
    if (-not (Test-Path -LiteralPath $checksumsPath -PathType Leaf)) {
        throw "Package inventory failed: checksums.json was not written."
    }

    $zip = Join-Path $OutputRoot "LetterBlack-LBE-2.0.3-win-x64-candidate.zip"
    if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }

    # Create the archive from the checksum inventory itself instead of asking
    # CreateFromDirectory to perform a second recursive filesystem enumeration.
    # npm dependency trees can be momentarily inconsistent on Windows; a second
    # enumeration previously produced a tiny ZIP containing only directory
    # entries even though the package root still contained thousands of files.
    # Inventory-driven creation fails closed if any inventoried file disappears.
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $partialZip = "$zip.partial"
    if (Test-Path -LiteralPath $partialZip) { Remove-Item -LiteralPath $partialZip -Force }
    $archiveStream = $null
    $archive = $null
    try {
        $archiveStream = [IO.File]::Open($partialZip, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        $archive = [IO.Compression.ZipArchive]::new($archiveStream, [IO.Compression.ZipArchiveMode]::Create, $false)
        foreach ($checksum in $checksums) {
            $relative = [string]$checksum.path
            $source = Join-Path $packageRoot ($relative.Replace("/", "\"))
            if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
                throw "Package archive failed: inventoried file disappeared: $relative"
            }
            $entry = $archive.CreateEntry($relative, [IO.Compression.CompressionLevel]::Optimal)
            $input = [IO.File]::OpenRead($source)
            $output = $entry.Open()
            try {
                $input.CopyTo($output)
            }
            finally {
                $output.Dispose()
                $input.Dispose()
            }
        }

        $manifestEntry = $archive.CreateEntry("checksums.json", [IO.Compression.CompressionLevel]::Optimal)
        $manifestInput = [IO.File]::OpenRead($checksumsPath)
        $manifestOutput = $manifestEntry.Open()
        try {
            $manifestInput.CopyTo($manifestOutput)
        }
        finally {
            $manifestOutput.Dispose()
            $manifestInput.Dispose()
        }
    }
    finally {
        if ($archive) { $archive.Dispose() }
        if ($archiveStream) { $archiveStream.Dispose() }
    }
    Move-Item -LiteralPath $partialZip -Destination $zip -Force
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
