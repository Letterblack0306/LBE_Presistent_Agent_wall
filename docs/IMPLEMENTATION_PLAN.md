# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-09-18
Status: **ACTIVE — LBE-OWNED RUST TUI CANONICALIZATION / REAL TERMINAL ACCEPTANCE**

## 0. Read this first

The machine gate is authoritative:

```text
.lbe/governance/implementation-gates.json
active_plan  = docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md
phase        = INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE
slice        = LBE_OWNED_RUST_TUI_PRODUCT_SURFACE
status       = OPEN
implementation_allowed = true
next_phase_locked       = true
publication             = LOCKED
selected_reasoning_agent = Cline (headless mechanics)
```

The 2026-09-18 explicit product-owner decision selects the existing LBE-owned Rust/Ratatui terminal work as the canonical visible product implementation. This supersedes the older requirement to make a copied/modified Cline CLI/TUI tree the visible product shell. Cline reasoning/provider mechanics remain selected.

## 1. Product goal

Build one persistent, provider-neutral LBE coding-agent product:

```text
USER
  -> lbe
  -> LBE-owned Rust/Ratatui terminal UI
  -> canonical LBE client/runtime boundary
  -> headless Cline reasoning/provider/model mechanics
  -> LBE authorization and governed execution
  -> ToolReceipt / evidence
  -> provider continuation
  -> persistence / recovery
  -> deterministic validation / completion
  -> truthful terminal projection
```

The Rust/Ratatui client owns presentation and interaction only. Cline owns cognition/provider continuation mechanics only. LBE owns all authority-bearing consequences and truth.

## 2. Product entrypoint, UI, and embedded mechanics

```text
product                  = LBE
entrypoint               = lbe
visible terminal client  = C:\LBE-TUI-Lab\src\ (Rust/Ratatui)
visual contract/reference= existing LBE HTML/React work + canonical GPT-K UI contract
reasoning mechanics      = governed headless Cline worker / @cline/agents
runtime authority        = LBE Agent Wall
validation runtime       = C:\Agents-Memory-Tool-v6-validation
```

The Cline CLI/OpenTUI product surface is no longer a product requirement. Its source may remain reference/reuse material for interaction ideas only. Do not restore a full Cline UI tree merely to satisfy presentation.

Python/Textual remains historical/diagnostic material, not the final product UI.

## 3. Proven baseline — do not reopen without regression evidence

Keep all previously proven LBE runtime/session/authorization/execution/receipt/evidence/persistence/validation/completion owners. Keep governed Cline worker/provider continuation evidence. Keep existing Rust RealLbeWrapper and client implementation as the selected presentation base, but do not infer installed acceptance from source/tests alone.

## 4. Current defect / open acceptance boundary

The technology/product decision is settled; implementation and package composition are not.

```text
Rust/Ratatui selected as canonical visible client  ACCEPTED
LBE visual contract / HTML reuse                   ACCEPTED_REFERENCE
Cline headless reasoning/provider mechanics        ACCEPTED
current product integration script                 SOURCE_RECONCILED / VALIDATION_PENDING
installed one-command Rust LBE product             UNVERIFIED
real PTY/ConPTY lifecycle                          UNVERIFIED
final product acceptance                           BLOCKED
```

`tools/lbe_product_integration.ps1` was source-reconciled at `cebd8cf7751b2cdeb8a76fb0dcc2e0bc0c8f58e5`: copied Cline UI checks are reference-only/non-blocking, while the product build/package path remains the Rust `lbe.exe` plus governed headless Cline worker. Claim-matched validation remains required before acceptance.

## 5. Current single job

```text
LBE_OWNED_RUST_TUI_PRODUCT_SURFACE
```

Required implementation sequence:

1. Canonicalize `C:\LBE-TUI-Lab\src\` as the visible product client while keeping it projection/control-only.
2. Adapt the existing LBE HTML/React visual hierarchy and interactions into Rust where useful; never import simulated state.
3. Preserve RealLbeWrapper/product-entry routing to LBE owners.
4. Keep Cline headless through the governed worker/provider path; remove product dependence on a system-installed or copied visible Cline CLI.
5. Validate the reconciled product integration verifier/builder so proof target, build target, package target, and installed launcher target all reference the same Rust client composition; fix only observed failures.
6. Implement/verify the locked LBE shell: compact header, unified timeline, [I] composer, real context usage, PLAN/ACT/AUDIT, concise approvals, no normal-user governance dump.
7. Reconcile user-facing PLAN/ACT/AUDIT with backend mode/policy/permission owners explicitly; do not hard-code unsafe authority.
8. Build/package/install from canonical source and prove the real terminal path.

## 6. Final real-terminal acceptance

Required proof chain:

```text
fresh terminal
-> lbe
-> LBE-owned Rust/Ratatui shell
-> canonical LBE session identity
-> real provider/model projection
-> headless Cline reasoning turn
-> governed tool proposal
-> authorization decision
-> exactly-once LBE execution
-> ToolReceipt/evidence correlation
-> provider continuation
-> persisted session consequence / resume
-> deterministic validation/completion
-> clean quit
-> terminal restoration
```

No source-only test, HTML prototype, Rust unit test, screenshot, or provider prose may substitute for this installed interactive proof.

## 7. Timeline / information surface contract

The final UI timeline is the readable operational foreground, not a decorative feed.

Meaningful events should project typed runtime truth, including as applicable:

```text
session_id
turn_id
operation_id
provider_tool_call_id
lbe_call_id
child_run_id
tool_receipt_id
evidence_refs
state
summary
target
provider
tool
result
error_code
```

Useful event families:

```text
instruction.received
agent.response
tool.requested
tool.started
tool.completed
tool.failed
provider.requested
provider.event
provider.failed
governance.blocked
validation.started
validation.completed
memory.recalled
skill.selected
skill.loaded
session.created
session.resumed
session.recovered
completion.proposed
completion.verified
```

Aggregate renderer plumbing, heartbeats, terminal resize noise, and repetitive health reads. Never hide a real failure or synthesize a success.

## 8. Memory / skills / evidence semantics

```text
tool     = executable capability
skill    = procedure for using capabilities
memory   = durable historical/project context
evidence = proof of an observed result
```

Historical memory may explain prior intent but cannot override current workspace/runtime truth.
Skills may guide procedure but cannot become execution authority.
Evidence and receipts remain LBE-owned.

## 9. Stop conditions

Continue automatically through routine implementation and validation. Stop only when:

- user-only authorization is actually required;
- the requested operation is destructive/publication-sensitive;
- canonical sources conflict and current evidence cannot resolve them;
- required external credentials/service/runtime are unavailable;
- the machine gate denies the mutation.

Do not stop merely because a request is marked unsupported. Trace the owner, implement the missing safe seam when relevant, record genuine exclusions, and continue.

## 10. Historical evidence routing

Do not embed historical failures into the live plan. Use the canonical records instead:

- `docs/acceptance/` for active/bounded acceptance records;
- `docs/history/` for superseded failure/repair history;
- `docs/governance/PROJECT_INTENT_LEDGER.md` for intent history;
- `docs/DOCUMENT_INTENT_MANIFEST.md` for document roles.

## 11. Completion predicate

The current slice can pass only when all are true:

```text
one canonical LBE runtime authority
one persisted workspace/session identity
accepted Cline CLI/TUI launches from the intended product path
structurally distinct LBE UI is visibly accepted
provider/model state is real
agent reasoning remains independent
all authority-bearing execution crosses LBE authorization/governed dispatch
DENY executes zero times
ALLOW executes exactly once
ToolReceipt/evidence correlation survives continuation
session/recovery state survives resume
validation establishes completion truth
clean PTY/ConPTY exit restores the terminal
no second authority exists
```

Until then:

```text
FINAL_PRODUCT_ACCEPTANCE = BLOCKED
PUBLICATION = LOCKED
```

## Final product acceptance status — 2026-09-18

```text
LBE_OWNED_RUST_TUI_PRODUCT_SURFACE = COMPLETE
FINAL_PRODUCT_ACCEPTANCE           = PASS
CANONICAL_INSTALLER_CONTRACT       = PASS
INSTALLED_SINGLE_COMMAND_LAUNCH    = PASS
```

The implementation/acceptance plan for the installed LBE product is complete. Further work, if any, belongs to separately authorized release/publication or new product intents.

