LBE Cline Wrapped Product with LBE-Owned Governed BirdEye Gate

Status: PASS - ARCHITECTURE BOUNDED - PRODUCTION IMPLEMENTATION REQUIRES SEPARATE SLICE

Active phase
phase: LBE_CLINE_WRAPPED_PRODUCT
slice: DEFINE_CLINE_PRODUCT_SURFACE_WITH_GOVERNED_BIRDEYE_ADDON
base_sha: a0ae2e4b96ff0566bdc1a8da79cb2820d91359b9

Authorization

The user directed: "completely USE THE CLINE ONLY... we are using LBE wrapper on top so only a few
things we can later modify." The installed unmodified Cline product is the interactive surface; LBE
is a thin wrapper above it; LBE binds governance through Cline-native configuration surfaces only.
The user further directed: "LBE will setup its own birdeye" and selected the thin governed add-on
that reuses the installed BirdEye package rather than a self-contained copy.

Authorized architecture candidate:

CLINE_PRODUCT_SURFACE_WITH_THIN_GOVERNED_BIRDEYE_ADDON

No other architecture candidate is authorized by this slice.

Why this slice exists

The prior slices built two governed execution surfaces that never reached an interactive product:
the Rust/Ratatui wrapper (INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE) and the headless
Python-owned Node subprocess worker (LBE_CLINE_GOVERNED_NODE_STDIO_ARCHITECTURE_GATE). The product
owner now selects the unmodified Cline CLI/TUI product as the visible surface, launched by LBE, with
LBE exercising governance only through Cline-native seams. This slice bounds that wrapper so a later
implementation slice can be activated without inventing new authority during coding.

The few modifiable seams are exactly:

1. Launcher: the LBE command that resolves session/wall/workspace, provisions project Cline
   configuration, injects LBE environment, spawns global Cline, and owns the child lifecycle.
2. Project configuration under the target workspace .cline\ (mcp.json + rules) that Cline already
   loads natively and that travels with the workspace.
3. LBE-owned governed BirdEye MCP server (thin add-on over the installed BirdEye package) that
   exposes the BirdEye read tools and a governed write surface that records receipts into the LBE
   wall database under the active LBE session.

Existing authority owners that must remain authoritative
authorization:
  lbe_guard_inspector/runtime/authorization_resolver.py::resolve_authorization


governed tool execution and receipts:
  lbe_guard_inspector/runtime/tool_orchestration.py::GovernedToolOrchestrator


canonical session/history/evidence:
  existing LBE session, operational-history, governed_operations, task_completion_evidence, wall
  database owners under state\lbe.sqlite3


session identity:
  existing LBE session_state owner; Cline session identifiers remain correlation IDs only


process lifecycle:
  LBE launcher (PowerShell) owns spawn, teardown, and restart responsibility

Cline is never an authority owner. BirdEye read tools remain read-only; the governed write surface is
the only mutation path from the Cline session and its receipts are LBE-persisted.

Architecture contract
LBE launcher (lbe-cline.ps1 + bin\lbe-cline.cmd)
        |
        | resolve/session/wall/workspace env contract
        | provision <workspace>\.cline\mcp.json + <workspace>\.cline\rules\
        v
global Cline product (npm cline, version 3.0.61) -- UNMODIFIED
        |
        | MCP stdio (autoApprove: [])
        v
LBE-owned governed BirdEye add-on (stdlib MCP server)
        |
        | read tools -> installed BirdEye package invoke() (read-only)
        | governed write tools -> authorized? -> GovernedToolOrchestrator.invoke()
        v
LBE wall database state\lbe.sqlite3
        (governed_operations + task_completion_evidence receipts under LBE_SESSION_ID)

Required invariants

LBE resolves and injects LBE_SESSION_ID, LBE_WALL_DATABASE and LBE_TARGET_WORKSPACE before Cline
starts. Without these the governed add-on fails closed at server startup.

The governed write surface builds on GovernedToolOrchestrator; every allowed execution crosses
resolve_authorization() before any executor.

Every governed write call appends a governed_operations row and a durable receipt correlated to the
LBE session; the wall database is the only mutation record.

BirdEye read tools are invoked through the installed BirdEye package and never write.

autoApprove for the LBE-governed MCP server is empty: every governed tool call requires Cline
approval, so opening the wall remains under the user's explicit control.

The launcher provisions .cline\mcp.json and .cline\rules\ only inside the activated workspace; it
never modifies the global ~/.cline\data\settings\cline_mcp_settings.json.

LBE never edits, patches, forks, or renames the installed Cline product.

Cline session IDs are correlation IDs; canonical turn/operation identity remains LBE-owned.

Fail closed on: missing session/database/workspace env, unknown tool, disallowed tool,
malformed request, or a wall database that cannot be opened.

Explicitly rejected designs in this slice
Self-contained LBE birdeye copy under the LBE install
full Product ClineCore adoption in the LBE Python runtime
second authorization resolver
second tool dispatcher
second canonical session/history store
native Cline filesystem/editor/shell/process authority for governed writes
LBE-owned mutation authority residing in the BirdEye read package
global Cline MCP settings mutation by the launcher
Cline branding/UI copy into the LBE install

Required design proof

Before this slice may become PASS, repository evidence must establish:

the exact seams (launcher, project .cline config, governed Birdeye add-on) and their placements;

the exact env contract reused from the installed launcher (LBE_SESSION_ID / LBE_WALL_DATABASE /
LBE_TARGET_WORKSPACE / LBE_WALL_PYTHON);

the governed write tools and their schema, and the read-tool reuse boundary into the installed
BirdEye package;

authorization + orchestrator + receipt persistence call paths bound to the existing owners;

the fail-closed rules; and

a test plan proving read-tool read-only, write-tool authorization-first, receipt persistence,
fail-closed startup, and launcher provisioning.

Required evidence level
ARCHITECTURE / SOURCE

No runtime integration claim is permitted from this slice.

PASS meaning

PASS means the wrapped-product surface is sufficiently bounded that one later production
implementation slice can be activated without inventing additional authority during coding.

PASS does not authorize production implementation automatically.

After PASS, stop and activate a separate implementation slice.

Non-goals

This slice does not:

modify Cline source;

create the governed add-on implementation;

create launcher PowerShell source;

create project configuration provisioning source;

write tests;

mutate the installed Cline MCP settings;

add runtime integration claims;

claim installed/live/user-flow/release readiness.

Production implementation adoption gate

The later implementation slice must prove:

governed add-on stdlib MCP server (imports installed BirdEye package read tools; adds governed write
tools through GovernedToolOrchestrator; appends governed_operations rows + receipts under
LBE_SESSION_ID; fails closed without session/wall/workspace env);

launcher lbe-cline.ps1 + bin\lbe-cline.cmd shipping under the installed LBE tree and resolving the
same env contract as lbe-launch.ps1;

provisioner writing <workspace>\.cline\mcp.json (lbe-birdeye entry with autoApprove []) and
<workspace>\.cline\rules\lbe-governance.md into the activated workspace only;

Cline global binary resolution (npm-cli cline 3.0.61) with an explicit failure instead of silent
misrouting;

child lifecycle ownership (spawn, wait, teardown);

sync of the canonical source into the installed tree;

tests and gate validator PASS; and

git diff --check PASS.

Required implementation tests
read tools remain read-only (no wall writes)
write tools are authorization-first (deny/escalate before executor)
governed execute produces a governed_operations row + receipt tied to LBE_SESSION_ID
fail-closed startup without env
launcher resolves env defaults identical to installed lbe-launch.ps1
provisioner writes project .cline\mcp.json + rules and never the global settings
Cline binary must resolve, else launcher fails
Checkpoint
phase: LBE_CLINE_WRAPPED_PRODUCT
slice: DEFINE_CLINE_PRODUCT_SURFACE_WITH_GOVERNED_BIRDEYE_ADDON
base_sha: a0ae2e4b96ff0566bdc1a8da79cb2820d91359b9
implementation_sha: a0ae2e4b96ff0566bdc1a8da79cb2820d91359b9
requirements: unmodified Cline product surface; LBE thin wrapper seams (launcher, project .cline config, LBE-owned governed BirdEye add-on); BirdEye reads reused read-only; governed writes via resolve_authorization + GovernedToolOrchestrator; receipts persisted under LBE session; fail-closed startup
existing_owner: resolve_authorization; GovernedToolOrchestrator; session_state; governed_operations; task_completion_evidence; wall database
reuse_decision: reuse installed BirdEye package for read tools; reuse existing authorization and orchestrator owners for governed writes; adopt unmodified global Cline as the visible product
required_evidence_level: ARCHITECTURE / SOURCE
validation_evidence: seams enumerated; env contract identified; read/write reuse boundary identified; fail-closed rules defined; adoption-gate and test contract defined
unverified: governed add-on implementation, launcher/provisioner implementation, installed sync, live governed flow, Cline MCP approval behavior; intentionally deferred to the implementation slice
document_conflicts: supersedes the Rust/Ratatui surface as the primary visible product; CLI_NORMAL_PATH and INSTALLED_PTY gates remain the acceptance record for their own slices
status: PASS
project_user_ready: UNVERIFIED
release_ready: UNVERIFIED
next_phase_locked: true