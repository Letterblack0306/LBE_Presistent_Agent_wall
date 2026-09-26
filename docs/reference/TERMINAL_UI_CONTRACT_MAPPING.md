# Terminal UI contract mapping: LBE HTML/React reference to Rust/Ratatui

Intent: `LBE-INTENT-TERMINAL-UI-CONTRACT-CONVERGENCE-001`

## Authority

```text
REFERENCE FOLDER  = visual + interaction + projection contract only
RUST CLIENT       = the real product surface (presentation + operator control)
LBE RUNTIME       = identity, authorization, governed execution, receipts,
                    evidence, persistence, validation, completion
```

The reference is not repository authority. Its copies of `PROJECT_INDEX.md` and `README.md`
are stale references; `PROJECT_INDEX.md` and `docs/CURRENT_STATUS.md` on canonical main are
current authority. Nothing from the reference may create runtime truth in the client.

## Classification rules

- `ALREADY-OWNED` - the Rust client already implements the contract; nothing to port.
- `GAP` - the contract is approved and the Rust client lacks it; needs a bounded slice.
- `REFERENCE-ONLY` - exists only to exercise the reference; must never reach the client.
- `OUT-OF-SCOPE` - deliberately not taken by the terminal client.

## Projection and ingestion seam

| Reference surface | Reference evidence | Rust owner | Status |
|---|---|---|---|
| `RuntimeProjectionAdapter` | `src/adapters/RuntimeProjectionAdapter.ts:24-37` | `LbeWrapper` request/event boundary, `App::reduce_lbe_event` | ALREADY-OWNED: same shape (snapshot + request boundary), no port needed |
| `RuntimeProjectionSource` / typed projections | `src/types/ide.ts` (`RuntimeProjection`, `ProviderProjection`, `SessionProjection`) | `LbeSnapshot`, `types.rs` projections | ALREADY-OWNED |
| `StateProvenance` (`LIVE_RUNTIME`/`REFERENCE_FIXTURE`/`HISTORICAL`/`UNKNOWN`) | `src/types/ide.ts` | evidence `source_type` / `verified` metadata in the governed projection | ALREADY-OWNED (expressed as evidence provenance, not a client enum) |
| `RuntimeConnectionStatus` `LIVE`/`PREVIEW`/`DISCONNECTED` | `src/types/ide.ts` | `RuntimeConnection` (`Mock`, `Disconnected`, `Connecting`, `Connected`, `Reconnecting`, `Lost`) | ALREADY-OWNED: the client distinguishes mock and live at a finer grain than the reference |
| Demo / reference projection source | `src/adapters/demoProjectionSource.ts` | - | REFERENCE-ONLY: synthetic ids and receipts must never enter the client |

## Core surfaces

| Reference screen | Reference evidence | Rust owner | Status |
|---|---|---|---|
| Agent Cockpit | `PrimaryScreen = cockpit` | main working surface, transcript + governed timeline | ALREADY-OWNED |
| **Action Gate** | `PrimaryScreen = action_gate`; `ToolProposalProjection`, `AuthorizationProjection`, `RiskLevel` | `MockPanel::Tools` shows the last governed tool projection; approval flows exist as `UserRequest::Approve`/`Reject` and `SessionStatus::WaitingForApproval` | **GAP**: no surface shows capability, target, risk, operation, diff, and allow-once/deny together. The client has the data (`risk_class`, `authorization_verdict`, `authorization_rationale` in the governed projection) but no dedicated surface |
| **Evidence / Receipt Inspector** | `PrimaryScreen = inspector`; one chain from proposal to validation | `MockPanel::Evidence` and `MockPanel::Receipts` are two independent panels | **GAP**: the cross-linked single-item chain (proposal to authorization to execution to receipt to evidence to validation) is not a surface; the two panels are not linked |
| Agent Wall | `PrimaryScreen = agent_wall`; `ChildRunProjection` | `MockPanel::Agents`, `ChildAgentRunsUpdated` event, `ChildAgentRun` status | ALREADY-OWNED |
| Extensions | `PrimaryScreen = extensions`; `CapabilityExtension`, `PluginManagerModal` | `MockPanel::Mcp`, `McpRegistryUpdated` | PARTIAL: registry coverage exists; capability extension model is not carried |
| Editor / file tree | `CodeEditor.tsx`, `FileExplorer.tsx` | `MockPanel::Changes`, `Undo`, `Processes` | OUT-OF-SCOPE: a terminal IDE editor is not part of this convergence |

## Timeline and lifecycle

| Reference | Reference evidence | Rust owner | Status |
|---|---|---|---|
| `TimelineItem`, `OperationalStepProjection` | `src/types/ide.ts` | `LbeEvent` typed operational events, operational history receipts | ALREADY-OWNED |
| Risk typing | `RiskLevel` `LOW`/`MEDIUM`/`HIGH`/`CRITICAL` | governed projection `risk_class` string | GAP (minor): untyped string with no `CRITICAL` level |

## Explicitly not ported

- `DemoProjectionAdapter` receipt/evidence/ID synthesis (`Date.now()`, `Math.random()`, `verified: true`, `execution_state: PERSISTED`) - REFERENCE-ONLY.
- `RealLBERuntimeAdapter` placeholder `ws://127.0.0.1:9099/lbe/stream` - design boundary only; the Rust wrapper and the current Python transport remain authoritative.
- Reference `PROJECT_INDEX.md` and `README.md` runtime-status text - stale copies, not authority.

## Action Gate and Patch Review are separate controls

The Action Gate projects LBE authority escalation (`REQUIRE_APPROVAL`). It is not a
mandatory confirmation step for operations already delegated by the active mode and
policy. This documents semantics that the runtime already enforces; it is not an
architecture change.

| Control | Question it answers | Path |
| --- | --- | --- |
| Patch Review | "Is this the change I intend to submit?" | `/patch` -> `PatchReview` -> Enter submits through the Agent Wall |
| Action Gate | "Does this operation have authority to execute?" | `AuthorizationRequired` -> ALLOW ONCE / DENY |

Consequence, measured against the real runtime: for capability `modify` the runtime
returns only `ALLOW` (already delegated) or `DENY` (`explicitly_forbidden`), so `/patch`
cannot reach the gate by design. `REQUIRE_APPROVAL` requires a capability the active
mode does not delegate, reachable via `/authorize <capability>` for a non-delegated
capability. `/patch` is therefore left unchanged.

## Next bounded slices (require user authorization each)

1. Action Gate surface driven only by the existing governed projection (no new authority, no synthetic data). - CLOSED (bounded implementation; PTY visual acceptance remains open at final-product level)
2. Single cross-linked Inspector surface over existing receipt/evidence/validation projections. - IN PROGRESS
3. Typed risk level in the client projection with an explicit `CRITICAL` value. - CLOSED / NOT YET AUTHORIZED